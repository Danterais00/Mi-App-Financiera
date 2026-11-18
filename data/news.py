import requests
import feedparser
import yfinance as yf
import pandas as pd
import streamlit as st
import logging
import time
import urllib3
import xml.etree.ElementTree as ET

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Accept': 'application/json, text/plain, */*'}

@st.cache_data(ttl=300)
def obtener_datos_criticos_puente():
    url_json = "https://raw.githubusercontent.com/Danterais00/Mi-App-Financiera/refs/heads/main/datos_criticos.json"
    try:
        r = requests.get(url_json, timeout=6)
        if r.status_code == 200: return r.json()
    except Exception as e: logger.warning(f"Error JSON: {e}")
    return None

@st.cache_data(ttl=300)
def obtener_macro_argentina():
    dUI = {"dolares": [], "riesgo_pais": None, "merval": {"valor": None}, "merval_usd": {"valor": None}, "bono_al30": {"valor": None}, "bono_al30d": {"valor": None}, "inflacion": None, "tasa_tamar": None, "tasa_badlar": None, "tasa_tna": None, "reservas": None}
    dp = obtener_datos_criticos_puente()
    if dp and "macro_arg_critica" in dp:
        mc = dp["macro_arg_critica"]
        dUI.update({"dolares": mc.get("dolares", []), "tasa_tamar": mc.get("tasa_tamar"), "tasa_badlar": mc.get("tasa_badlar"), "tasa_tna": mc.get("tasa_tna"), "reservas": mc.get("reservas_m")})
        dUI["merval"]["valor"] = mc.get("merval_ars"); dUI["merval_usd"]["valor"] = mc.get("merval_usd")
        dUI["bono_al30"]["valor"] = mc.get("bono_al30"); dUI["bono_al30d"]["valor"] = mc.get("bono_al30d")
        
        if dUI["merval"]["valor"] is None and "cotizaciones_merval" in dp:
            cot = dp["cotizaciones_merval"]
            p_ggal = cot.get("GGAL.BA", {}).get("precio", 0)
            p_ypfd = cot.get("YPFD.BA", {}).get("precio", 0)
            p_pamp = cot.get("PAMP.BA", {}).get("precio", 0)
            p_bma = cot.get("BMA.BA", {}).get("precio", 0)
            if p_ggal and p_ypfd and p_pamp and p_bma:
                merv_calc = round((p_ggal * 165) + (p_ypfd * 145) + (p_pamp * 110) + (p_bma * 75))
                dUI["merval"]["valor"] = merv_calc
                ccl_v = next((float(d['venta']) for d in dUI["dolares"] if d['nombre'] == 'CCL'), None)
                if ccl_v and ccl_v > 0: dUI["merval_usd"]["valor"] = round(merv_calc / ccl_v)
    
    try:
        ri = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", headers=HEADERS, timeout=8)
        if ri.status_code == 200: dUI["inflacion"] = round(float(ri.json()[-1]["valor"]), 1)
    except: pass
    try:
        rp = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", headers=HEADERS, timeout=8)
        if rp.status_code == 200: dUI["riesgo_pais"] = {"valor": round(float(rp.json()[-1]["valor"]))}
    except: pass
    
    if dUI["bono_al30"]["valor"] is None:
        try:
            res_al30 = requests.get("https://data912.com/live/arg_bonds", headers=HEADERS, timeout=8)
            if res_al30.status_code == 200:
                for b in res_al30.json():
                    sym = b.get("symbol") or b.get("ticker")
                    p = float(b.get("c", b.get("price", 0)))
                    if sym == "AL30" and p > 0: dUI["bono_al30"]["valor"] = round(p * 100, 2) if p < 2000 else round(p, 2)
                    if sym == "AL30D" and p > 0: dUI["bono_al30d"]["valor"] = round(p, 2)
        except: pass
        
    return dUI

@st.cache_data(ttl=3600)
def obtener_macro_internacional():
    datos = {}
    tm = {"S&P 500 (Global)": "^GSPC", "Dow Jones": "^DJI", "Nasdaq (Tech)": "^IXIC", "Russell 2000 (Small Caps)": "^RUT", "Euro Stoxx 50 (Europa)": "^STOXX50E", "Nikkei 225 (Japón)": "^N225", "Oro (Refugio)": "GC=F", "Plata": "SI=F", "Cobre (Industrial)": "HG=F", "Petróleo Crudo (WTI)": "CL=F", "DXY (Índice Dólar)": "DX-Y.NYB", "VIX (Miedo)": "^VIX", "Bono 10Y EE.UU (%)": "^TNX", "Bono 10Y Japón (%)": "^JGBS", "Bitcoin (Cripto)": "BTC-USD"}
    for n in tm.keys(): datos[n] = {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None}
    try:
        hd = yf.download(list(tm.values()), period="1y", progress=False)
        if not hd.empty and 'Close' in hd:
            dc = hd['Close']
            for n, t in tm.items():
                if t in dc.columns:
                    s = dc[t].dropna()
                    if len(s) >= 2:
                        act = float(s.iloc[-1])
                        datos[n].update({"valor": act, "var_diaria": float(((act/s.iloc[-2])-1)*100)})
                        if len(s)>=21: datos[n]["var_1m"] = float(((act/s.iloc[-21])-1)*100)
                        if len(s)>=126: datos[n]["var_6m"] = float(((act/s.iloc[-126])-1)*100)
                        if len(s)>=250: datos[n]["var_1y"] = float(((act/s.iloc[0])-1)*100)
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
                    if len(evs)<10: evs.append({"Evento": tit, "Fecha/Hora": f"{e.find('date').text} {e.find('time').text}", "Actual": f"<span style='color:{c_act}; font-weight:bold;'>{act}</span>" if act else "-", "Proyección": forcast if forcast else "-"})
    except: pass
    return evs

@st.cache_data(ttl=3600)
def obtener_valuaciones_mercado():
    dp = obtener_datos_criticos_puente()
    val = {"ARG": [], "USA": []}
    if dp:
        for t, i in dp.get("valuaciones_arg", {}).items():
            val["ARG"].append({"Activo": t, "Sector": i.get("Sector", "N/D"), "P/E": str(i.get("P/E", "N/D")), "ROE (%)": str(i.get("ROE (%)", "N/D")), "1M": i.get("1M"), "6M": i.get("6M"), "1Y": i.get("1Y")})
        for t, i in dp.get("valuaciones_usa", {}).items():
            val["USA"].append({"Activo": t, "Sector": i.get("Sector", "N/D"), "P/E": str(i.get("P/E", "N/D")), "ROE (%)": str(i.get("ROE (%)", "N/D")), "1M": i.get("1M"), "6M": i.get("6M"), "1Y": i.get("1Y")})
    return val

@st.cache_data(ttl=3600)
def obtener_datos_gics():
    # CAMBIO QUIRÚRGICO: Se amplía la historia a 1 año (1y) y se calcula v12
    etfs = {"Tecnología": "XLK", "Financiero": "XLF", "Energía": "XLE", "Salud": "XLV", "Industriales": "XLI", "Cons. Discrecional": "XLY", "Cons. Básico": "XLP", "Utilities": "XLU", "Materiales": "XLB", "Real Estate": "XLRE", "Comunicaciones": "XLC"}
    ds = []
    try:
        hd = yf.download(list(etfs.values()), period="1y", progress=False)
        dfc = hd['Close'] if not hd.empty and 'Close' in hd else pd.DataFrame()
    except: dfc = pd.DataFrame()
    for s, t in etfs.items():
        v1, v6, v12 = 0.0, 0.0, 0.0
        if not dfc.empty and t in dfc.columns:
            sr = dfc[t].dropna()
            if len(sr) >= 20:
                pa = float(sr.iloc[-1])
                if len(sr) >= 21: v1 = ((pa / float(sr.iloc[-21])) - 1) * 100
                if len(sr) >= 126: v6 = ((pa / float(sr.iloc[-126])) - 1) * 100
                else: v6 = ((pa / float(sr.iloc[0])) - 1) * 100
                if len(sr) >= 250: v12 = ((pa / float(sr.iloc[0])) - 1) * 100
                else: v12 = ((pa / float(sr.iloc[0])) - 1) * 100
        sc = max(0, min(100, int(50.0 + (v6 * 1.5))))
        ds.append({"Sector": s, "ETF": t, "1M (%)": v1, "6M (%)": v6, "12M (%)": v12, "Score": sc})
    return sorted(ds, key=lambda x: x["Score"], reverse=True)

@st.cache_data(ttl=3600)
def obtener_datos_merval():
    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    dp = obtener_datos_criticos_puente()
    cot = dp.get("cotizaciones_merval", {}) if dp else {}
    res = []
    for tf, d in cot.items():
        tl = tf.replace(".BA", "")
        p = d.get("precio"); s2 = d.get("sma20"); r = d.get("rsi"); v = d.get("volumen_m"); pe = d.get("pe"); pb = d.get("pbv")
        lec = "Lateralizando en zona de equilibrio."
        if v is not None and v < 0.05 and tf not in lider: lec = "🔴 RIESGO DE ILIQUIDEZ EXTREMO."
        elif r is not None:
            if r > 70: lec = "¡Precaución! RSI en sobrecompra (>70)."
            elif r < 35: lec = "Oportunidad Técnica: Sobreventa (RSI < 35)."
            elif pb and pb < 1: lec = "Subvaluada por fundamentales (P/BV < 1)."
        res.append({"Ticker": tl, "Panel": "Principal" if tf in lider else "General", "Precio (ARS)": round(p,2) if p else None, "P/E": pe, "P/BV": pb, "Vol. (M)": v, "RSI": r, "Lectura": lec})
    return sorted(res, key=lambda x: x["RSI"] if x["RSI"] is not None else 999)

@st.cache_data(ttl=1800)
def obtener_noticias_acciones(tickers):
    n = {}
    for t in tickers[:6]:
        try:
            feed = feedparser.parse(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US")
            n[t] = [{"titulo": e.title, "link": e.link, "fecha": e.published} for e in feed.entries[:3]]
        except: n[t] = []
    return n

@st.cache_data(ttl=1800)
def obtener_noticias_globales():
    try:
        feed = feedparser.parse("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC,CL=F,GC=F,^TNX&region=US&lang=en-US")
        return [entry.title for entry in feed.entries[:5]]
    except: return []

@st.cache_data(ttl=3600)
def generar_analisis_ia(m_arg, m_int, gics):
    try:
        val = obtener_valuaciones_mercado()
        dm = obtener_datos_merval()
        ev = obtener_eventos_macro_eeuu()
        ng = obtener_noticias_globales()
        
        def g(k): return m_int.get(k, {}).get('valor', 'N/D')
        
        dols = m_arg.get("dolares", [])
        ccl = next((float(d['venta']) for d in dols if d['nombre']=='CCL'), None)
        ofi = next((float(d['venta']) for d in dols if d['nombre']=='Oficial'), None)
        brecha = f"{((ccl/ofi)-1)*100:.1f}%" if ccl and ofi else "N/D"
        
        p = (
            "Actúa como Asesor Financiero (CIO) para un inversor en Argentina.\n"
            "Redacta un Resumen Matutino estratégico.\n\n"
            "**1. MACROECONOMÍA ARGENTINA:**\n"
            f"| Merval: {m_arg.get('merval',{}).get('valor','N/D')} pts (USD {m_arg.get('merval_usd',{}).get('valor','N/D')}) | Riesgo País: {m_arg.get('riesgo_pais',{}).get('valor','N/D')} pb | AL30: ${m_arg.get('bono_al30',{}).get('valor','N/D')} |\n"
            f"| TNA (PF): {m_arg.get('tasa_tna','N/D')}% | BADLAR: {m_arg.get('tasa_badlar','N/D')}% | TAMAR: {m_arg.get('tasa_tamar','N/D')}% | Inflación: {m_arg.get('inflacion','N/D')}% |\n"
            f"| Brecha: {brecha} | Reservas: USD {m_arg.get('reservas','N/D')} M |\n\n"
            "**2. MACRO GLOBAL:**\n"
            f"- S&P 500: {g('S&P 500 (Global)')} | Nasdaq: {g('Nasdaq (Tech)')} | DXY: {g('DXY (Índice Dólar)')} | VIX: {g('VIX (Miedo)')}\n"
            f"- Oro: USD {g('Oro (Refugio)')} | WTI: USD {g('Petróleo Crudo (WTI)')} | Tasa 10Y US: {g('Bono 10Y EE.UU (%)')}%\n\n"
        )
        if ev:
            p += "**3. CALENDARIO EE.UU:**\n"
            for e in ev: p += f"- {e['Evento']}: Actual {e['Actual']} vs Proy {e['Proyección']}\n"
            
        p += "\n**4. LÍDERES SECTORIALES (VALUACIÓN + MOMENTUM):**\n"
        for v in val.get("USA", []): p += f"- USA: {v['Activo']} ({v['Sector']}) | P/E: {v['P/E']} | ROE: {v['ROE (%)']} | 1M: {v['1M']}% | 1Y: {v['1Y']}%\n"
        for v in val.get("ARG", []): p += f"- ARG: {v['Activo']} ({v['Sector']}) | P/E: {v['P/E']} | ROE: {v['ROE (%)']} | 1M: {v['1M']}% | 1Y: {v['1Y']}%\n"
            
        p += "\n**5. SCREENER MERVAL:**\n"
        ti = [m for m in dm if (m['RSI'] and m['RSI']<38) or (m['RSI'] and m['RSI']>70) or (m['P/BV'] and m['P/BV']<1)][:10]
        for m in ti: p += f"- {m['Ticker']}: RSI {m['RSI']} | P/BV {m['P/BV']} | {m['Lectura']}\n"
        
        return f"<div style='background-color:#0d1117; padding:15px; border-radius:8px;'><pre style='color:#c9d1d9; font-family:monospace;'>{p}</pre></div>"
    except Exception as e: return f"Error: {e}"
