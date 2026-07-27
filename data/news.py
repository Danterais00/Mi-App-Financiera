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
        # Ampliamos a 5d para evitar cortes de fin de semana
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
    tickers_macro = {
        "S&P 500 (Mercado Global)": "^GSPC",
        "Petróleo Crudo (WTI)": "CL=F", 
        "DXY (Índice Dólar)": "DX-Y.NYB",
        "Tasas FED (Bono 10Y EE.UU)": "^TNX"
    }
    datos = {}
    for nombre, t in tickers_macro.items():
        # INYECCIÓN: Forzamos la creación del dato en estado "Nulo" para que no desaparezca de la tabla
        datos[nombre] = {"valor": None, "var": None}
        try:
            # Ampliamos a 5d para garantizar lectura en fines de semana
            hist = yf.Ticker(t).history(period="5d")
            if len(hist) >= 2:
                actual = hist['Close'].iloc[-1]
                previo = hist['Close'].iloc[-2]
                if not pd.isna(actual) and not pd.isna(previo):
                    datos[nombre] = {"valor": actual, "var": ((actual / previo) - 1) * 100}
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
