import requests
import feedparser
import yfinance as yf
import streamlit as st

# Usamos User-Agent para que los servidores no bloqueen nuestra lectura (Evitar 403)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

@st.cache_data(ttl=1800)  # Se actualiza cada 30 minutos para no saturar
def obtener_macro_argentina():
    datos = {"dolares": [], "riesgo_pais": None, "merval": None}
    
    # 1. Dólar (Vía DolarAPI - 100% estable)
    try:
        res = requests.get("https://dolarapi.com/v1/dolares", timeout=5)
        if res.status_code == 200:
            for d in res.json():
                if d["casa"] in ["oficial", "blue", "bolsa", "contadoconliqui", "tarjeta"]:
                    nombre = "MEP" if d["casa"] == "bolsa" else "CCL" if d["casa"] == "contadoconliqui" else d["casa"].capitalize()
                    datos["dolares"].append({"nombre": nombre, "compra": d["compra"], "venta": d["venta"]})
    except: pass
    
    # 2. Riesgo País (Vía endpoint JSON oculto de Ámbito Financiero - Muy robusto)
    try:
        res_rp = requests.get("https://mercados.ambito.com//riesgopais/info", headers=HEADERS, timeout=5)
        if res_rp.status_code == 200:
            rp_json = res_rp.json()
            datos["riesgo_pais"] = {"valor": rp_json.get("valor"), "variacion": rp_json.get("variacion")}
    except: pass

    # 3. Merval (Vía Yahoo Finance)
    try:
        merv = yf.Ticker("^MERV").history(period="2d")
        if len(merv) >= 2:
            act = merv['Close'].iloc[-1]
            prev = merv['Close'].iloc[-2]
            datos["merval"] = {"valor": act, "var": ((act / prev) - 1) * 100}
    except: pass

    return datos

@st.cache_data(ttl=3600)
def obtener_macro_internacional():
    # Usamos YFinance para capturar el macro mundial sin scraping frágil
    # ^TNX (Bono 10 años) actúa como termómetro de las tasas de la FED
    tickers_macro = {"Petróleo Crudo (WTI)": "CL=F", "S&P 500 (Mercado Global)": "^GSPC", "Tasas FED (Bono 10Y EE.UU)": "^TNX"}
    datos = {}
    for nombre, t in tickers_macro.items():
        try:
            hist = yf.Ticker(t).history(period="2d")
            if len(hist) >= 2:
                actual = hist['Close'].iloc[-1]
                previo = hist['Close'].iloc[-2]
                datos[nombre] = {"valor": actual, "var": ((actual / previo) - 1) * 100}
        except: pass
    return datos

@st.cache_data(ttl=1800)
def obtener_noticias_acciones(lista_tickers):
    noticias = {}
    # Limitamos a los primeros 6 tickers para mantener la app ultrarrápida
    for ticker in lista_tickers[:6]:
        try:
            # RSS Oficial de Yahoo Finance
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
            feed = feedparser.parse(url)
            entradas = []
            for entry in feed.entries[:3]:  # Top 3 noticias por empresa
                entradas.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "fecha": entry.published
                })
            noticias[ticker] = entradas
        except:
            noticias[ticker] = []
    return noticias
