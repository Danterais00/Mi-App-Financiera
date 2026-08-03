import requests
import feedparser
import yfinance as yf
import pandas as pd
import streamlit as st
import time
import logging

# --- CONFIGURACIÓN DE LOGS ---
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    except Exception as e: logger.warning(f"Error DolarAPI: {e}")
    
    try:
        res_rp = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", timeout=10)
        if res_rp.status_code == 200:
            data_rp = res_rp.json()
            if isinstance(data_rp, list) and len(data_rp) > 0:
                datos["riesgo_pais"] = {"valor": data_rp[-1]["valor"], "variacion": ""}
        else: raise Exception("Saltar al respaldo")
    except Exception as e:
        try:
            res_rp_alt = requests.get("https://mercados.ambito.com/riesgopais/info", headers=HEADERS, timeout=10)
            if res_rp_alt.status_code == 200 and "valor" in res_rp_alt.json():
                datos["riesgo_pais"] = {"valor": res_rp_alt.json().get("valor"), "variacion": res_rp_alt.json().get("variacion")}
        except Exception as e2: logger.warning(f"Error Riesgo País (ambos): {e2}")

    try:
        res_inf = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", timeout=10)
        if res_inf.status_code == 200:
            data_inf = res_inf.json()
            if isinstance(data_inf, list) and len(data_inf) > 0:
                datos["inflacion"] = float(data_inf[-1]["valor"]) 
    except Exception as e: logger.warning(f"Error Inflación: {e}")

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
    except Exception as e:
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
        except Exception as e2: logger.warning(f"Error Tasa BCRA: {e2}")

    try:
        res_bcra = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", timeout=10)
        if res_bcra.status_code == 200:
            data_bcra = res_bcra.json()
            if isinstance(data_bcra, list):
                for item in reversed(data_bcra):
                    if item.get("valor") is not None:
                        datos["reservas"] = float(item["valor"])
                        break
    except Exception as e: logger.warning(f"Error Reservas BCRA: {e}")

    try:
        merv = yf.Ticker("^MERV").history(period="1y")
        if len(merv) >= 2:
            act = merv['Close'].iloc[-1]
            datos["merval"]["valor"] = float(act)
            datos["merval"]["var_diaria"] = float(((act / merv['Close'].iloc[-2]) - 1) * 100)
            if len(merv) >= 21: datos["merval"]["var_1m"] = float(((act / merv['Close'].iloc[-21]) - 1) * 100)
            if len(merv) >= 126: datos["merval"]["var_6m"] = float(((act / merv['Close'].iloc[-126]) - 1) * 100)
            if len(merv) >= 250: datos["merval"]["var_1y"] = float(((act / merv['Close'].iloc[0]) - 1) * 100)
    except Exception as e: logger.warning(f"Error Merval: {e}")
    
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
    
    for nombre in tickers_macro.keys():
        datos[nombre] = {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None}
    
    lista_tickers = list(tickers_macro.values())
    try:
        hist_data = yf.download(lista_tickers, period="1y", progress=False)
        if not hist_data.empty and 'Close' in hist_data:
            df_close = hist_data['Close']
            for nombre, t in tickers_macro.items():
                if t in df_close.columns:
                    serie = df_close[t].dropna()
                    if len(serie) >= 2:
                        actual = float(serie.iloc[-1])
                        datos[nombre]["valor"] = actual
                        datos[nombre]["var_diaria"] = float(((actual / serie.iloc[-2]) - 1) * 100)
                        if len(serie) >= 21: datos[nombre]["var_1m"] = float(((actual / serie.iloc[-21]) - 1) * 100)
                        if len(serie) >= 126: datos[nombre]["var_6m"] = float(((actual / serie.iloc[-126]) - 1) * 100)
                        if len(serie) >= 250: datos[nombre]["var_1y"] = float(((actual / serie.iloc[0]) - 1) * 100)
    except Exception as e: logger.warning(f"Error Batch Download Macro: {e}")

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
                except Exception as e: logger.warning(f"Error extrayendo {nombre} de FRED: {e}")
    except Exception as e: logger.warning(f"Error FRED general: {e}")
    
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
            
            dy_str = "N/D"
            if dy is not None:
                dy_val = dy * 100 if dy < 0.20 else dy
                dy_str = f"{dy_val:.2f}%"
            
            data = {
                "Activo": ticker,
                "Sector": sector,
                "Período": "Actual (TTM)",
                "P/E": f"{pe:.2f}" if pe else "N/D",
                "P/B": f"{pb:.2f}" if pb else "N/D",
                "ROE (%)": f"{roe*100:.1f}%" if roe else "N/D",
                "Div. Yield (%)": dy_str
            }
            if ticker in activos_arg: valuaciones["ARG"].append(data)
            else: valuaciones["USA"].append(data)
        except Exception as e: logger.warning(f"Error valuación {ticker}: {e}")
    return valuaciones

@st.cache_data(ttl=3600)
def obtener_datos_gics():
    etfs_sectores = {
        "Tecnología": "XLK", "Financiero": "XLF", "Energía": "XLE", 
        "Salud": "XLV", "Industriales": "XLI", "Cons. Discrecional": "XLY", 
        "Cons. Básico": "XLP", "Utilities": "XLU", "Materiales": "XLB", 
        "Real Estate": "XLRE", "Comunicaciones": "XLC"
    }
    
    pe_historico = {
        "Tecnología": 23.0, "Financiero": 13.5, "Energía": 14.5, 
        "Salud": 17.5, "Industriales": 18.0, "Cons. Discrecional": 24.0, 
        "Cons. Básico": 20.0, "Utilities": 17.5, "Materiales": 16.5, 
        "Real Estate": 35.0, "Comunicaciones": 19.0
    }
    
    datos_sectores = []
    tickers = list(etfs_sectores.values())
    
    try:
        hist_data = yf.download(tickers, period="6mo", progress=False)
        df_close = hist_data['Close'] if 'Close' in hist_data else pd.DataFrame()
    except Exception as e:
        logger.warning(f"Error Batch Download GICS: {e}")
        df_close = pd.DataFrame()
        
    for sector, ticker in etfs_sectores.items():
        try:
            tk = yf.Ticker(ticker)
            info = tk.info
            pe = info.get("trailingPE") or info.get("forwardPE")
            pe_val = float(pe) if pe else None
            
            var_1m, var_6m = 0.0, 0.0
            if not df_close.empty and ticker in df_close.columns:
                serie = df_close[ticker].dropna()
                if len(serie) >= 20:
                    precio_actual = serie.iloc[-1]
                    precio_1m = serie.iloc[-21] if len(serie) >= 21 else precio_actual
                    precio_6m = serie.iloc[0]
                    var_1m = ((precio_actual / precio_1m) - 1) * 100
                    var_6m = ((precio_actual / precio_6m) - 1) * 100
            
            score = 50.0 
            score += (var_6m * 1.5) 
            
            if pe_val:
                benchmark = pe_historico.get(sector, 18.0)
                desviacion = (pe_val / benchmark) - 1 
                
                if desviacion < -0.15: score += 15       
                elif -0.15 <= desviacion <= 0.05: score += 5  
                elif 0.05 < desviacion <= 0.20: score -= 5    
                elif desviacion > 0.20: score -= 10      
            
            score = max(0, min(100, int(score))) 
            
            datos_sectores.append({
                "Sector": sector,
                "ETF": ticker,
                "P/E": pe_val,
                "1M (%)": var_1m,
                "6M (%)": var_6m,
                "Score": score
            })
        except Exception as e:
            logger.warning(f"Error procesando {sector}: {e}")
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
        except Exception as e: logger.warning(f"Error noticias {ticker}: {e}"); noticias[ticker] = []
    return noticias

# --- MOTOR DE IA RECONSTRUIDO: LECTURA DEL JSON DE GOOGLE ---
@st.cache_data(ttl=3600)
def generar_analisis_ia(macro_arg, macro_int, datos_gics):
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ **Falta la clave API de Gemini.** Configura `GEMINI_API_KEY` en los Secrets de Streamlit."
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        
        rp_val = macro_arg.get('riesgo_pais', {}).get('valor', 'N/D') if macro_arg.get('riesgo_pais') else 'N/D'
        inf = macro_arg.get('inflacion', 'N/D')
        tasa = macro_arg.get('tasa_bcra', 'N/D')
        
        bono_val = macro_int.get('Bono 10Y EE.UU (%)', {}).get('valor', 'N/D') if 'Bono 10Y EE.UU (%)' in macro_int else 'N/D'
        inf_us_val = macro_int.get('Inflación EE.UU YoY (%)', {}).get('valor', 'N/D') if 'Inflación EE.UU YoY (%)' in macro_int else 'N/D'
        curva_val = macro_int.get('Yield Curve 2Y-10Y (pts)', {}).get('valor', 'N/D') if 'Yield Curve 2Y-10Y (pts)' in macro_int else 'N/D'
        
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
        Bono 10Y EE.UU: {bono_val}
        Inflación EE.UU: {inf_us_val}
        Curva 2Y-10Y EE.UU: {curva_val}
        Riesgo País ARG: {rp_val}
        Tasa ARG: {tasa}%
        Inflación ARG: {inf}%
        
        --- SCORES SECTORES GICS ---
        """
        
        for g in datos_gics:
            pe_str = f"{g['P/E']:.2f}" if g['P/E'] else "N/D"
            prompt += f"Sector: {g['Sector']} | P/E actual: {pe_str} | Retorno 6M: {g['6M (%)']:.1f}% | SCORE QUANT: {g['Score']}/100\n"
            
        modelos = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-pro"
        ]
        
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
                    
                    else:
                        # Extraer el error nativo exacto de Google
                        try:
                            error_detalle = res.json().get('error', {}).get('message', 'Error desconocido en JSON')
                        except:
                            error_detalle = res.text[:80] # Extraer primeros caracteres si no es JSON
                            
                        if res.status_code == 429:
                            if intento < max_reintentos - 1:
                                time.sleep(3)
                                continue
                            else:
                                errores_detallados.append(f"{modelo}: 429 (Saturado)")
                                break
                        else:
                            # Imprimir el código de error y las palabras exactas de Google
                            errores_detallados.append(f"{modelo}: {res.status_code} ({error_detalle})")
                            break
                        
                except requests.exceptions.RequestException as e:
                    errores_detallados.append(f"{modelo}: Error de Red ({e})")
                    break
                    
        return f"❌ **Error del servidor de IA.** Detalle: { ' | '.join(errores_detallados) }"
        
    except Exception as e: 
        return f"❌ **Error crítico de procesamiento:** Detalle: {e}"
