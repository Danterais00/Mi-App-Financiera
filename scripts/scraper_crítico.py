import json
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

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

def obtener_tendencia_ccl():
    try:
        r = requests.get("https://api.argentinadatos.com/v1/cotizaciones/dolares/contadoconliqui", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            hist_ccl = r.json()
            if hist_ccl:
                act = float(hist_ccl[-1]["venta"])
                d_1m = buscar_dato_historico(hist_ccl, 30)
                d_3m = buscar_dato_historico(hist_ccl, 90)
                v1m = round(((act / float(d_1m["venta"])) - 1) * 100, 2) if (d_1m and float(d_1m["venta"]) > 0) else None
                v3m = round(((act / float(d_3m["venta"])) - 1) * 100, 2) if (d_3m and float(d_3m["venta"]) > 0) else None
                return v1m, v3m
    except: pass
    return None, None

def obtener_macro_arg_critica():
    datos = {
        "reservas_m": None, "reservas_fecha": None, "reservas_var_30d_m": None, "reservas_var_30d_pct": None,
        "tasa_tamar": None, "tasa_badlar": None, "tasa_tna": None, 
        "dolares": [], "ccl_var_1m": None, "ccl_var_3m": None,
        "riesgo_pais_actual": None, 
        "riesgo_pais_1m": None, "riesgo_pais_var_1m_pb": None, "riesgo_pais_var_1m_pct": None,
        "riesgo_pais_6m": None, "riesgo_pais_var_6m_pb": None, "riesgo_pais_var_6m_pct": None,
        "inflacion_mensual": None, "inflacion_fecha": None,
        "emae_ultimo": None, "emae_fecha": None,
        "merval_ars": None, "merval_usd": None,
        "al30_precio": None, "al30_var_1m": None
    }
    
    # 1. Riesgo País Histórico
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
    
    # 2. Reservas Brutas BCRA (API BCRA v4.0 Monetarias Variable 1 + Variación 30d)
    try:
        r_bcra = requests.get("https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/1?limit=25", headers=HEADERS, verify=False, timeout=10)
        if r_bcra.status_code == 200:
            results = r_bcra.json().get("results", [])
            if results and results[0].get("detalle"):
                detalle = results[0]["detalle"]
                ultimo = detalle[0]
                previo = detalle[-1]
                val_act = float(ultimo["valor"])
                val_prev = float(previo["valor"])
                datos["reservas_m"] = round(val_act)
                datos["reservas_fecha"] = ultimo["fecha"]
                datos["reservas_var_30d_m"] = round(val_act - val_prev)
                if val_prev > 0:
                    datos["reservas_var_30d_pct"] = round(((val_act / val_prev) - 1) * 100, 2)
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

    # 5. Dólares + Tendencia CCL 1M y 3M
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
    datos["ccl_var_1m"], datos["ccl_var_3m"] = obtener_tendencia_ccl()
    
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

    # 7. Bono AL30 (Data912 historical)
    try:
        r_d9 = requests.get("https://data912.com/historical/bonds/AL30", headers=HEADERS, timeout=8)
        if r_d9.status_code == 200:
            hist = r_d9.json()
            if hist:
                act = float(hist[-1]["c"])
                datos["al30_precio"] = round(act * 100, 2) if act < 2000 else round(act, 2)
                if len(hist) >= 21:
                    prev = float(hist[-21]["c"])
                    if prev > 0:
                        datos["al30_var_1m"] = round(((act / prev) - 1) * 100, 2)
    except: pass
    
    return datos

def extraer_valuaciones(ccl_venta=None):
    lideres_usa = {
        "SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF", "MSFT": "Tecnología", 
        "GOOGL": "Comunicaciones", "JPM": "Financiero", "XOM": "Energía", 
        "LLY": "Salud", "CAT": "Industriales", "AMZN": "Cons. Discrecional", 
        "PG": "Cons. Básico", "NEE": "Utilities", "LIN": "Materiales", "PLD": "Real Estate"
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
            precio = info.get("currentPrice") or info.get("regularMarketPrice")
            target = info.get("targetMeanPrice")
            peg = info.get("pegRatio") or info.get("trailingPegRatio")
            pe = info.get("trailingPE")
            fpe = info.get("forwardPE")
            pb = info.get("priceToBook")
            roe = info.get("returnOnEquity")
            ev_ebitda = info.get("enterpriseToEbitda")
            fcf = info.get("freeCashflow")
            mcap = info.get("marketCap")
            de = info.get("debtToEquity")
            curr = info.get("currency")
            fin_curr = info.get("financialCurrency")

            precio_str = f"${precio:.2f}" if isinstance(precio, (int, float)) else "N/D"
            target_str = f"${target:.2f}" if isinstance(target, (int, float)) else "N/D"
            upside_str = f"{((float(target)/float(precio))-1)*100:+.1f}%" if (isinstance(precio, (int, float)) and isinstance(target, (int, float)) and precio > 0) else "N/D"
            peg_str = f"{peg:.2f}" if isinstance(peg, (int, float)) and peg > 0 else "N/D"
            pe_str = f"{pe:.1f}" if isinstance(pe, (int, float)) else "N/D"
            fpe_str = f"{fpe:.1f}" if isinstance(fpe, (int, float)) else "N/D"
            pb_str = f"{pb:.2f}" if isinstance(pb, (int, float)) and pb > 0 else "N/D"
            roe_str = f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D"
            ev_ebitda_str = f"{ev_ebitda:.1f}" if isinstance(ev_ebitda, (int, float)) and ev_ebitda > 0 else "N/D"
            
            fcf_yield_str = "N/D"
            if isinstance(fcf, (int, float)) and isinstance(mcap, (int, float)) and mcap > 0:
                fcf_usd = None
                if fin_curr == curr:
                    fcf_usd = fcf
                elif fin_curr == "ARS" and curr == "USD" and ccl_venta and ccl_venta > 0:
                    fcf_usd = fcf / ccl_venta
                
                if fcf_usd is not None:
                    raw_yield = (fcf_usd / mcap) * 100
                    if -100 < raw_yield < 100:
                        fcf_yield_str = f"{raw_yield:.1f}%"
                
            de_str = f"{de/100:.2f}" if isinstance(de, (int, float)) else "N/D"
            
            v1, v6, v12 = None, None, None
            if not hist.empty and t in hist.columns:
                v1, v6, v12 = calcular_momentums_hist(hist[t].dropna())
                
            registro = {
                "Sector": lideres_usa.get(t) or lideres_arg.get(t),
                "Precio": precio_str, "Target": target_str, "Upside": upside_str, "PEG": peg_str,
                "P/E": pe_str, "Forward P/E": fpe_str, "P/BV": pb_str,
                "EV/EBITDA": ev_ebitda_str, "FCF Yield": fcf_yield_str, 
                "Debt/Equity": de_str, "ROE (%)": roe_str, 
                "1M": v1, "6M": v6, "1Y": v12
            }
            if t in lideres_usa: val_usa[t] = registro
            else: val_arg[t] = registro
        except: pass
        
    return val_usa, val_arg

def extraer_merval(ccl_var_1m=None, ccl_venta=None):
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
                    if not hist.empty and "Volume" in hist.columns and len(hist["Volume"].dropna()) >= 5:
                        vol_20d = float(hist["Volume"].dropna().tail(20).mean())
                    else:
                        vol_20d = float(info.get("averageVolume", info.get("regularMarketVolume", 0)))
                    vol_pesos_m = round((vol_20d * p) / 1_000_000, 2)
                    vol_usd_k = round(((vol_20d * p) / ccl_venta) / 1_000, 1) if (ccl_venta and ccl_venta > 0) else None
                    
                    v1, v6, v12 = None, None, None
                    if not hist_1y.empty and t in hist_1y.columns:
                        v1, v6, v12 = calcular_momentums_hist(hist_1y[t].dropna())
                    elif len(hist) >= 21:
                        v1 = round(float(((hist["Close"].iloc[-1] / hist["Close"].iloc[-21]) - 1) * 100), 2)

                    v1_usd = None
                    if v1 is not None and ccl_var_1m is not None:
                        v1_usd = round((((1 + v1/100) / (1 + ccl_var_1m/100)) - 1) * 100, 2)

                    pe_raw = info.get("trailingPE")
                    pb_raw = info.get("priceToBook")
                    div_raw = info.get("dividendYield")

                    datos[t] = {
                        "precio": round(float(p), 2),
                        "pe": round(float(pe_raw), 2) if isinstance(pe_raw, (int, float)) else None,
                        "pbv": round(float(pb_raw), 2) if isinstance(pb_raw, (int, float)) else None,
                        "div_yield": round(float(div_raw) * 100, 2) if isinstance(div_raw, (int, float)) else 0.0,
                        "volumen_pesos_m": vol_pesos_m,
                        "volumen_usd_k": vol_usd_k,
                        "var_1m": v1, "var_1m_usd": v1_usd, "var_6m": v6
                    }
                    if len(hist) >= 14:
                        delta = hist['Close'].diff()
                        g = delta.where(delta > 0, 0.0).rolling(14).mean()
                        l = -delta.where(delta < 0, 0.0).rolling(14).mean()
                        rs = g / l
                        datos[t]["rsi"] = round(float(100 - (100 / (1 + rs.iloc[-1]))), 2) if l.iloc[-1] != 0 else 100.0
        except Exception as e: print(f"Error {t}: {e}")
    return datos

if __name__ == "__main__":
    t_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d_c = obtener_macro_arg_critica()
    
    ccl_v = None
    if d_c["dolares"]:
        ccl_v = next((float(d['venta']) for d in d_c["dolares"] if d['nombre'] == 'CCL'), None)
        
    d_m = extraer_merval(d_c.get("ccl_var_1m"), ccl_venta=ccl_v)
    
    if d_m:
        p_ggal = d_m.get("GGAL.BA", {}).get("precio", 0)
        p_ypfd = d_m.get("YPFD.BA", {}).get("precio", 0)
        p_pamp = d_m.get("PAMP.BA", {}).get("precio", 0)
        p_bma = d_m.get("BMA.BA", {}).get("precio", 0)
        if p_ggal and p_ypfd and p_pamp and p_bma:
            d_c["merval_ars"] = round((p_ggal * 165) + (p_ypfd * 145) + (p_pamp * 110) + (p_bma * 75))
            
    if d_c["merval_ars"] and ccl_v and ccl_v > 0:
        d_c["merval_usd"] = round(d_c["merval_ars"] / ccl_v)

    v_usa, v_arg = extraer_valuaciones(ccl_venta=ccl_v)
    out = {
        "timestamp": t_stamp, 
        "cotizaciones_merval": d_m, 
        "macro_arg_critica": d_c,
        "valuaciones_usa": v_usa,
        "valuaciones_arg": v_arg
    }
    with open("datos_criticos.json", "w", encoding="utf-8") as f: json.dump(out, f, indent=4)
