import requests
import feedparser
import yfinance as yf
import pandas as pd
import streamlit as st
import time

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

@st.cache_data(ttl=1800)
def obtener_macro_argentina():
    datos = {
        "dolares": [], "riesgo_pais": None, 
        "merval": {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None},
        "inflacion": None, "tasa_bcra": None, "reservas": None
    }
    
    # 1. Dólares
    try:
        res = requests.get("https://dolarapi.com/v1/dolares", timeout=10)
        if res.status_code == 200:
            for d in res.json():
                if d["casa"] in ["oficial", "blue", "bolsa", "contadoconliqui", "tarjeta"]:
                    nombre = "MEP" if d["casa"] == "bolsa" else "CCL" if d["casa"] == "contadoconliqui" else d["casa"].capitalize()
                    datos["dolares"].append({"nombre": nombre, "compra": d["compra"], "venta": d["venta"]})
    except: pass
    
    # 2. Riesgo País 
    try:
        res_rp = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", timeout=10)
        if res_rp.status_code == 200:
            data_rp = res_rp.json()
            if isinstance(data_rp, list) and len(data_rp) > 0:
                datos["riesgo_pais"] = {"valor": data_rp[-1]["valor"], "variacion": ""}
        else: raise Exception("Saltar al respaldo")
    except:
        try:
            res_rp_alt = requests.get("https://mercados.ambito.com/riesgopais/info", headers=HEADERS, timeout=10)
            if res_rp_alt.status_code == 200 and "valor" in res_rp_alt.json():
                datos["riesgo_pais"] = {"valor": res_rp_alt.json().get("valor"), "variacion": res_rp_alt.json().get("variacion")}
        except: pass

    # 3. Inflación Argentina (IPC) 
    try:
        res_inf = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", timeout=10)
        if res_inf.status_code == 200:
            data_inf = res_inf.json()
            if isinstance(data_inf, list) and len(data_inf) > 0:
                datos["inflacion"] = float(data_inf[-1]["valor"]) 
    except: pass

    # 4. Tasa de Referencia 
    try:
        res_tasa = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/politicaMonetaria", timeout=10)
        if res_tasa.status_code == 200:
            data_tasa = res_tasa.json()
            if isinstance(data_tasa, list):
                for item in reversed(data_tasa):
                    val = item.get("valor") or item.get("tasa")
                    if val is not None:
                        tasa_num = float(val)
                        datos["tasa_bcra"] = tasa_num * 100 if tasa_num < 2 else tasa_num
                        break 
        if datos["tasa_bcra"] is None: raise Exception("Saltar a Plazo Fijo")
    except:
        try:
            res_tasa_alt = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo", timeout=10)
            if res_tasa_alt.status_code == 200:
                data_tasa_alt = res_tasa_alt.json()
                if isinstance(data_tasa_alt, list):
                    for item in reversed(data_tasa_alt):
                        val_alt = item.get("valor") or item.get("tasa")
                        if val_alt is not None:
                            tasa_num = float(val_alt)
                            datos["tasa_bcra"] = tasa_num * 100 if tasa_num < 2 else tasa_num
                            break
        except: pass

    # 4.5. Reservas BCRA (Nuevo)
    try:
        res_bcra = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", timeout=10)
        if res_bcra.status_code == 200:
            data_bcra = res_bcra.json()
            if isinstance(data_bcra, list):
                for item in reversed(data_bcra):
                    if item.get("valor") is not None:
                        datos["reservas"] = float(item["valor"])
                        break
    except: pass

    # 5. Merval
    try:
        merv = yf.Ticker("^MERV").history(period="1y")
        if len(merv) >= 2:
            act = merv['Close'].iloc[-1]
            datos["merval"]["valor"] = float(act)
            datos["merval"]["var_diaria"] = float(((act / merv['Close'].iloc[-2]) - 1) * 100)
            if len(merv) >= 21: datos["merval"]["var_1m"] = float(((act / merv['Close'].iloc[-21]) - 1) * 100)
            if len(merv) >= 126: datos["merval"]["var_6m"] = float(((act / merv['Close'].iloc[-126]) - 1) * 100)
            if len(merv) >= 250: datos["merval"]["var_1y"] = float(((act / merv['Close'].iloc[0]) - 1) * 100)
    except: pass
    
    return datos

@st.cache_data(ttl=3600)
def obtener_macro_internacional():
    datos = {}
    # EXPANDIDO: Nivel 1 Macro
    tickers_macro = {
        "S&P 500 (Global)": "^GSPC",
        "Nasdaq (Tech)": "^IXIC",
        "Russell 2000 (Small Caps)": "^RUT",
        "Oro (Refugio)": "GC=F",
        "Petróleo Crudo (WTI)": "CL=F", 
        "DXY (Índice Dólar)": "DX-Y.NYB",
        "VIX (Miedo)": "^VIX",
        "Bono 10Y EE.UU (%)": "^TNX"
    }
    
    for nombre, t in tickers_macro.items():
        datos[nombre] = {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None}
        try:
            hist = yf.Ticker(t).history(period="1y")
            if len(hist) >= 2:
                actual = hist['Close'].iloc[-1]
                datos[nombre]["valor"] = float(actual)
                datos[nombre]["var_diaria"] = float(((actual / hist['Close'].iloc[-2]) - 1) * 100)
                if len(hist) >= 21: datos[nombre]["var_1m"] = float(((actual / hist['Close'].iloc[-21]) - 1) * 100)
                if len(hist) >= 126: datos[nombre]["var_6m"] = float(((actual / hist['Close'].iloc[-126]) - 1) * 100)
                if len(hist) >= 250: datos[nombre]["var_1y"] = float(((actual / hist['Close'].iloc[0]) - 1) * 100)
        except: pass

    try:
        if "FRED_API_KEY" in st.secrets:
            api_key = st.secrets["FRED_API_KEY"]
            # EXPANDIDO: Curva de rendimientos 2Y-10Y
            fred_series = {
                "Tasa FED (%)": {"id": "FEDFUNDS", "units": "lin"},
                "Inflación EE.UU YoY (%)": {"id": "CPIAUCSL", "units": "pc1"},
                "Yield Curve 2Y-10Y (pts)": {"id": "T10Y2Y", "units": "lin"},
                "Desempleo EE.UU (%)": {"id": "UNRATE", "units": "lin"}
            }
            for nombre, config in fred_series.items():
                datos[nombre] = {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None}
                url = f"https://api.stlouisfed.org/fred/series/observations?series_id={config['id']}&api_key={api_key}&file_type=json&units={config['units']}&sort_order=desc&limit=15"
                try:
                    res = requests.get(url, timeout=5)
                    if res.status_code == 200:
                        obs = res.json().get("observations", [])
                        valid_obs = [float(o["value"]) for o in obs if o["value"] != "."]
                        if len(valid_obs) >= 1:
                            act = valid_obs[0]
                            datos[nombre]["valor"] = act
                            if len(valid_obs) >= 2:
                                datos[nombre]["var_diaria"] = act - valid_obs[1] 
                                datos[nombre]["var_1m"] = act - valid_obs[1] 
                            if len(valid_obs) >= 7: datos[nombre]["var_6m"] = act - valid_obs[6]
                            if len(valid_obs) >= 13: datos[nombre]["var_1y"] = act - valid_obs[12]
                except: pass
    except: pass 
    return datos

# NUEVO: MOTOR DE VALUACIONES (NIVEL 2)
@st.cache_data(ttl=3600)
def obtener_valuaciones_mercado():
    # ADRs Argentinos y ETFs de Sectores USA
    activos_arg = {"YPF": "Energía", "GGAL": "Financiero", "BMA": "Financiero", "PAMP": "Energía", "CEPU": "Utilities"}
    activos_usa = {"SPY": "S&P 500", "QQQ": "Nasdaq", "XLE": "Energía", "XLF": "Financiero", "XLK": "Tecnología", "XLV": "Salud"}
    
    valuaciones = {"ARG": [], "USA": []}
    
    for ticker, sector in {**activos_arg, **activos_usa}.items():
        try:
            tk = yf.Ticker(ticker)
            info = tk.info
            pe = info.get("trailingPE") or info.get("forwardPE")
            pb = info.get("priceToBook")
            roe = info.get("returnOnEquity")
            dy = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
            
            data = {
                "Activo": ticker,
                "Sector / Índice": sector,
                "P/E": f"{pe:.2f}" if pe else "-",
                "P/B": f"{pb:.2f}" if pb else "-",
                "ROE (%)": f"{roe*100:.1f}%" if roe else "-",
                "Div. Yield (%)": f"{dy*100:.2f}%" if dy else "-"
            }
            if ticker in activos_arg:
                valuaciones["ARG"].append(data)
            else:
                valuaciones["USA"].append(data)
        except:
            pass
    return valuaciones

@st.cache_data(ttl=1800)
def obtener_noticias_acciones(lista_tickers):
    noticias = {}
    for ticker in lista_tickers[:6]:
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
            feed = feedparser.parse(url)
            entradas = []
            for entry in feed.entries[:3]:
                entradas.append({"titulo": entry.title, "link": entry.link, "fecha": entry.published})
            noticias[ticker] = entradas
        except: noticias[ticker] = []
    return noticias

@st.cache_data(ttl=3600)
def generar_analisis_ia(macro_arg, macro_int, brecha):
    # Se mantiene la versión estable global temporalmente hasta implementar el Nivel 4
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ **Falta la clave API de Gemini.**"
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        prompt = f"""
        Eres un Asesor Financiero Institucional. Analiza el tablero macroeconómico global.
        ### 1. Visión Estratégica General (4 bullet points).
        ### 2. Perspectiva GICS (Tabla Markdown: Sector | Veredicto | Justificación).
        --- DATOS INTERNACIONALES ---\n
        """
        for nombre, datos in macro_int.items():
            prompt += f"{nombre}: {datos.get('valor', 'N/D')}\n"
            
        modelos = ["gemini-1.5-flash", "gemini-1.5-pro"]
        headers = {'Content-Type': 'application/json'}
        for modelo in modelos:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
            try:
                res = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=25)
                if res.status_code == 200:
                    return res.json()['candidates'][0]['content']['parts'][0]['text'].replace('</div>', '').replace('<div>', '').strip()
                if res.status_code == 429: time.sleep(2)
            except: pass
        return "❌ Error del servidor de IA."
    except Exception as e: return f"❌ Error: {e}"
