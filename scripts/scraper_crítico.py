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

def obtener_tna_pf_robusta():
    try:
        rt = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazo-fijo", headers=HEADERS, timeout=8)
        if rt.status_code == 200:
            tasas_pf = []
            for b in rt.json():
                v = b.get("tnaClientes")
                if v is not None:
                    try:
                        vf = float(v)
                        if vf > 0:
                            tasas_pf.append(vf * 100 if vf < 2 else vf)
                    except: pass
            if tasas_pf:
                return round(sum(tasas_pf) / len(tasas_pf), 2)
    except: pass

    series_pf = ["89.2_TS_DEPOS_0_D_23", "168.1_T_PF_30_59_0_M_26"]
    for s_id in series_pf:
        try:
            rt2 = requests.get(f"https://apis.datos.gob.ar/series/api/series/?ids={s_id}&limit=5&sort=desc&format=json", timeout=8)
            if rt2.status_code == 200:
                filas = rt2.json().get("data", [])
                for fila in filas:
                    if len(fila) > 1 and fila[1] is not None:
                        return round(float(fila[1]), 2)
        except: pass

    return None

def obtener_variacion_ccl_1m():
    try:
        r = requests.get("https://api.argentinadatos.com/v1/cotizaciones/dolares/contadoconliqui", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            hist_ccl = r.json()
            if hist_ccl:
                act = float(hist_ccl[-1]["venta"])
                d_1m = buscar_dato_historico(hist_ccl, 30)
                if d_1m and float(d_1m["venta"]) > 0:
                    return round(((act / float(d_1m["venta"])) - 1) * 100, 2)
    except: pass
    return None

def obtener_macro_arg_critica():
    datos = {
        "reservas_m": None, "reservas_fecha": None, 
        "tasa_tamar": None, "tasa_badlar": None, "tasa_tna": None, 
        "dolares": [], "ccl_var_1m": None,
        "riesgo_pais_actual": None, 
        "riesgo_pais_1m": None, "riesgo_pais_var_1m_pb": None, "riesgo_pais_var_1m_pct": None,
        "riesgo_pais_6m": None, "riesgo_pais_var_6m_pb": None, "riesgo_pais_var_6m_pct": None,
        "inflacion_mensual": None, "inflacion_fecha": None,
        "emae_ultimo": None, "emae_fecha": None,
        "merval_ars": None, "merval_usd": None,
        "al30_precio": None, "al30_var_1m": None
    }
    
    # 1. Riesgo País Histórico (Actual, 1M y 6M pre-calculados)
    try:
        r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            datos_rp = r.json()
            val_act = round(float(datos_rp[-1]["valor"]))
            datos["riesgo_pais_actual"] = {"valor": val_act, "fecha": datos_rp[-1]["fecha"]}
            
            d_1m = buscar_dato_historico(datos_rp, 30)
            if d_1m:
                val_1m = round(float(d_1m["valor"]))
                datos["riesgo_pais_1m"] = {"valor": val_1m, "fecha": d_1m["fecha"]}
                datos["riesgo_pais_var_1m_pb"] = val_act - val_1m
                if val_1m > 0: datos["riesgo_pais_var_1m_pct"] = round(((val_act / val_1m) - 1) * 100, 1)
                
            d_6m = buscar_dato_historico(datos_rp, 180)
            if d_6m:
                val_6m = round(float(d_6m["valor"]))
                datos["riesgo_pais_6m"] = {"valor": val_6m, "fecha": d_6m["fecha"]}
                datos["riesgo_pais_var_6m_pb"] = val_act - val_6m
                if val_6m > 0: datos["riesgo_pais_var_6m_pct"] = round(((val_act / val_6m) - 1) * 100, 1)
    except: pass
    
    # 2. Reservas BCRA
    try:
        r_gob = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=300.1_AP_ACT_RESTER_0_M_21&limit=1&sort=desc&format=json", timeout=8)
        if r_gob.status_code == 200:
            d_gob = r_gob.json().get("data", [])[0]
            if d_gob[1]:
                val_r = float(d_gob[1])
                datos["reservas_m"] = round(val_r / 1_000_000) if val_r > 1_000_000_000 else round(val_r)
                datos["reservas_fecha"] = d_gob[0]
    except: pass

    if datos["reservas_m"] is None:
        try:
            r = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", headers=HEADERS, timeout=8)
            if r.status_code == 200:
                res_data = r.json()[-1]
                val_r = res_data.get("valor") or res_data.get("reservas")
                if val_r:
                    datos["reservas_m"] = round(float(val_r))
                    datos["reservas_fecha"] = res_data.get("fecha")
        except: pass
    
    # 3. Inflación Mensual
    try:
        r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            ult_inf = r.json()[-1]
            datos["inflacion_mensual"] = round(float(ult_inf["valor"]), 1)
            datos["inflacion_fecha"] = ult_inf.get("fecha")
    except: pass

    # 4. EMAE (Actividad Económica)
    try:
        r = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=143.3_NO_PR_2004_A_21&limit=1&sort=desc&format=json", timeout=8)
        if r.status_code == 200:
            d = r.json().get("data", [])[0]
            datos["emae_fecha"] = d[0]
            datos["emae_ultimo"] = round(float(d[1]), 2)
    except: pass

    # 5. Dólares (Oficial, Blue, MEP, CCL, Mayorista) + Variación 1M CCL
    try:
        rd = requests.get("https://dolarapi.com/v1/dolares", timeout=8)
        if rd.status_code == 200:
            mapa_nombres = {
                "oficial": "Oficial", "blue": "Blue", "bolsa": "MEP",
                "contadoconliqui": "CCL", "mayorista": "Mayorista"
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
    datos["ccl_var_1m"] = obtener_variacion_ccl_1m()
    
    # 6. Tasas (BADLAR, TNA Plazo Fijo 30D y TAMAR)
    try:
        rb = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=89.2_TS_INTELAR_0_D_20&limit=5&sort=desc&format=json", timeout=8)
        if rb.status_code == 200:
            for fila in rb.json().get("data", []):
                if len(fila) > 1 and fila[1] is not None:
                    datos["tasa_badlar"] = round(float(fila[1]), 2)
                    break
    except: pass

    datos["tasa_tna"] = obtener_tna_pf_robusta()
    if datos["tasa_tna"] is None and datos["tasa_badlar"] is not None:
        datos["tasa_tna"] = round(datos["tasa_badlar"] - 2.10, 2)

    try:
        rtm = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/tamar", headers=HEADERS, timeout=8)
        if rtm.status_code == 200:
            datos["tasa_tamar"] = round(float(rtm.json()[-1]["valor"]), 2)
    except: pass
    if datos["tasa_tamar"] is None and datos["tasa_badlar"] is not None:
        datos["tasa_tamar"] = round(datos["tasa_badlar"] + 3.20, 2)

    # 7. Bono AL30 (Precio y variación 1M vía yfinance AL30.BA)
    try:
        al30_hist = yf.Ticker("AL30.BA").history(period="2mo")
        if not al30_hist.empty:
            p_act = float(al30_hist["Close"].iloc[-1])
            datos["al30_precio"] = round(p_act, 2)
            if len(al30_hist) >= 21:
                p_1m = float(al30_hist["Close"].iloc[-21])
                if p_1m > 0:
                    datos["al30_var_1m"] = round(((p_act / p_1m) - 1) * 100, 2)
    except: pass
    
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
            fpe = info.get("forwardPE")
            roe = info.get("returnOnEquity")
            ev_ebitda = info.get("enterpriseToEbitda")
            fcf = info.get("freeCashflow")
            mcap = info.get("marketCap")
            de = info.get("debtToEquity")

            pe_str = f"{pe:.1f}" if isinstance(pe, (int, float)) else "N/D"
            fpe_str = f"{fpe:.1f}" if isinstance(fpe, (int, float)) else "N/D"
            roe_str = f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D"
            ev_ebitda_str = f"{ev_ebitda:.1f}" if isinstance(ev_ebitda, (int, float)) else "N/D"
            
            fcf_yield_str = "N/D"
            if isinstance(fcf, (int, float)) and isinstance(mcap, (int, float)) and mcap > 0:
                fcf_yield_str = f"{(fcf / mcap)*100:.1f}%"
                
            de_str = f"{de/100:.2f}" if isinstance(de, (int, float)) else "N/D"
            
            v1, v6, v12 = None, None, None
            if not hist.empty and t in hist.columns:
                v1, v6, v12 = calcular_momentums_hist(hist[t].dropna())
                
            registro = {
                "Sector": lideres_usa.get(t) or lideres_arg.get(t),
                "P/E": pe_str, "Forward P/E": fpe_str,
                "EV/EBITDA": ev_ebitda_str, "FCF Yield": fcf_yield_str, 
                "Debt/Equity": de_str, "ROE (%)": roe_str, 
                "1M": v1, "6M": v6, "1Y": v12
            }
            if t in lideres_usa: val_usa[t] = registro
            else: val_arg[t] = registro
        except: pass
        
    return val_usa, val_arg

def extraer_merval(ccl_var_1m=None):
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
                hist = ti.history(period="2mo")
                p = info.get("currentPrice", info.get("regularMarketPrice"))
                if p is None and not hist.empty: p = float(hist["Close"].iloc[-1])
                if p is not None and p > 0:
                    # Promedio exacto de volumen de las últimas 20 ruedas
                    if not hist.empty and "Volume" in hist.columns and len(hist["Volume"].dropna()) >= 5:
                        vol_20d = float(hist["Volume"].dropna().tail(20).mean())
                    else:
                        vol_20d = float(info.get("averageVolume", info.get("regularMarketVolume", 0)))
                    vol_pesos_m = (vol_20d * p) / 1_000_000
                    
                    v1, v6, v12 = None, None, None
                    if not hist_1y.empty and t in hist_1y.columns:
                        v1, v6, v12 = calcular_momentums_hist(hist_1y[t].dropna())
                    elif len(hist) >= 21:
                        v1 = round(float(((hist["Close"].iloc[-1] / hist["Close"].iloc[-21]) - 1) * 100), 2)

                    # Variación 1M estimada en USD (ajustada por variación CCL 1M)
                    v1_usd = None
                    if v1 is not None and ccl_var_1m is not None:
                        v1_usd = round((((1 + v1/100) / (1 + ccl_var_1m/100)) - 1) * 100, 2)

                    datos[t] = {
                        "precio": p, "pe": info.get("trailingPE"), "pbv": info.get("priceToBook"),
                        "volumen_pesos_m": vol_pesos_m, "var_1m": v1, "var_1m_usd": v1_usd, "var_6m": v6
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
    d_c = obtener_macro_arg_critica()
    d_m = extraer_merval(d_c.get("ccl_var_1m"))
    
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
