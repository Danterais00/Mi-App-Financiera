import requests
import feedparser
import yfinance as yf
import pandas as pd
import streamlit as st
import logging
import urllib3
import xml.etree.ElementTree as ET
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

@st.cache_data(ttl=300)
def obtener_datos_criticos_puente():
    url_json = "https://raw.githubusercontent.com/Danterais00/Mi-App-Financiera/refs/heads/main/datos_criticos.json"
    try:
        r = requests.get(url_json, timeout=6)
        if r.status_code == 200: return r.json()
    except Exception as e: logger.warning(f"Error JSON: {e}")
    return None

def _obtener_tna_pf_live():
    try:
        rt = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazo-fijo", headers=HEADERS, timeout=6)
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
            rt2 = requests.get(f"https://apis.datos.gob.ar/series/api/series/?ids={s_id}&limit=5&sort=desc&format=json", timeout=6)
            if rt2.status_code == 200:
                for fila in rt2.json().get("data", []):
                    if len(fila) > 1 and fila[1] is not None:
                        return round(float(fila[1]), 2)
        except: pass
    return None

@st.cache_data(ttl=300)
def obtener_macro_argentina():
    dUI = {
        "dolares": [], "riesgo_pais": None, "merval": {"valor": None}, "merval_usd": {"valor": None}, 
        "bono_al30": {"valor": None, "var_1m": None}, "inflacion": None, "tasa_tamar": None, "tasa_badlar": None, 
        "tasa_tna": None, "reservas": None, "emae_ultimo": None
    }
    dp = obtener_datos_criticos_puente()
    if dp and "macro_arg_critica" in dp:
        mc = dp["macro_arg_critica"]
        dUI["dolares"] = mc.get("dolares", [])
        dUI["tasa_tamar"] = mc.get("tasa_tamar")
        dUI["tasa_badlar"] = mc.get("tasa_badlar")
        dUI["tasa_tna"] = mc.get("tasa_tna")
        dUI["reservas"] = mc.get("reservas_m")
        dUI["inflacion"] = mc.get("inflacion_mensual")
        dUI["emae_ultimo"] = mc.get("emae_ultimo")
        dUI["merval"]["valor"] = mc.get("merval_ars")
        dUI["merval_usd"]["valor"] = mc.get("merval_usd")
        if mc.get("al30_precio"): dUI["bono_al30"]["valor"] = mc["al30_precio"]
        if mc.get("al30_var_1m") is not None: dUI["bono_al30"]["var_1m"] = mc["al30_var_1m"]
        if mc.get("riesgo_pais_actual"): dUI["riesgo_pais"] = mc["riesgo_pais_actual"]

    if len(dUI["dolares"]) < 5:
        try:
            rd = requests.get("https://dolarapi.com/v1/dolares", timeout=6)
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
                        lista_d.append({"nombre": mapa_nombres[casa], "compra": d.get("compra"), "venta": d.get("venta")})
                dUI["dolares"] = sorted(lista_d, key=lambda x: orden.index(x["nombre"]) if x["nombre"] in orden else 99)
        except: pass

    if dUI["merval"]["valor"] is None:
        try:
            hd_m = yf.download(["GGAL.BA", "YPFD.BA", "PAMP.BA", "BMA.BA"], period="5d", progress=False)
            if not hd_m.empty and 'Close' in hd_m:
                dc = hd_m['Close']
                p_ggal = float(dc["GGAL.BA"].dropna().iloc[-1])
                p_ypfd = float(dc["YPFD.BA"].dropna().iloc[-1])
                p_pamp = float(dc["PAMP.BA"].dropna().iloc[-1])
                p_bma = float(dc["BMA.BA"].dropna().iloc[-1])
                if p_ggal and p_ypfd and p_pamp and p_bma:
                    dUI["merval"]["valor"] = round((p_ggal * 165) + (p_ypfd * 145) + (p_pamp * 110) + (p_bma * 75))
        except: pass

    if dUI["merval"]["valor"] and dUI["merval_usd"]["valor"] is None:
        ccl_v = next((float(d['venta']) for d in dUI["dolares"] if d['nombre'] == 'CCL'), None)
        if ccl_v and ccl_v > 0:
            dUI["merval_usd"]["valor"] = round(dUI["merval"]["valor"] / ccl_v)

    if dUI["inflacion"] is None:
        try:
            ri = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", headers=HEADERS, timeout=6)
            if ri.status_code == 200: dUI["inflacion"] = round(float(ri.json()[-1]["valor"]), 1)
        except: pass
    if dUI["riesgo_pais"] is None:
        try:
            rp = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", headers=HEADERS, timeout=6)
            if rp.status_code == 200: dUI["riesgo_pais"] = {"valor": round(float(rp.json()[-1]["valor"]))}
        except: pass
    if dUI["reservas"] is None:
        try:
            r_bcra = requests.get("https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/1?limit=2", headers=HEADERS, verify=False, timeout=8)
            if r_bcra.status_code == 200:
                results = r_bcra.json().get("results", [])
                if results and results[0].get("detalle"):
                    dUI["reservas"] = round(float(results[0]["detalle"][0]["valor"]))
        except: pass

    if dUI["tasa_badlar"] is None:
        try:
            rb = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=89.2_TS_INTELAR_0_D_20&limit=5&sort=desc&format=json", timeout=6)
            if rb.status_code == 200:
                for fila in rb.json().get("data", []):
                    if len(fila) > 1 and fila[1] is not None:
                        dUI["tasa_badlar"] = round(float(fila[1]), 2)
                        break
        except: pass
    if dUI["tasa_tna"] is None:
        dUI["tasa_tna"] = _obtener_tna_pf_live()
    if dUI["tasa_tna"] is None and dUI["tasa_badlar"] is not None:
        dUI["tasa_tna"] = round(dUI["tasa_badlar"] - 2.10, 2)
    if dUI["tasa_tamar"] is None and dUI["tasa_badlar"] is not None:
        dUI["tasa_tamar"] = round(dUI["tasa_badlar"] + 3.20, 2)

    if dUI["bono_al30"]["valor"] is None or dUI["bono_al30"]["var_1m"] is None:
        try:
            r_d9 = requests.get("https://data912.com/historical/bonds/AL30", headers=HEADERS, timeout=6)
            if r_d9.status_code == 200:
                hist = r_d9.json()
                if hist:
                    act = float(hist[-1]["c"])
                    dUI["bono_al30"]["valor"] = round(act * 100, 2) if act < 2000 else round(act, 2)
                    if len(hist) >= 21:
                        prev = float(hist[-21]["c"])
                        if prev > 0:
                            dUI["bono_al30"]["var_1m"] = round(((act / prev) - 1) * 100, 2)
        except: pass
        
    return dUI

@st.cache_data(ttl=3600)
def obtener_macro_internacional():
    datos = {}
    tm = {
        "S&P 500 (Global)": "^GSPC", "Dow Jones": "^DJI", "Nasdaq (Tech)": "^IXIC", 
        "Russell 2000 (Small Caps)": "^RUT", "Euro Stoxx 50 (Europa)": "^STOXX50E", 
        "Nikkei 225 (Japón)": "^N225", "Oro (Refugio)": "GC=F", "Plata": "SI=F", 
        "Cobre (Industrial)": "HG=F", "Petróleo Crudo (WTI)": "CL=F", 
        "DXY (Índice Dólar)": "DX-Y.NYB", "VIX (Miedo)": "^VIX", 
        "Bono 10Y EE.UU (%)": "^TNX", "Bitcoin (Cripto)": "BTC-USD"
    }
    for n in tm.keys(): datos[n] = {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None}
    try:
        hd = yf.download(list(tm.values()), period="1y", progress=False)
        if not hd.empty and 'Close' in hd:
            dc = hd['Close']
            for n, t in tm.items():
                if t in dc.columns:
                    s = dc[t].dropna()
                    if len(s) >= 2:
                        act = round(float(s.iloc[-1]), 2)
                        datos[n].update({"valor": act, "var_diaria": round(float(((act/s.iloc[-2])-1)*100), 2)})
                        if len(s)>=21: datos[n]["var_1m"] = round(float(((act/s.iloc[-21])-1)*100), 2)
                        if len(s)>=126: datos[n]["var_6m"] = round(float(((act/s.iloc[-126])-1)*100), 2)
                        if len(s)>=250: datos[n]["var_1y"] = round(float(((act/s.iloc[0])-1)*100), 2)
    except: pass
    return datos

@st.cache_data(ttl=1800)
def obtener_eventos_macro_eeuu():
    evs = []
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.xml", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for e in root.findall("event"):
                if (e.find("impact") is not None and e.find("impact").text in ["High", "Medium"]) and (e.find("country") is not None and e.find("country").text == "USD"):
                    tit = e.find("title").text if e.find("title") is not None else ""
                    act = e.find("actual").text if e.find("actual") is not None else ""
                    forcast = e.find("forecast").text if e.find("forecast") is not None else ""
                    c_act = "#a3a8b8"
                    if act and forcast:
                        try:
                            av = float(act.replace('%','').replace('B','').replace('K','').replace('M',''))
                            fv = float(forcast.replace('%','').replace('B','').replace('K','').replace('M',''))
                            c_act = "#2ecca6" if av > fv else "#ff6b6b" if av < fv else "#ffd54f"
                        except: pass
                    if len(evs)<10: evs.append({"Evento": tit, "Fecha/Hora": f"{e.find('date').text} {e.find('time').text}", "Actual": f"<span style='color:{c_act}; font-weight:bold;'>{act}</span>" if act else "-", "Actual_Raw": act if act else "Pendiente", "Proyección": forcast if forcast else "-"})
    except: pass
    return evs

@st.cache_data(ttl=3600)
def obtener_valuaciones_mercado():
    dp = obtener_datos_criticos_puente()
    val = {"ARG": [], "USA": []}
    if dp and dp.get("valuaciones_usa") and dp.get("valuaciones_arg"):
        for t, i in dp.get("valuaciones_arg", {}).items():
            val["ARG"].append({
                "Activo": t, "Sector": i.get("Sector", "N/D"), 
                "Precio": str(i.get("Precio", "N/D")), "Target": str(i.get("Target", "N/D")),
                "Upside": str(i.get("Upside", "N/D")), "PEG": str(i.get("PEG", "N/D")),
                "P/E": str(i.get("P/E", "N/D")), "Fwd P/E": str(i.get("Forward P/E", "N/D")),
                "P/BV": str(i.get("P/BV", "N/D")),
                "EV/EBITDA": str(i.get("EV/EBITDA", "N/D")),
                "FCF Yield": str(i.get("FCF Yield", "N/D")), "Debt/Eq": str(i.get("Debt/Equity", "N/D")),
                "ROE (%)": str(i.get("ROE (%)", "N/D"))
            })
        for t, i in dp.get("valuaciones_usa", {}).items():
            val["USA"].append({
                "Activo": t, "Sector": i.get("Sector", "N/D"), 
                "Precio": str(i.get("Precio", "N/D")), "Target": str(i.get("Target", "N/D")),
                "Upside": str(i.get("Upside", "N/D")), "PEG": str(i.get("PEG", "N/D")),
                "P/E": str(i.get("P/E", "N/D")), "Fwd P/E": str(i.get("Forward P/E", "N/D")),
                "P/BV": str(i.get("P/BV", "N/D")),
                "EV/EBITDA": str(i.get("EV/EBITDA", "N/D")),
                "FCF Yield": str(i.get("FCF Yield", "N/D")), "Debt/Eq": str(i.get("Debt/Equity", "N/D")),
                "ROE (%)": str(i.get("ROE (%)", "N/D"))
            })
        return val

    lideres_usa = {"SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF", "MSFT": "Tecnología", "GOOGL": "Comunicaciones", "JPM": "Financiero", "XOM": "Energía", "LLY": "Salud"}
    lideres_arg = {"GGAL": "Financiero", "BMA": "Financiero", "YPF": "Energía", "PAM": "Energía", "VIST": "Energía", "TGS": "Energía", "MELI": "Tecnología"}
    for t, sec in lideres_usa.items():
        try:
            inf = yf.Ticker(t).info
            p = inf.get("currentPrice") or inf.get("regularMarketPrice")
            tg = inf.get("targetMeanPrice")
            peg = inf.get("pegRatio") or inf.get("trailingPegRatio")
            pe = inf.get("trailingPE")
            fpe = inf.get("forwardPE")
            pb = inf.get("priceToBook")
            roe = inf.get("returnOnEquity")
            val["USA"].append({
                "Activo": t, "Sector": sec,
                "Precio": f"${p:.2f}" if p else "N/D",
                "Target": f"${tg:.2f}" if tg else "N/D",
                "Upside": f"{((tg/p)-1)*100:+.1f}%" if (p and tg) else "N/D",
                "PEG": f"{peg:.2f}" if isinstance(peg, (int, float)) else "N/D",
                "P/E": f"{pe:.1f}" if isinstance(pe, (int, float)) else "N/D",
                "Fwd P/E": f"{fpe:.1f}" if isinstance(fpe, (int, float)) else "N/D",
                "P/BV": f"{pb:.2f}" if isinstance(pb, (int, float)) else "N/D",
                "EV/EBITDA": f"{inf.get('enterpriseToEbitda'):.1f}" if isinstance(inf.get('enterpriseToEbitda'), (int, float)) else "N/D",
                "ROE (%)": f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D"
            })
        except: pass
    for t, sec in lideres_arg.items():
        try:
            inf = yf.Ticker(t).info
            p = inf.get("currentPrice") or inf.get("regularMarketPrice")
            tg = inf.get("targetMeanPrice")
            peg = inf.get("pegRatio") or inf.get("trailingPegRatio")
            pe = inf.get("trailingPE")
            fpe = inf.get("forwardPE")
            pb = inf.get("priceToBook")
            roe = inf.get("returnOnEquity")
            val["ARG"].append({
                "Activo": t, "Sector": sec,
                "Precio": f"${p:.2f}" if p else "N/D",
                "Target": f"${tg:.2f}" if tg else "N/D",
                "Upside": f"{((tg/p)-1)*100:+.1f}%" if (p and tg) else "N/D",
                "PEG": f"{peg:.2f}" if isinstance(peg, (int, float)) else "N/D",
                "P/E": f"{pe:.1f}" if isinstance(pe, (int, float)) else "N/D",
                "Fwd P/E": f"{fpe:.1f}" if isinstance(fpe, (int, float)) else "N/D",
                "P/BV": f"{pb:.2f}" if isinstance(pb, (int, float)) else "N/D",
                "EV/EBITDA": f"{inf.get('enterpriseToEbitda'):.1f}" if isinstance(inf.get('enterpriseToEbitda'), (int, float)) else "N/D",
                "ROE (%)": f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D"
            })
        except: pass
    return val

@st.cache_data(ttl=3600)
def obtener_datos_gics():
    etfs = {"Tecnología": "XLK", "Financiero": "XLF", "Energía": "XLE", "Salud": "XLV", "Industriales": "XLI", "Cons. Discrecional": "XLY", "Cons. Básico": "XLP", "Utilities": "XLU", "Materiales": "XLB", "Real Estate": "XLRE", "Comunicaciones": "XLC"}
    ds = []
    try:
        hd = yf.download(list(etfs.values()), period="1y", progress=False)
        dfc = hd['Close'] if not hd.empty and 'Close' in hd else pd.DataFrame()
    except: dfc = pd.DataFrame()
    for s, t in etfs.items():
        v1, v6, v12 = 0.0, 0.0, 0.0
        pe_val = None
        try:
            pe_raw = yf.Ticker(t).info.get("trailingPE")
            if isinstance(pe_raw, (int, float)): pe_val = round(float(pe_raw), 2)
        except: pass
        if not dfc.empty and t in dfc.columns:
            sr = dfc[t].dropna()
            if len(sr) >= 20:
                pa = float(sr.iloc[-1])
                if len(sr) >= 21: v1 = round(((pa / float(sr.iloc[-21])) - 1) * 100, 2)
                if len(sr) >= 126: v6 = round(((pa / float(sr.iloc[-126])) - 1) * 100, 2)
                if len(sr) >= 250: v12 = round(((pa / float(sr.iloc[0])) - 1) * 100, 2)
        sc = max(0, min(100, int(50.0 + (v6 * 1.5))))
        ds.append({"Sector": s, "ETF": t, "P/E": pe_val, "1M (%)": v1, "6M (%)": v6, "12M (%)": v12, "Score": sc})
    return sorted(ds, key=lambda x: x["Score"], reverse=True)

@st.cache_data(ttl=3600)
def obtener_datos_merval():
    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    general = ["AGRO.BA", "AUSO.BA", "BHIP.BA", "CAPX.BA", "CGPA2.BA", "GCLA.BA", "HAVA.BA", "MORI.BA", "OEST.BA", "SAMI.BA"]
    dp = obtener_datos_criticos_puente()
    cot = dp.get("cotizaciones_merval", {}) if dp else {}
    res = []

    if cot:
        for tf, d in cot.items():
            tl = tf.replace(".BA", "")
            panel = "Principal" if tf in lider else "General"
            p = d.get("precio"); r = d.get("rsi"); v_ars = d.get("volumen_pesos_m"); v_usd = d.get("volumen_usd_k")
            pe = d.get("pe"); pb = d.get("pbv")
            div_y = d.get("div_yield", 0.0)
            v1m = d.get("var_1m"); v1m_usd = d.get("var_1m_usd")
            
            lec = "Lateralizando en zona de equilibrio."
            if v_ars is not None and v_ars < 100 and panel == "General": lec = "🔴 RIESGO DE ILIQUIDEZ EXTREMO."
            elif r is not None:
                if r > 70: lec = "¡Precaución! RSI en sobrecompra (>70)."
                elif r < 35: lec = "Señal de Sobreventa (RSI < 35)."
                elif pb and pb < 1: lec = "Subvaluada por fundamentales contables."
                
            res.append({
                "Ticker": tl, "Panel": panel, "Precio (ARS)": round(p,2) if p else None, 
                "P/E": round(pe,2) if isinstance(pe, (int, float)) else None, 
                "P/BV": round(pb,2) if isinstance(pb, (int, float)) else None, 
                "Div Yield (%)": round(div_y, 2) if isinstance(div_y, (int, float)) else 0.0,
                "Vol. 20d (M ARS)": round(v_ars,2) if isinstance(v_ars, (int, float)) else None, 
                "Vol. 20d (K USD)": round(v_usd,1) if isinstance(v_usd, (int, float)) else None,
                "RSI": round(r, 2) if r else None, "Var_1M": v1m, "Var_1M_USD": v1m_usd, "Lectura": lec
            })
        return sorted(res, key=lambda x: x["RSI"] if isinstance(x["RSI"], (int, float)) else 999)

    tkrs = lider + general
    try:
        ts = yf.Tickers(" ".join(tkrs))
        for tf in tkrs:
            ti = ts.tickers[tf]
            hist = ti.history(period="2mo")
            if not hist.empty:
                p = float(hist["Close"].iloc[-1])
                vol_20d = float(hist["Volume"].dropna().tail(20).mean())
                v_ars = round((vol_20d * p) / 1_000_000, 2)
                r = None
                if len(hist) >= 14:
                    delta = hist['Close'].diff()
                    g = delta.where(delta > 0, 0.0).rolling(14).mean()
                    l = -delta.where(delta < 0, 0.0).rolling(14).mean()
                    rs = g / l
                    r = round(float(100 - (100 / (1 + rs.iloc[-1]))), 2) if l.iloc[-1] != 0 else 100.0
                inf = ti.info
                pe = inf.get("trailingPE")
                pb = inf.get("priceToBook")
                panel = "Principal" if tf in lider else "General"
                lec = "Lateralizando en zona de equilibrio."
                if v_ars < 100 and panel == "General": lec = "🔴 RIESGO DE ILIQUIDEZ EXTREMO."
                elif r and r > 70: lec = "¡Precaución! RSI en sobrecompra (>70)."
                elif r and r < 35: lec = "Señal de Sobreventa (RSI < 35)."
                res.append({
                    "Ticker": tf.replace(".BA", ""), "Panel": panel, "Precio (ARS)": round(p, 2),
                    "P/E": round(float(pe), 2) if isinstance(pe, (int, float)) else None,
                    "P/BV": round(float(pb), 2) if isinstance(pb, (int, float)) else None,
                    "Div Yield (%)": 0.0, "Vol. 20d (M ARS)": v_ars, "Vol. 20d (K USD)": None, "RSI": r, "Lectura": lec
                })
    except: pass
    return sorted(res, key=lambda x: x["RSI"] if isinstance(x["RSI"], (int, float)) else 999)

@st.cache_data(ttl=1800)
def obtener_noticias_acciones(tickers):
    n = {}
    for t in tickers[:6]:
        try:
            feed = feedparser.parse(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US")
            n[t] = [{"titulo": e.title, "link": e.link, "fecha": e.published} for e in feed.entries[:3]]
        except: n[t] = []
    return n

@st.cache_data(ttl=3600)
def generar_analisis_ia(m_arg, m_int, gics, estrategia=None, tickers_cartera=None):
    try:
        dp = obtener_datos_criticos_puente()
        val = obtener_valuaciones_mercado()
        dm = obtener_datos_merval()
        ev = obtener_eventos_macro_eeuu()
        
        ts_corte = dp.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")) if dp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cartera_str = ", ".join(tickers_cartera) if tickers_cartera else "Ninguna cargada aún"
        
        tna = m_arg.get('tasa_tna')
        inf = m_arg.get('inflacion')
        tem = tna * (30/365) if tna else None
        rend_real = (((1 + tem/100) / (1 + inf/100)) - 1) * 100 if (tem is not None and inf is not None) else None
        
        mc = dp.get("macro_arg_critica", {}) if dp else {}
        rp_act = mc.get("riesgo_pais_actual", {}).get("valor", m_arg.get('riesgo_pais', {}).get('valor', 'N/D'))
        rp_fecha = mc.get("riesgo_pais_actual", {}).get("fecha", "N/D")
        rp_1m = mc.get("riesgo_pais_1m", {}).get("valor", "N/D")
        rp_var_1m_pb = mc.get("riesgo_pais_var_1m_pb", "N/D")
        rp_var_1m_pct = mc.get("riesgo_pais_var_1m_pct", "N/D")
        rp_6m = mc.get("riesgo_pais_6m", {}).get("valor", "N/D")
        rp_var_6m_pb = mc.get("riesgo_pais_var_6m_pb", "N/D")
        rp_var_6m_pct = mc.get("riesgo_pais_var_6m_pct", "N/D")
        
        res_fecha = mc.get("reservas_fecha", "N/D")
        res_v30_m = mc.get("reservas_var_30d_m", "N/D")
        res_v30_pct = mc.get("reservas_var_30d_pct", "N/D")
        ccl_v1m = mc.get("ccl_var_1m", "N/D")
        ccl_v3m = mc.get("ccl_var_3m", "N/D")
        inf_fecha = mc.get("inflacion_fecha", "N/D")
        emae_fecha = mc.get("emae_fecha", "N/D")
        
        al30_val = m_arg.get('bono_al30', {}).get('valor', 'N/D')
        al30_v1m_raw = m_arg.get('bono_al30', {}).get('var_1m')
        al30_v1m_str = f"{al30_v1m_raw:+.2f}%" if isinstance(al30_v1m_raw, (int, float)) else "N/D"
        
        def g(k, metric='valor'):
            v = m_int.get(k, {}).get(metric)
            return f"{v:.2f}" if isinstance(v, (int, float)) else "N/D"
        
        dols = m_arg.get("dolares", [])
        ccl = next((float(d['venta']) for d in dols if d['nombre']=='CCL'), None)
        ofi = next((float(d['venta']) for d in dols if d['nombre']=='Oficial'), None)
        brecha = f"{((ccl/ofi)-1)*100:.1f}%" if ccl and ofi else "N/D"
        
        p = (
            f"Actúa como un Analista Fundamental Senior (Equity & Macro Research) presentando un informe objetivo y claro en español llano. [Corte de Datos: {ts_corte}]\n"
            f"CARTERA ACTUAL DEL CLIENTE (solo para detectar superposiciones temáticas si hay activos cargados): [{cartera_str}]\n\n"
            "Redacta un Informe de Investigación Fundamental basado EXCLUSIVAMENTE en los datos provistos abajo.\n"
            "REGLAS ESTRICTAS DE ALCANCE Y RIGOR:\n"
            "1. ENFOQUE 100% FUNDAMENTAL: NO menciones perfiles de riesgo (agresivo, moderado, conservador), NO asignes porcentajes de cartera, NO des órdenes de entrada escalonada y NO fijes precios de Stop-Loss ni gatillos técnicos por RSI. Evalúa únicamente la salud del negocio, la generación de caja, el endeudamiento y la valuación respecto al precio actual.\n"
            "2. PROHIBIDO REPETIR TABLAS CRUDAS: No transcribas listas de números de entrada; explica de forma directa qué significa cada indicador y cómo impacta en el valor de las empresas.\n"
            "3. RIGOR MACROECONÓMICO:\n"
            "   - Aclara que el saldo del BCRA corresponde a Reservas Brutas (que incluyen encajes y swaps, no libre disponibilidad neta) y analiza su tendencia de acumulación/caída en 30 días.\n"
            "   - Evalúa no solo la brecha cambiaria, sino la velocidad de suba del Dólar CCL (1M y 3M) frente a la inflación mensual, y menciona que más allá del Plazo Fijo tradicional existen instrumentos de corto plazo en pesos (Letras/CER/Money Market).\n"
            "   - Explica correctamente la macro global: una tasa del Bono del Tesoro EE.UU. a 10 años arriba del 5% implica caída en el precio de los bonos y mayor exigencia de descuento sobre las ganancias futuras de las acciones.\n"
            "4. PRECIO VS. VALOR Y CALIDAD OPERATIVA:\n"
            "   - Separa calidad de negocio de precio de compra: compara siempre Precio Actual vs. Target Price (Upside %), PEG Ratio, EV/EBITDA, FCF Yield (flujo de caja libre sobre valor de mercado) y Deuda/Patrimonio.\n"
            "   - En bancos (JPM, GGAL, BMA), evalúa P/BV junto con ROE y aclara que sus ganancias proyectadas dependen del ciclo de tasas, crédito y morosidad.\n"
            "   - En empresas reguladas (TGNO4, EDN, CEPU), aclara que su flujo depende de cuadros tarifarios y capex, no solo de múltiplos contables.\n"
            "   - Alerta explícitamente sobre trampas de valor (múltiplos contables bajos pero con deterioro en ganancias proyectadas o caja negativa) y sobre acciones del Panel General con liquidez diaria mínima (en pesos y dólares).\n\n"
            f"--- DATOS DE REFERENCIA (NO COPIAR EN BLOQUE, SOLO INTERPRETAR) ---\n"
            f"1. MACRO ARGENTINA:\n"
            f"- Merval: USD {m_arg.get('merval_usd',{}).get('valor','N/D')} | Bono AL30: ${al30_val} (Var 1M: {al30_v1m_str})\n"
            f"- Dólar CCL: ${ccl if ccl else 'N/D'} (Var 1M: {ccl_v1m}% | Var 3M: {ccl_v3m}%) | Brecha CCL vs Oficial: {brecha}\n"
            f"- Reservas Brutas BCRA (al {res_fecha}): USD {m_arg.get('reservas','N/D')} M (Var 30d: {res_v30_m} M / {res_v30_pct}%)\n"
            f"- Riesgo País (al {rp_fecha}): {rp_act} pb (Var 1M: {rp_var_1m_pb} pb / {rp_var_1m_pct}%, base {rp_1m} pb | Var 6M: {rp_var_6m_pb} pb / {rp_var_6m_pct}%, base {rp_6m} pb)\n"
            f"- Plazo Fijo 30D: TNA {tna}% ({f'{tem:.2f}%' if tem else 'N/D'} mensual) vs Inflación Mensual (al {inf_fecha}): {inf}% -> Rendimiento Real PF: {f'{rend_real:.2f}%' if rend_real else 'N/D'}\n"
            f"- Actividad Económica EMAE (al {emae_fecha}, rezago oficial): {m_arg.get('emae_ultimo','N/D')}\n\n"
            f"2. MACRO GLOBAL:\n"
            f"- Bono EE.UU 10Y: {g('Bono 10Y EE.UU (%)')}% (1M: {g('Bono 10Y EE.UU (%)', 'var_1m')}% | 6M: {g('Bono 10Y EE.UU (%)', 'var_6m')}%) | DXY: {g('DXY (Índice Dólar)')} (1M: {g('DXY (Índice Dólar)', 'var_1m')}%)\n"
            f"- Oro: USD {g('Oro (Refugio)')} (1M: {g('Oro (Refugio)', 'var_1m')}% | 6M: {g('Oro (Refugio)', 'var_6m')}%) | VIX: {g('VIX (Miedo)')}\n"
            f"- Índices de Referencia (1M / 6M / 12M): S&P 500 ({g('S&P 500 (Global)', 'var_1m')}% / {g('S&P 500 (Global)', 'var_6m')}% / {g('S&P 500 (Global)', 'var_1y')}%) | Nasdaq ({g('Nasdaq (Tech)', 'var_1m')}% / {g('Nasdaq (Tech)', 'var_6m')}% / {g('Nasdaq (Tech)', 'var_1y')}%)\n\n"
        )
        if ev:
            p += "3. AGENDA ECONÓMICA EE.UU. ESTA SEMANA:\n"
            for e in ev[:4]: p += f"- {e['Evento']} ({e['Fecha/Hora']}): Estado {e.get('Actual_Raw','Pendiente')} vs Proy {e['Proyección']}\n"

        if gics:
            p += "\n4. FORTALEZA SECTORIAL EE.UU. (GICS):\n"
            for s in gics[:6]:
                p += f"- {s['Sector']} ({s['ETF']}): Puntaje {s['Score']}/100 | 1M: {s['1M (%)']:+.2f}% | 6M: {s['6M (%)']:+.2f}% | 12M: {s['12M (%)']:+.2f}%\n"

        p += "\n5. EMPRESAS LÍDERES (Precio vs Target, PEG, Múltiplos y Generación de Caja):\n"
        for v in val.get("USA", []):
            p += f"- USA {v['Activo']} ({v['Sector']}): Precio {v.get('Precio','N/D')} | Target {v.get('Target','N/D')} (Upside {v.get('Upside','N/D')}) | PEG {v.get('PEG','N/D')} | P/E {v['P/E']} | Fwd P/E {v.get('Fwd P/E','N/D')} | P/BV {v.get('P/BV','N/D')} | EV/EBITDA {v.get('EV/EBITDA','N/D')} | FCF Yield {v.get('FCF Yield','N/D')} | Deuda/Patr {v.get('Debt/Eq','N/D')} | ROE {v['ROE (%)']}\n"
        for v in val.get("ARG", []):
            p += f"- ARG {v['Activo']} ({v['Sector']}): Precio {v.get('Precio','N/D')} | Target {v.get('Target','N/D')} (Upside {v.get('Upside','N/D')}) | PEG {v.get('PEG','N/D')} | P/E {v['P/E']} | Fwd P/E {v.get('Fwd P/E','N/D')} | P/BV {v.get('P/BV','N/D')} | EV/EBITDA {v.get('EV/EBITDA','N/D')} | FCF Yield {v.get('FCF Yield','N/D')} | Deuda/Patr {v.get('Debt/Eq','N/D')} | ROE {v['ROE (%)']}\n"
            
        p += "\n6. UNIVERSO LOCAL MERVAL (Liquidez diaria en ARS y USD + Múltiplos Contables):\n"
        ti = [m for m in dm if (isinstance(m['RSI'], (int, float)) and m['RSI'] < 38) or (isinstance(m['P/BV'], (int, float)) and m['P/BV'] < 1)][:10]
        for m in ti:
            pe_str = f"{m['P/E']}" if m.get('P/E') is not None else "N/D"
            p += f"- {m['Ticker']} ({m['Panel']}): Precio ${m.get('Precio (ARS)','N/D')} | Var 1M USD: {m.get('Var_1M_USD', 'N/D')}% | P/E {pe_str} | P/BV {m['P/BV']} | Vol. diario: ${m.get('Vol. 20d (M ARS)','N/D')} M ARS (USD {m.get('Vol. 20d (K USD)','N/D')} K) | {m['Lectura']}\n"
        
        p += (
            "\n--- ESTRUCTURA EXACTA DE TU INFORME FUNDAMENTAL ---\n"
            "1. Diagnóstico Macroeconómico y Cambiario (Riesgo País y trayectoria 1M/6M, Reservas Brutas vs Netas y tendencia 30d, velocidad del CCL vs Inflación, alternativas de corto plazo en pesos y Tasas de EE.UU. 10Y).\n"
            "2. Dinámica Sectorial (Qué sectores muestran fundamentos y tracción relativa a 1M/6M/12M y cuáles sufren por el costo del dinero).\n"
            "3. Auditoría Fundamental de Compañías (Clasificación clara en tres grupos: [A] Fundamentos sólidos con margen de seguridad atractivo según Precio vs Target, FCF Yield y Deuda; [B] Buenas compañías pero con valuación exigente o bajo Upside; [C] Descartadas por deterioro operativo proyectado, caja negativa o iliquidez severa).\n"
            "4. Escenarios Fundamentales y Variables a Monitorear (Escenario Optimista, Base y Pesimista según evolución de petróleo, tarifas, tasas de la Fed y reservas, sin incluir órdenes de compra, porcentajes ni stop-loss)."
        )
        
        return f"<pre style='color:#e2e8f0; font-family:monospace; white-space: pre-wrap; margin:0;'>{p}</pre>"
    except Exception as e: return f"Error generador IA: {e}"
