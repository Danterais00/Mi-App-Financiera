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
        "inflacion": None, "tasa_bcra": None 
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
        else:
            raise Exception("Saltar al respaldo")
    except:
        try:
            res_rp_alt = requests.get("https://mercados.ambito.com/riesgopais/info", headers=HEADERS, timeout=10)
            if res_rp_alt.status_code == 200 and "valor" in res_rp_alt.json():
                rp_json = res_rp_alt.json()
                datos["riesgo_pais"] = {"valor": rp_json.get("valor"), "variacion": rp_json.get("variacion")}
        except: pass

    # 3. Inflación Argentina (IPC) 
    try:
        res_inf = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", timeout=10)
        if res_inf.status_code == 200:
            data_inf = res_inf.json()
            if isinstance(data_inf, list) and len(data_inf) > 0:
                datos["inflacion"] = float(data_inf[-1]["valor"]) 
    except: pass

    # 4. Tasa de Referencia (NUEVO: Búsqueda inversa segura y cambio de prioridad)
    try:
        # Intento 1: Tasa de Política Monetaria (Principal)
        res_tasa = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/politicaMonetaria", timeout=10)
        if res_tasa.status_code == 200:
            data_tasa = res_tasa.json()
            if isinstance(data_tasa, list):
                # Búsqueda inversa: desde el dato más reciente hacia atrás
                for item in reversed(data_tasa):
                    val = item.get("valor") or item.get("tasa")
                    if val is not None:
                        tasa_num = float(val)
                        datos["tasa_bcra"] = tasa_num * 100 if tasa_num < 2 else tasa_num
                        break # Encontramos el último dato válido, detenemos la búsqueda
        
        # Si luego del Intento 1 sigue siendo None, forzamos el plan B
        if datos["tasa_bcra"] is None:
            raise Exception("Saltar a Plazo Fijo")
    except:
        try:
            # Intento 2: Tasa de Plazo Fijo (Respaldo)
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
    tickers_macro = {
        "S&P 500 (Mercado Global)": "^GSPC",
        "Petróleo Crudo (WTI)": "CL=F", 
        "DXY (Índice Dólar)": "DX-Y.NYB",
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
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ **Falta la clave API de Gemini.** Configura `GEMINI_API_KEY` en los Secrets de Streamlit."
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        
        prompt = f"""
        Eres un Asesor Financiero Institucional (Portfolio Manager).
        Analiza el siguiente tablero macroeconómico global. 
        
        Tu respuesta debe tener EXACTAMENTE DOS partes en formato Markdown:
        
        ### 1. Visión Estratégica General
        Redacta un análisis en 4 bullet points indicando oportunidades de inversión en renta variable (acciones), deduciendo en qué etapa del ciclo nos encontramos.
        
        ### 2. Perspectiva de los 11 Sectores (Clasificación GICS)
        Basándote en los datos internacionales, dibuja una tabla Markdown de 3 columnas:
        | Sector (GICS) | Veredicto (Atractivo / Neutral / Cautela) | Justificación (1 oración) |
        
        REGLA ESTRICTA: NO uses HTML. Solo Markdown.
        
        --- DATOS INTERNACIONALES ---
        """
        for nombre, datos in macro_int.items():
            v = datos.get('valor')
            var_d = datos.get('var_diaria')
            var_1y = datos.get('var_1y')
            
            v_str = f"{v:.2f}" if v is not None else 'N/D'
            str_d = f"Diaria: {var_d:.2f}%" if var_d is not None else "N/D"
            str_1y = f" | 1Y: {var_1y:.2f}%" if var_1y is not None else ""
            
            prompt += f"{nombre}: {v_str} ({str_d}{str_1y})\n"
            
        modelos = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        ultimo_error = ""
        
        for modelo in modelos:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=25)
                
                if res.status_code == 200:
                    texto_ia = res.json()['candidates'][0]['content']['parts'][0]['text']
                    return texto_ia.replace('</div>', '').replace('<div>', '').strip()
                else:
                    ultimo_error = f"Código {res.status_code}: {res.text}"
                    if res.status_code == 429:
                        time.sleep(2)
                    continue
                    
            except Exception as e:
                ultimo_error = f"Fallo en {modelo}: {str(e)}"
                continue
                
        return f"❌ **Error del servidor de IA:** Ningún modelo respondió. Último fallo: {ultimo_error}"
        
    except Exception as e: 
        return f"❌ **Error crítico de procesamiento:** Detalle: {e}"
