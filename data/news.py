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
    
    try:
        res = requests.get("https://dolarapi.com/v1/dolares", timeout=10)
        if res.status_code == 200:
            for d in res.json():
                if d["casa"] in ["oficial", "blue", "bolsa", "contadoconliqui", "tarjeta"]:
                    nombre = "MEP" if d["casa"] == "bolsa" else "CCL" if d["casa"] == "contadoconliqui" else d["casa"].capitalize()
                    datos["dolares"].append({"nombre": nombre, "compra": d["compra"], "venta": d["venta"]})
    except: pass
    
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

    try:
        res_inf = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", timeout=10)
        if res_inf.status_code == 200:
            data_inf = res_inf.json()
            if isinstance(data_inf, list) and len(data_inf) > 0:
                datos["inflacion"] = float(data_inf[-1]["valor"]) 
    except: pass

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

@st.cache_data(ttl=3600)
def obtener_valuaciones_mercado():
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
            if ticker in activos_arg: valuaciones["ARG"].append(data)
            else: valuaciones["USA"].append(data)
        except: pass
    return valuaciones

@st.cache_data(ttl=3600)
def obtener_datos_gics():
    etfs_sectores = {
        "Tecnología": "XLK", "Financiero": "XLF", "Energía": "XLE", 
        "Salud": "XLV", "Industriales": "XLI", "Cons. Discrecional": "XLY", 
        "Cons. Básico": "XLP", "Utilities": "XLU", "Materiales": "XLB", 
        "Real Estate": "XLRE", "Comunicaciones": "XLC"
    }
    
    datos_sectores = []
    
    for sector, ticker in etfs_sectores.items():
        exito = False
        for intento in range(2):
            try:
                tk = yf.Ticker(ticker)
                info = tk.info
                hist = tk.history(period="6mo")
                
                if len(hist) < 20: 
                    continue 
                
                precio_actual = hist['Close'].iloc[-1]
                precio_1m = hist['Close'].iloc[-21] if len(hist) >= 21 else precio_actual
                precio_6m = hist['Close'].iloc[0]
                
                var_1m = ((precio_actual / precio_1m) - 1) * 100
                var_6m = ((precio_actual / precio_6m) - 1) * 100
                
                pe = info.get("trailingPE") or info.get("forwardPE")
                pe_val = float(pe) if pe else None
                
                score = 50.0 
                score += (var_6m * 1.5) 
                
                if pe_val:
                    if pe_val < 15: score += 15
                    elif 15 <= pe_val <= 22: score += 5
                    elif 22 < pe_val <= 28: score -= 5
                    elif pe_val > 28: score -= 10 
                
                score = max(0, min(100, int(score))) 
                
                datos_sectores.append({
                    "Sector": sector,
                    "ETF": ticker,
                    "P/E": pe_val,
                    "1M (%)": var_1m,
                    "6M (%)": var_6m,
                    "Score": score
                })
                exito = True
                break 
            except:
                time.sleep(1) 
                
        if not exito:
            datos_sectores.append({
                "Sector": sector, "ETF": ticker, "P/E": None,
                "1M (%)": 0.0, "6M (%)": 0.0, "Score": 50
            })
        
    return sorted(datos_sectores, key=lambda x: x["Score"], reverse=True)

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
def generar_analisis_ia(macro_arg, macro_int, datos_gics):
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ **Falta la clave API de Gemini.** Configura `GEMINI_API_KEY` en los Secrets de Streamlit."
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        
        rp = macro_arg.get('riesgo_pais') or {}
        rp_val = rp.get('valor') or 'N/D'
        inf = macro_arg.get('inflacion') or 'N/D'
        tasa = macro_arg.get('tasa_bcra') or 'N/D'
        
        # CORRECCIÓN DE SINTAXIS APLICADA ABAJO (Uso de {} simple en lugar de {{}})
        prompt = f"""
        Eres un Modelo Cuantitativo de Inversión Institucional. 
        Analiza el tablero global y los scores sectoriales. 
        
        Devuelve tu respuesta ESTRICTAMENTE usando el formato de SEMÁFOROS, sin texto introductorio, estructurado de la siguiente forma usando listas:
        
        ### 1. Entorno Macro y Renta Fija
        [Emoji] **Contexto Global:** [Breve justificación]
        [Emoji] **Bonos del Tesoro (USA):** [Comprar/Mantener/Vender] - [Justificación]
        [Emoji] **Renta Fija Argentina (Carry/Bonos):** [Comprar/Mantener/Vender] - [Justificación]
        
        ### 2. Semáforo Sectores GICS (Acciones)
        Asigna el color según el 'Score' provisto y la macro:
        [Emoji] **[Nombre del Sector]:** [Comprar/Mantener/Vender] - [Una línea de por qué]
        (Repetir para los 5 mejores sectores)
        
        Reglas de Emojis: 🟢 (Comprar/Positivo), 🟡 (Mantener/Neutral), 🔴 (Vender/Cautela).
        NO uses HTML. Solo formato Markdown puro.
        
        --- DATOS MACRO ---
        Bono 10Y EE.UU: {macro_int.get('Bono 10Y EE.UU (%)', {{}}).get('valor', 'N/D')}
        Inflación EE.UU: {macro_int.get('Inflación EE.UU YoY (%)', {{}}).get('valor', 'N/D')}
        Curva 2Y-10Y EE.UU: {macro_int.get('Yield Curve 2Y-10Y (pts)', {{}}).get('valor', 'N/D')}
        Riesgo País ARG: {rp_val}
        Tasa ARG: {tasa}%
        Inflación ARG: {inf}%
        
        --- SCORES SECTORES GICS ---
        """
        
        for g in datos_gics:
            pe_str = g['P/E'] if g['P/E'] else "N/D"
            prompt += f"Sector: {g['Sector']} | P/E: {pe_str} | Retorno 6M: {g['6M (%)']:.1f}% | SCORE QUANT: {g['Score']}/100\n"
            
        modelos = ["gemini-1.5-flash", "gemini-1.5-flash-8b"]
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        errores_detallados = []
        max_reintentos = 2
        
        for modelo in modelos:
            for intento in range(max_reintentos):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
                try:
                    res = requests.post(url, headers=headers, json=payload, timeout=30)
                    
                    if res.status_code == 200:
                        texto_ia = res.json()['candidates'][0]['content']['parts'][0]['text']
                        return texto_ia.replace('</div>', '').replace('<div>', '').strip()
                    
                    elif res.status_code == 429:
                        if intento < max_reintentos - 1:
                            time.sleep(3)
                            continue
                        else:
                            errores_detallados.append(f"{modelo}: 429 (Saturado)")
                            break
                    
                    elif res.status_code == 404:
                        errores_detallados.append(f"{modelo}: 404 (No autorizado)")
                        break
                    
                    else:
                        errores_detallados.append(f"{modelo}: Error {res.status_code}")
                        break
                        
                except requests.exceptions.RequestException:
                    errores_detallados.append(f"{modelo}: Fallo de red")
                    break
                    
        return f"❌ **Error del servidor de IA.** Detalle: { ' | '.join(errores_detallados) }"
        
    except Exception as e: 
        return f"❌ **Error crítico de procesamiento:** Detalle: {e}"
