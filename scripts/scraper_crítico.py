import json
import requests
import feedparser
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import urllib3
import xml.etree.ElementTree as ET

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def buscar_dato_historico(datos, dias_atras):
    fecha_buscada = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
    return next((d for d in reversed(datos) if d["fecha"] <= fecha_buscada), None)

def obtener_macro_arg_critica():
    datos = {"reservas_m": None, "reservas_fecha": None, "tasa_bcra": None, "dolares": [], "riesgo_pais_actual": None, "riesgo_pais_1m": None, "inflacion_mensual": None, "inflacion_interanual": None, "emae_ultimo": None, "emae_fecha": None}
    
    # Riesgo País Histórico (Validado)
    try:
        r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            datos_rp = r.json()
            datos["riesgo_pais_actual"] = {"valor": datos_rp[-1]["valor"], "fecha": datos_rp[-1]["fecha"]}
            d_1m = buscar_dato_historico(datos_rp, 30)
            if d_1m: datos["riesgo_pais_1m"] = {"valor": d_1m["valor"], "fecha": d_1m["fecha"]}
    except: pass
    
    # Reservas (Nueva Fuente Validada)
    try:
        r = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            res_data = r.json()[-1]
            datos["reservas_m"] = res_data["valor"]
            datos["reservas_fecha"] = res_data["fecha"]
    except: pass
    
    # Inflación (Mensual e Interanual)
    try:
        r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            inf_data = r.json()
            datos["inflacion_mensual"] = float(inf_data[-1]["valor"])
            datos["inflacion_interanual"] = float(inf_data[-1].get("interanual", 0))
    except: pass

    # EMAE (Actividad - Con sello de tiempo)
    try:
        r = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=143.3_NO_PR_2004_A_21&limit=1&sort=desc&format=json", timeout=8)
        if r.status_code == 200:
            d = r.json().get("data", [])[0]
            datos["emae_fecha"] = d[0]
            datos["emae_ultimo"] = d[1]
    except: pass

    # Dólares y Tasa
    try:
        rd = requests.get("https://dolarapi.com/v1/dolares", timeout=8)
        if rd.status_code == 200:
            datos["dolares"] = [{"nombre": d["nombre"], "compra": d["compra"], "venta": d["venta"]} for d in rd.json() if d["nombre"] in ["Oficial", "Blue", "CCL", "MEP", "Mayorista"]]
    except: pass
    
    try:
        rt = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazo-fijo", headers=HEADERS, timeout=8)
        if rt.status_code == 200:
            bna = next((b for b in rt.json() if "nacion" in b["entidad"].lower()), None)
            if bna: datos["tasa_bcra"] = float(bna["tnaClientes"])
    except: pass
    
    return datos

def calcular_momentums_hist(serie_precios):
    v1, v6, v12 = None, None, None
    if len(serie_precios) >= 21: v1 = float(((serie_precios.iloc[-1] / serie_precios.iloc[-21]) - 1) * 100)
    if len(serie_precios) >= 126: v6 = float(((serie_precios.iloc[-1] / serie_precios.iloc[-126]) - 1) * 100)
    if len(serie_precios) >= 250: v12 = float(((serie_precios.iloc[-1] / serie_precios.iloc[0]) - 1) * 100)
    return v1, v6, v12

def obtener_macro_int_critica():
    tm = {"S&P 500 (Global)": "^GSPC", "Nasdaq (Tech)": "^IXIC", "Oro (Refugio)": "GC=F", "Petróleo Crudo (WTI)": "CL=F", "DXY (Índice Dólar)": "DX-Y.NYB", "VIX (Miedo)": "^VIX", "Bono 10Y EE.UU (%)": "^TNX"}
    datos = {}
    try:
        hd = yf.download(list(tm.values()), period="1y", progress=False)
        if not hd.empty and 'Close' in hd:
            dc = hd['Close']
            for n, t in tm.items():
                if t in dc.columns:
                    s = dc[t].dropna()
                    if len(s) >= 2:
                        act = float(s.iloc[-1])
                        v1, v6, v12 = calcular_momentums_hist(s)
                        datos[n] = {"valor": act, "var_diaria": float(((act/s.iloc[-2])-1)*100), "var_1m": v1, "var_6m": v6, "var_1y": v12}
    except: pass
    return datos

def extraer_merval():
    # Volúmenes en pesos (Dinero real, no nominales)
    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    general = ["AGRO.BA", "AUSO.BA", "BHIP.BA", "CAPX.BA", "CGPA2.BA", "GCLA.BA", "HAVA.BA", "MORI.BA", "OEST.BA", "SAMI.BA"]
    tkrs = lider + general
    datos = {}
    
    # 1Y histórico para Momentums del Merval (Para evitar Alucinaciones de la IA)
    try:
        hist = yf.download(tkrs, period="1y", progress=False)
        precios_hist = hist['Close'] if not hist.empty and 'Close' in hist else pd.DataFrame()
    except: precios_hist = pd.DataFrame()

    for i in range(0, len(tkrs), 10):
        lote = tkrs[i:i+10]
        try:
            ts = yf.Tickers(" ".join(lote))
            for t in lote:
                ti = ts.tickers[t]
                info = ti.info
                hist = ti.history(period="1mo")
                p = info.get("currentPrice", info.get("regularMarketPrice"))
                if p is None and not hist.empty: p = float(hist["Close"].iloc[-1])
                if p is not None and p > 0:
                    vol_nominal = info.get("averageVolume", info.get("regularMarketVolume", 0))
                    vol_pesos_m = (vol_nominal * p) / 1_000_000  # VOLUMEN EN MILLONES DE PESOS REALES
                    
                    # Momentum Histórico
                    v1, v6, v12 = None, None, None
                    if not precios_hist.empty and t in precios_hist.columns:
                        s_hist = precios_hist[t].dropna()
                        v1, v6, v12 = calcular_momentums_hist(s_hist)

                    datos[t] = {
                        "precio": p, "pe": info.get("trailingPE"), "pbv": info.get("priceToBook"),
                        "volumen_pesos_m": vol_pesos_m,
                        "var_1m": v1, "var_6m": v6
                    }
                    if len(hist) >= 14:
                        delta = hist['Close'].diff()
                        g = delta.where(delta > 0, 0.0).rolling(14).mean()
                        l = -delta.where(delta < 0, 0.0).rolling(14).mean()
                        rs = g / l
                        datos[t]["rsi"] = float(100 - (100 / (1 + rs.iloc[-1]))) if l.iloc[-1] != 0 else 100
        except Exception as e: print(f"Error {t}: {e}")
    return datos

if __name__ == "__main__":
    t_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d_m = extraer_merval()
    d_c = obtener_macro_arg_critica()
    d_i = obtener_macro_int_critica()
    out = {"timestamp": t_stamp, "cotizaciones_merval": d_m, "macro_arg_critica": d_c, "macro_int_critica": d_i}
    with open("datos_criticos.json", "w", encoding="utf-8") as f: json.dump(out, f, indent=4)
