import requests
import feedparser
import yfinance as yf
import pandas as pd
import streamlit as st

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

@st.cache_data(ttl=1800)
def obtener_macro_argentina():
    datos = {"dolares": [], "riesgo_pais": None, "merval": {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None}}
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
        merv = yf.Ticker("^MERV").history(period="1y")
        if len(merv) >= 2:
            act = merv['Close'].iloc[-1]
            datos["merval"]["valor"] = act
            datos["merval"]["var_diaria"] = ((act / merv['Close'].iloc[-2]) - 1) * 100
            
            if len(merv) >= 21:
                datos["merval"]["var_1m"] = ((act / merv['Close'].iloc[-21]) - 1) * 100
            if len(merv) >= 126:
                datos["merval"]["var_6m"] = ((act / merv['Close'].iloc[-126]) - 1) * 100
            if len(merv) >= 250:
                datos["merval"]["var_1y"] = ((act / merv['Close'].iloc[0]) - 1) * 100
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
    
    # 1. Extracción de activos de mercado (yfinance)
    for nombre, t in tickers_macro.items():
        datos[nombre] = {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None}
        try:
            hist = yf.Ticker(t).history(period="1y")
            if len(hist) >= 2:
                actual = hist['Close'].iloc[-1]
                
                datos[nombre]["valor"] = float(actual)
                datos[nombre]["var_diaria"] = float(((actual / hist['Close'].iloc[-2]) - 1) * 100)
                
                if len(hist) >= 21:
                    datos[nombre]["var_1m"] = float(((actual / hist['Close'].iloc[-21]) - 1) * 100)
                if len(hist) >= 126:
                    datos[nombre]["var_6m"] = float(((actual / hist['Close'].iloc[-126]) - 1) * 100)
                if len(hist) >= 250:
                    datos[nombre]["var_1y"] = float(((actual / hist['Close'].iloc[0]) - 1) * 100)
        except: pass

    # 2. Extracción de variables macroeconómicas de EE.UU. (API FRED)
    try:
        if "FRED_API_KEY" in st.secrets:
            api_key = st.secrets["FRED_API_KEY"]
            fred_series = {
                "Tasa FED (%)": {"id": "FEDFUNDS", "units": "lin"},
                "Inflación EE.UU YoY (%)": {"id": "CPIAUCSL", "units": "pc1"},
                "Desempleo EE.UU (%)": {"id": "UNRATE", "units": "lin"}
            }
            
            for nombre, config in fred_series.items():
                # Inicializamos todas las columnas para que la tabla no rompa
                datos[nombre] = {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None}
                
                # Solicitamos 12 publicaciones (1 año de datos mensuales)
                url = f"https://api.stlouisfed.org/fred/series/observations?series_id={config['id']}&api_key={api_key}&file_type=json&units={config['units']}&sort_order=desc&limit=12"
                
                try:
                    res = requests.get(url, timeout=5)
                    if res.status_code == 200:
                        obs = res.json().get("observations", [])
                        
                        # Filtramos cualquier dato ausente que FRED devuelva como "."
                        valid_obs = [float(o["value"]) for o in obs if o["value"] != "."]
                        
                        if len(valid_obs) >= 1:
                            act = valid_obs[0]
                            datos[nombre]["valor"] = act
                            
                            if len(valid_obs) >= 2:
                                datos[nombre]["var_diaria"] = act - valid_obs[1] 
                                datos[nombre]["var_1m"] = act - valid_obs[1] 
                            
                            if len(valid_obs) >= 7:
                                datos[nombre]["var_6m"] = act - valid_obs[6]
                                
                            if len(valid_obs) >= 12:
                                datos[nombre]["var_1y"] = act - valid_obs[11]
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

# --- MOTOR DE INTELIGENCIA ARTIFICIAL ---
@st.cache_data(ttl=3600)
def generar_analisis_ia(macro_arg, macro_int, brecha):
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ **Falta la clave API de Gemini.** Configura `GEMINI_API_KEY` en los Secrets de Streamlit."
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        
        rp = macro_arg.get('riesgo_pais')
        rp_val = rp['valor'] if rp else 'N/D'
        
        merv = macro_arg.get('merval', {})
        merv_val = f"{merv.get('valor', 0):.0f}"
        merv_var = merv.get('var_diaria')
        merv_var_str = f"Var Diaria: {merv_var:.2f}%" if merv_var is not None else "N/D"
        merv_6m = f"Var 6M: {merv.get('var_6m', 0):.2f}%" if merv.get('var_6m') is not None else ""
        
        brecha_str = f"{brecha:.2f}%" if brecha is not None else 'N/D'
        
        prompt = f"""
        Eres un asesor financiero didáctico, claro y amigable.
        Analiza el siguiente tablero macroeconómico de Argentina y EE.UU. 
        Presta especial atención a las tendencias de 1 Mes, 6 Meses y 1 Año para deducir en qué etapa del ciclo económico nos encontramos.
        
        Tu respuesta debe tener EXACTAMENTE dos partes:
        
        ### 1. Visión Estratégica General
        Redacta un análisis en 4 bullet points indicando oportunidades de inversión claras, explicadas con un lenguaje sencillo, fácil de entender para un inversor principiante o intermedio. Si usas jerga financiera, explícala brevemente en términos cotidianos.
        
        ### 2. Perspectiva de los 11 Sectores (Clasificación GICS)
        Basándote ESTRICTAMENTE en los datos macroeconómicos provistos y sus tendencias históricas, usando deducción lógica, dibuja una tabla en formato Markdown con los 11 sectores de la economía.
        La tabla debe tener exactamente 3 columnas:
        | Sector (GICS) | Veredicto (Atractivo / Neutral / Cautela) | Justificación Macroeconómica (1 oración sencilla) |
        
        Lista estricta de sectores a incluir: Tecnología, Financiero, Salud, Consumo Discrecional, Consumo Masivo, Energía, Industrial, Materiales Básicos, Servicios Públicos, Bienes Raíces, y Comunicaciones.
        
        REGLA ESTRICTA: NO utilices etiquetas HTML bajo ninguna circunstancia. Devuelve únicamente texto plano y formato Markdown puro. Evita saludos iniciales.
        
        --- DATOS ARGENTINA ---
        Riesgo País: {rp_val}
        Merval: {merv_val} ({merv_var_str} | {merv_6m})
        Brecha Cambiaria (CCL vs Oficial): {brecha_str}
        
        --- DATOS INTERNACIONALES (CON HISTORIAL) ---
        """
        for nombre, datos in macro_int.items():
            v = datos.get('valor', 'N/D')
            var_d = datos.get('var_diaria')
            var_1m = datos.get('var_1m')
            var_6m = datos.get('var_6m')
            var_1y = datos.get('var_1y')
            
            str_d = f"Diaria: {var_d:.2f}%" if var_d is not None else "N/D"
            str_1m = f" | 1M: {var_1m:.2f}%" if var_1m is not None else ""
            str_6m = f" | 6M: {var_6m:.2f}%" if var_6m is not None else ""
            str_1y = f" | 1Y: {var_1y:.2f}%" if var_1y is not None else ""
            
            prompt += f"{nombre}: {v} ({str_d}{str_1m}{str_6m}{str_1y})\n"
            
        modelos_a_probar = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        for modelo in modelos_a_probar:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
            res = requests.post(url, headers=headers, json=payload, timeout=45)
            
            if res.status_code == 200:
                data = res.json()
                texto_ia = data['candidates'][0]['content']['parts'][0]['text']
                # Eliminación defensiva de código HTML residual
                texto_limpio = texto_ia.replace('</div>', '').replace('<div>', '').strip()
                return texto_limpio
            elif res.status_code == 503:
                continue
            else:
                return f"❌ **Error del servidor de IA:** Código {res.status_code} en {modelo}. Respuesta: {res.text}"
        
        return "⚠️ **Servidores de Google Saturados:** En este momento la API gratuita está experimentando un pico de tráfico global. Por favor, intenta sincronizar los datos nuevamente en unos minutos."
            
    except Exception as e:
        return f"❌ **Error crítico de conexión:** No se pudo procesar la IA. Detalle: {e}"
