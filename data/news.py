import requests
import feedparser
import yfinance as yf
import pandas as pd
import streamlit as st

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
        res = requests.get("https://dolarapi.com/v1/dolares", timeout=5)
        if res.status_code == 200:
            for d in res.json():
                if d["casa"] in ["oficial", "blue", "bolsa", "contadoconliqui", "tarjeta"]:
                    nombre = "MEP" if d["casa"] == "bolsa" else "CCL" if d["casa"] == "contadoconliqui" else d["casa"].capitalize()
                    datos["dolares"].append({"nombre": nombre, "compra": d["compra"], "venta": d["venta"]})
    except: pass
    
    # 2. Riesgo País
    try:
        res_rp = requests.get("https://mercados.ambito.com//riesgopais/info", headers=HEADERS, timeout=5)
        if res_rp.status_code == 200:
            rp_json = res_rp.json()
            datos["riesgo_pais"] = {"valor": rp_json.get("valor"), "variacion": rp_json.get("variacion")}
    except: pass

    # 3. Inflación Argentina (IPC) 
    try:
        res_inf = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", timeout=5)
        if res_inf.status_code == 200:
            data_inf = res_inf.json()
            if data_inf:
                datos["inflacion"] = float(data_inf[-1]["valor"]) 
    except: pass

    # 4. Tasa de Referencia 
    try:
        res_tasa = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo", timeout=5)
        if res_tasa.status_code == 200:
            data_tasa = res_tasa.json()
            if data_tasa:
                datos["tasa_bcra"] = float(data_tasa[-1]["tasa"]) 
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
                url = f"https://api.stlouisfed.org/fred/series/observations?series_id={config['id']}&api_key={api_key}&file_type=json&units={config['units']}&sort_order=desc&limit=12"
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
                            if len(valid_obs) >= 12: datos[nombre]["var_1y"] = act - valid_obs[11]
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

# --- MOTOR DE IA CON AUTO-DESCUBRIMIENTO DE MODELOS ---
@st.cache_data(ttl=3600)
def generar_analisis_ia(macro_arg, macro_int, brecha):
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ **Falta la clave API de Gemini.** Configura `GEMINI_API_KEY` en los Secrets de Streamlit."
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        
        # EXTRACCIÓN Y FORMATEO SEGURO
        rp = macro_arg.get('riesgo_pais') or {}
        rp_val = rp.get('valor')
        rp_str = str(rp_val) if rp_val is not None else 'N/D'
        
        merv = macro_arg.get('merval', {})
        merv_val = merv.get('valor')
        merv_str = f"{merv_val:.0f}" if merv_val is not None else 'N/D'
        
        inf_val = macro_arg.get('inflacion')
        inf_arg = f"{inf_val:.1f}%" if inf_val is not None else 'N/D'
        
        tasa_val = macro_arg.get('tasa_bcra')
        tasa_arg = f"{tasa_val:.1f}%" if tasa_val is not None else 'N/D'
        
        brecha_str = f"{brecha:.2f}%" if brecha is not None else 'N/D'
        
        prompt = f"""
        Eres un Asesor Financiero Institucional (Portfolio Manager).
        Analiza el siguiente tablero macroeconómico global y local. 
        
        Tu respuesta debe tener EXACTAMENTE TRES partes en formato Markdown:
        
        ### 1. Visión Estratégica General
        Redacta un análisis en 4 bullet points indicando oportunidades de inversión en renta variable (acciones), deduciendo en qué etapa del ciclo nos encontramos.
        
        ### 2. Estrategia de Renta Fija y Cobertura (Argentina)
        Evalúa el Riesgo País, Brecha, Inflación local y Tasas de interés. 
        Recomienda de forma clara en bullet points cómo armar la cartera de bonos: 
        ¿Es momento de Carry Trade (LECAPs), cobertura inflacionaria (Bonos CER), ganancia de capital soberana (AL30/GD30) o riesgo corporativo (Obligaciones Negociables)? Justifica tu decisión matemáticamente.
        
        ### 3. Perspectiva de los 11 Sectores (Clasificación GICS)
        Basándote en los datos internacionales, dibuja una tabla Markdown de 3 columnas:
        | Sector (GICS) | Veredicto (Atractivo / Neutral / Cautela) | Justificación (1 oración) |
        
        REGLA ESTRICTA: NO uses HTML. Solo Markdown.
        
        --- DATOS ARGENTINA ---
        Riesgo País: {rp_str}
        Merval: {merv_str}
        Brecha Cambiaria (CCL vs Oficial): {brecha_str}
        Inflación Mensual (Último dato): {inf_arg}
        Tasa Referencia (TNA): {tasa_arg}
        
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
            
        # ---------------------------------------------------------
        # SOLUCIÓN MAESTRA: AUTO-DESCUBRIMIENTO DINÁMICO DE MODELOS
        # ---------------------------------------------------------
        
        # 1. Consultamos a Google qué modelos están habilitados para esta API Key
        url_list = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res_list = requests.get(url_list, timeout=10)
        
        if res_list.status_code != 200:
            return f"❌ **Error conectando con Google:** {res_list.text}"
            
        modelos_disponibles = res_list.json().get("models", [])
        modelos_validos = []
        
        # Filtramos solo los que soportan generación de texto
        for m in modelos_disponibles:
            if "generateContent" in m.get("supportedGenerationMethods", []):
                nombre_limpio = m.get("name", "").replace("models/", "")
                modelos_validos.append(nombre_limpio)
                
        if not modelos_validos:
            return "❌ **Permisos Insuficientes:** Tu API Key no tiene modelos de texto habilitados."
            
        # 2. Priorizamos los mejores modelos encontrados (Flash y Pro son mejores y más rápidos)
        def puntuar_modelo(nombre):
            puntos = 0
            if "flash" in nombre: puntos += 10
            if "pro" in nombre: puntos += 5
            if "1.5" in nombre: puntos += 2
            if "vision" in nombre: puntos -= 5 # Evitamos modelos enfocados solo en imágenes
            return puntos
            
        modelos_validos.sort(key=puntuar_modelo, reverse=True)
        
        # 3. Ejecutamos la petición usando el mejor modelo garantizado por Google
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        ultimo_error = ""
        # Intentamos con los 3 mejores modelos disponibles
        for modelo_elegido in modelos_validos[:3]:
            url_gen = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_elegido}:generateContent?key={api_key}"
            res_gen = requests.post(url_gen, headers=headers, json=payload, timeout=45)
            
            if res_gen.status_code == 200:
                texto_ia = res_gen.json()['candidates'][0]['content']['parts'][0]['text']
                return texto_ia.replace('</div>', '').replace('<div>', '').strip()
            else:
                ultimo_error = f"Falló {modelo_elegido} (Código: {res_gen.status_code})"
                continue
                
        return f"❌ **Error del servidor de IA:** Ninguno de los modelos autorizados respondió. Último fallo: {ultimo_error}"
        
    except Exception as e: 
        return f"❌ **Error crítico de conexión:** No se pudo procesar la IA. Detalle: {e}"
