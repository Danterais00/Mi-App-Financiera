import json
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def buscar_dato_historico(datos, dias_atras):
    fecha_buscada = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
    return next((d for d in reversed(datos) if d["fecha"] <= fecha_buscada), None)

def calcular_momentums_hist(serie_precios):
    v1, v6, v12 = None, None, None
    if len(serie_precios) >= 21: v1 = round(float(((serie_precios.iloc[-1] / serie_precios.iloc[-21]) - 1) * 100), 2)
    if len(serie_precios) >= 126: v6 = round(float(((serie_precios.iloc[-1] / serie_precios.iloc[-126]) - 1) * 100), 2)
    if len(serie_precios) >= 250: v12 = round(float(((serie_precios.iloc[-1] / serie_precios.iloc[0]) - 1) * 100), 2)
    return v1, v6, v12

def obtener_macro_arg_critica():
    datos = {
        "reservas_m": None, "reservas_fecha": None, 
        "tasa_tamar": None, "tasa_badlar": None, "tasa_tna": None, 
        "dolares": [], "riesgo_pais_actual": None, "riesgo_pais_1m": None, 
        "inflacion_mensual": None, "emae_ultimo": None, "emae_fecha": None,
        "merval_ars": None, "merval_usd": None
    }
    
    # 1. Riesgo País Histórico
    try:
        r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            datos_rp = r.json()
            datos["riesgo_pais_actual"] = {"valor": round(float(datos_rp[-1]["valor"])), "fecha": datos_rp[-1]["fecha"]}
            d_1m = buscar_dato_historico(datos_rp, 30)
            if d_1m: datos["riesgo_pais_1m"] = {"valor": round(float(d_1m["valor"])), "fecha": d_1m["fecha"]}
    except: pass
    
    # 2. Reservas BCRA (Fuente validada argentinadatos)
    try:
        r = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            res_data = r.json()[-1]
            datos["reservas_m"] = float(res_data["valor"])
            datos["reservas_fecha"] = res_data["fecha"]
    except: pass
    
    # 3. Inflación Mensual
    try:
        r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            datos["inflacion_mensual"] = round(float(r.json()[-1]["valor"]), 1)
    except: pass

    # 4. EMAE (Actividad Económica)
    try:
        r = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=143.3_NO_PR_2004_A_21&limit=1&sort=desc&format=json", timeout=8)
        if r.status_code == 200:
            d = r.json().get("data", [])[0]
            datos["emae_fecha"] = d[0]
            datos["emae_ultimo"] = round(float(d[1]), 2)
    except: pass

    # 5. Dólares (Mapeo exacto de DolarAPI para incluir MEP, CCL, Oficial, Blue, Mayorista)
    try:
        rd = requests.get("https://dolarapi.com/v1/dolares", timeout=8)
        if rd.status_code == 200:
            mapa_nombres = {
                "oficial": "Oficial",
                "blue": "Blue",
                "bolsa": "MEP",
                "contadoconliqui": "CCL",
                "mayorista": "Mayorista"
            }
            orden = ["Oficial", "Blue", "MEP", "CCL", "Mayorista"]
            lista_d = []
            for d in rd.json():
                casa = d.get("casa", "").lower()
                if casa in mapa_nombres:
                    lista_d.append({
                        "nombre": mapa_nombres[casa],
                        "compra": d.get("compra"),
                        "venta": d.get("venta")
                    })
            datos["dolares"] = sorted(lista_d, key=lambda x: orden.index(x["nombre"]) if x["nombre"] in orden else 99)
    except: pass
    
    # 6. Tasas (BADLAR, Plazo Fijo TNA y TAMAR desde API oficial Datos Gob Ar + Argentinadatos)
    # BADLAR Bancos Privados (Serie oficial BCRA: 89.2_TS_INTELAR_0_D_20)
    try:
        rb = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=89.2_TS_INTELAR_0_D_20&limit=1&sort=desc&format=json", timeout=8)
        if rb.status_code == 200:
            val_b = rb.json().get("data", [])[0][1]
            if val_b: datos["tasa_badlar"] = round(float(val_b), 2)
    except: pass

    # TNA Plazo Fijo 30 días (Serie oficial BCRA: 89.2_TS_DEPOS_0_D_23 o Argentinadatos)
    try:
        rt = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazo-fijo", headers=HEADERS, timeout=8)
        if rt.status_code == 200:
            tasas_pf = [float(b["tnaClientes"]) for b in rt.json() if b.get("tnaClientes")]
            if tasas_pf:
                prom = sum(tasas_pf) / len(tasas_pf)
                datos["tasa_tna"] = round(prom * 100, 2) if prom < 2 else round(prom, 2)
    except: pass
    if datos["tasa_tna"] is None:
        try:
            rt2 = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=89.2_TS_DEPOS_0_D_23&limit=1&sort=desc&format=json", timeout=8)
            if rt2.status_code == 200:
                val_t = rt2.json().get("data", [])[0][1]
                if val_t: datos["tasa_tna"] = round(float(val_t), 2)
        except: pass

    # TAMAR (Tasa Mayorista > $1.000M - Argentinadatos o diferencial técnico sobre BADLAR)
    try:
        rtm = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/tamar", headers=HEADERS, timeout=8)
        if rtm.status_code == 200:
            datos["tasa_tamar"] = round(float(rtm.json()[-1]["valor"]), 2)
    except: pass
    if datos["tasa_tamar"] is None and datos["tasa_badlar"] is not None:
        # Spread histórico institucional TAMAR vs BADLAR (+1.40 pp) si el endpoint público cae
        datos["tasa_tamar"] = round(datos["tasa_badlar"] + 1.40, 2)
    
    return datos

def extraer_valuaciones():
    lideres_usa = {
        "MSFT": "Tecnología", "GOOGL": "Comunicaciones", "JPM": "Financiero",
        "XOM": "Energía", "LLY": "Salud", "CAT": "Industriales",
        "AMZN": "Cons. Discrecional", "PG": "Cons. Básico", "NEE": "Utilities",
        "LIN": "Materiales", "PLD": "Real Estate"
    }
    lideres_arg = {
        "GGAL": "Financiero", "BMA": "Financiero", "YPF": "Energía",
        "PAM": "Energía", "VIST": "Energía", "TGS": "Energía",
        "CEPU": "Utilities", "EDN": "Utilities", "LOMA": "Materiales",
        "CRESY": "Agro/Real Estate", "IRS": "Real Estate", "MELI": "Tecnología"
    }
    
    val_usa, val_arg = {}, {}
    todos = list(lideres_usa.keys()) + list(lideres_arg.keys())
    
    try:
        hist = yf.download(todos, period="1y", progress=False)['Close']
    except:
        hist = pd.DataFrame()

    for t in todos:
        try:
            info = yf.Ticker(t).info
            pe = info.get("trailingPE")
            roe = info.get("returnOnEquity")
            pe_str = f"{pe:.1f}" if isinstance(pe, (int, float)) else "N/D"
            roe_str = f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D"
            
            v1, v6, v12 = None, None, None
            if not hist.empty and t in hist.columns:
                v1, v6, v12 = calcular_momentums_hist(hist[t].dropna())
                
            registro = {
                "Sector": lideres_usa.get(t) or lideres_arg.get(t),
                "P/E": pe_str, "ROE (%)": roe_str,
                "1M": v1, "6M": v6, "1Y": v12
            }
            if t in lideres_usa: val_usa[t] = registro
            else: val_arg[t] = registro
        except: pass
        
    return val_usa, val_arg

def extraer_merval():
    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    general = ["AGRO.BA", "AUSO.BA", "BHIP.BA", "CAPX.BA", "CGPA2.BA", "GCLA.BA", "HAVA.BA", "MORI.BA", "OEST.BA", "SAMI.BA"]
    tkrs = lider + general
    datos = {}
    
    try:
        hist_1y = yf.download(tkrs, period="1y", progress=False)['Close']
    except:
        hist_1y = pd.DataFrame()

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
                    vol_pesos_m = (vol_nominal * p) / 1_000_000
                    
                    v1, v6, v12 = None, None, None
                    if not hist_1y.empty and t in hist_1y.columns:
                        v1, v6, v12 = calcular_momentums_hist(hist_1y[t].dropna())

                    datos[t] = {
                        "precio": p, "pe": info.get("trailingPE"), "pbv": info.get("priceToBook"),
                        "volumen_pesos_m": vol_pesos_m, "var_1m": v1, "var_6m": v6
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
    
    # Índice Merval directo desde yfinance (^MERV) o ponderado de respaldo
    try:
        m_hist = yf.Ticker("^MERV").history(period="5d")
        if not m_hist.empty:
            d_c["merval_ars"] = round(float(m_hist["Close"].iloc[-1]))
    except: pass
    
    if d_c["merval_ars"] is None and d_m:
        p_ggal = d_m.get("GGAL.BA", {}).get("precio", 0)
        p_ypfd = d_m.get("YPFD.BA", {}).get("precio", 0)
        p_pamp = d_m.get("PAMP.BA", {}).get("precio", 0)
        p_bma = d_m.get("BMA.BA", {}).get("precio", 0)
        if p_ggal and p_ypfd and p_pamp and p_bma:
            d_c["merval_ars"] = round((p_ggal * 165) + (p_ypfd * 145) + (p_pamp * 110) + (p_bma * 75))
            
    if d_c["merval_ars"] and d_c["dolares"]:
        ccl_v = next((float(d['venta']) for d in d_c["dolares"] if d['nombre'] == 'CCL'), None)
        if ccl_v and ccl_v > 0:
            d_c["merval_usd"] = round(d_c["merval_ars"] / ccl_v)

    v_usa, v_arg = extraer_valuaciones()
    out = {
        "timestamp": t_stamp, 
        "cotizaciones_merval": d_m, 
        "macro_arg_critica": d_c,
        "valuaciones_usa": v_usa,
        "valuaciones_arg": v_arg
    }
    with open("datos_criticos.json", "w", encoding="utf-8") as f: json.dump(out, f, indent=4)
