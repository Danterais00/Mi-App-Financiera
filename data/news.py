# --- NUEVO MOTOR DE INTELIGENCIA ARTIFICIAL (CONECTOR DIRECTO REST API) ---
@st.cache_data(ttl=3600)
def generar_analisis_ia(macro_arg, macro_int, brecha):
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ **Falta la clave API de Gemini.** Configura `GEMINI_API_KEY` en los Secrets de Streamlit."
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        
        # 1. Empaquetamos los datos para la IA
        rp = macro_arg.get('riesgo_pais')
        rp_val = rp['valor'] if rp else 'N/D'
        merv = macro_arg.get('merval')
        merv_val = f"{merv['valor']:.0f} (Var: {merv['var']:.2f}%)" if merv else 'N/D'
        brecha_str = f"{brecha:.2f}%" if brecha is not None else 'N/D'
        
        # 2. Creamos el Prompt Estratégico
        prompt = f"""
        Eres un experto estratega financiero de Wall Street asesorando a un fondo institucional.
        Analiza el siguiente tablero macroeconómico de Argentina y EE.UU. 
        Redacta un análisis estratégico directo en 4 bullet points indicando oportunidades de inversión claras 
        (ej: CEDEARs, Renta Fija Internacional, Acciones locales, Carry Trade, etc.).
        Sé conciso, profesional, y justifica tu racional cruzando los datos provistos. Evita saludos, ve directo al análisis.
        
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
            
        # 3. BYPASS DEL SDK: Conexión HTTP pura a los servidores de Google
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        # Hacemos la llamada directa
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"❌ **Error del servidor de IA:** Código {res.status_code} - Revisa que la API Key sea correcta."
            
    except Exception as e:
        return f"❌ **Error crítico de conexión:** No se pudo procesar la IA. Detalle: {e}"
