import requests
import feedparser
import yfinance as yf
import pandas as pd
import streamlit as st

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

@st.cache_data(ttl=1800)
def obtener_macro_argentina():
    datos = {"dolares": [], "riesgo_pais": None, "merval": None}
    try:
        res = requests.get("https://dolarapi.com/v1/dolares", timeout=5)
        if res.status_code == 200:
            for d in res.json():
                if d["casa"] in ["oficial", "blue", "bolsa", "contadoconliqui", "tarjeta"]:
                    nombre = "MEP" if d["casa"] == "bolsa" else "CCL" if d["casa"] == "contadoconliqui" else d["casa"].capitalize()
                    datos["dolares"].append({"nombre": nombre, "compra": d["compra"], "venta": d["venta"]})
    except: pass
    
    try:
        res_rp = requests.get("https://mercados.ambito.com//riesgopais/info", headers=HEADERS, timeout=5)
        if res_rp.status_code == 200:
            rp_json = res_rp.json()
            datos["riesgo_pais"] = {"valor": rp_json.get("valor"), "variacion": rp_json.get("variacion")}
    except: pass

    try:
        merv = yf.Ticker("^MERV").history(period="5d")
        if len(merv) >= 2:
            act = merv['Close'].iloc[-1]
            prev = merv['Close'].iloc[-2]
            if not pd.isna(act) and not pd.isna(prev):
                datos["merval"] = {"valor": act, "var": ((act / prev) - 1) * 100}
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
        datos[nombre] = {"valor": None, "var": None}
        try:
            hist = yf.Ticker(t).history(period="5d")
            if len(hist) >= 2:
                actual = hist['Close'].iloc[-1]
                previo = hist['Close'].iloc[-2]
                if not pd.isna(actual) and not pd.isna(previo):
                    datos[nombre] = {"valor": float(actual), "var": float(((actual / previo) - 1) * 100)}
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
                datos[nombre] = {"valor": None, "var": None}
                url = f"https://api.stlouisfed.org/fred/series/observations?series_id={config['id']}&api_key={api_key}&file_type=json&units={config['units']}&sort_order=desc&limit=2"
                try:
                    res = requests.get(url, timeout=5)
                    if res.status_code == 200:
                        obs = res.json().get("observations", [])
                        if len(obs) >= 2:
                            v_act = obs[0]["value"]
                            v_prev = obs[1]["value"]
                            if v_act != "." and v_prev != ".":
                                act = float(v_act)
                                prev = float(v_prev)
                                datos[nombre] = {"valor": act, "var": act - prev}
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
                entradas.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "fecha": entry.published
                })
            noticias[ticker] = entradas
        except:
            noticias[ticker] = []
    return noticias

# --- NUEVO MOTOR DE INTELIGENCIA ARTIFICIAL (CON FALLBACK AUTOMÁTICO) ---
@st.cache_data(ttl=3600)
def generar_analisis_ia(macro_arg, macro_int, brecha):
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ **Falta la clave API de Gemini.** Configura `GEMINI_API_KEY` en los Secrets de Streamlit."
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        
        # 1. Empaquetamos los datos
        rp = macro_arg.get('riesgo_pais')
        rp_val = rp['valor'] if rp else 'N/D'
        merv = macro_arg.get('merval')
        merv_val = f"{merv['valor']:.0f} (Var: {merv['var']:.2f}%)" if merv else 'N/D'
        brecha_str = f"{brecha:.2f}%" if brecha is not None else 'N/D'
        
        prompt = f"""
        Eres un asesor financiero didáctico, claro y amigable.
        Analiza el siguiente tablero macroeconómico de Argentina y EE.UU. 
        Redacta un análisis en 4 bullet points indicando oportunidades de inversión claras, pero explicadas con un lenguaje sencillo, fácil de entender para un inversor principiante o intermedio.
        Si usas jerga financiera (como "carry trade" o "soft landing"), explícala brevemente en términos cotidianos. Evita saludos, ve directo al análisis.
        
        --- DATOS ARGENTINA ---
        
        --- DATOS ARGENTINA ---
        Riesgo País: {rp_val}
        Merval: {merv_val}
        Brecha Cambiaria (CCL vs Oficial): {brecha_str}
        
        --- DATOS INTERNACIONALES ---
        """
        for nombre, datos in macro_int.items():
            v = datos['valor'] if datos['valor'] is not None else 'N/D'
            var = datos['var'] if datos['var'] is not None else 'N/D'
            prompt += f"{nombre}: {v} (Var: {var})\n"
            
        # 2. Arquitectura de Alta Disponibilidad (Lista de modelos de prioridad)
        modelos_a_probar = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]
        
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        # 3. El código intentará cada modelo en orden. Si hay cuello de botella (503), salta al siguiente.
        for modelo in modelos_a_probar:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
            res = requests.post(url, headers=headers, json=payload, timeout=45)
            
            if res.status_code == 200:
                data = res.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            elif res.status_code == 503:
                continue  # Error de tráfico. El bucle pasa inmediatamente al modelo 'lite'.
            else:
                return f"❌ **Error del servidor de IA:** Código {res.status_code} en {modelo}. Respuesta: {res.text}"
        
        # Si todos los modelos de la lista fallan por 503:
        return "⚠️ **Servidores de Google Saturados:** En este momento la API gratuita está experimentando un pico de tráfico global. Por favor, intenta sincronizar los datos nuevamente en unos minutos."
            
    except Exception as e:
        return f"❌ **Error crítico de conexión:** No se pudo procesar la IA. Detalle: {e}"
