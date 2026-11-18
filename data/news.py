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
HEADERS = {'User-Agent': 'Mozilla/5.0'}

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

    # 1. Dólares
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

    # 2. Merval ARS y USD
    if dUI["merval"]["valor"] is None:
        try:
            m_hist = yf.Ticker("^MERV").history(period="5d")
            if not m_hist.empty:
                dUI["merval"]["valor"] = round(float(m_hist["Close"].iloc[-1]))
        except: pass
    if dUI["merval"]["valor"] and dUI["merval_usd"]["valor"] is None:
        ccl_v = next((float(d['venta']) for d in dUI["dolares"] if d['nombre'] == 'CCL'), None)
        if ccl_v and ccl_v > 0:
            dUI["merval_usd"]["valor"] = round(dUI["merval"]["valor"] / ccl_v)

    # 3. Inflación, Riesgo País y Reservas
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
            r_gob = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=300.1_AP_ACT_RESTER_0_M_21&limit=1&sort=desc&format=json", timeout=6)
            if r_gob.status_code == 200:
                d_gob = r_gob.json().get("data", [])[0]
                if d_gob[1]:
                    val_r = float(d_gob[1])
                    dUI["reservas"] = round(val_r / 1_000_000) if val_r > 1_000_000_000 else round(val_r)
        except: pass
    if dUI["reservas"] is None:
        try:
            rr = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", headers=HEADERS, timeout=6)
            if rr.status_code == 200:
                res_data = rr.json()[-1]
                val_r = res_data.get("valor") or res_data.get("reservas")
                if val_r: dUI["reservas"] = round(float(val_r))
        except: pass

    # 4. Tasas
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

    # 5. Bono AL30 en vivo
    try:
        res_al30 = requests.get("https://data912.com/live/arg_bonds", headers=HEADERS, timeout=6)
        if res_al30.status_code == 200:
            for b in res_al30.json():
                sym = b.get("symbol") or b.get("ticker")
                p = float(b.get("c", b.get("price", 0)))
                if sym == "AL30" and p > 0: dUI["bono_al30"]["valor"] = round(p * 100, 2) if p < 2000 else round(p, 2)
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
            val["ARG"].append({
                "Activo": t, "Sector": i.get("Sector", "N/D"), 
                "P/E": str(i.get("P/E", "N/D")), "Forward P/E": str(i.get("Forward P/E", "N/D")),
                "EV/EBITDA": str(i.get("EV/EBITDA", "N/D")),
                "FCF Yield": str(i.get("FCF Yield", "N/D")), "Debt/Equity": str(i.get("Debt/Equity", "N/D")),
                "ROE (%)": str(i.get("ROE (%)", "N/D")), 
                "1M": i.get("1M"), "6M": i.get("6M"), "1Y": i.get("1Y")
            })
        for t, i in dp.get("valuaciones_usa", {}).items():
            val["USA"].append({
                "Activo": t, "Sector": i.get("Sector", "N/D"), 
                "P/E": str(i.get("P/E", "N/D")), "Forward P/E": str(i.get("Forward P/E", "N/D")),
                "EV/EBITDA": str(i.get("EV/EBITDA", "N/D")),
                "FCF Yield": str(i.get("FCF Yield", "N/D")), "Debt/Equity": str(i.get("Debt/Equity", "N/D")),
                "ROE (%)": str(i.get("ROE (%)", "N/D")), 
                "1M": i.get("1M"), "6M": i.get("6M"), "1Y": i.get("1Y")
            })
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
        if not dfc.empty and t in dfc.columns:
            sr = dfc[t].dropna()
            if len(sr) >= 20:
                pa = float(sr.iloc[-1])
                if len(sr) >= 21: v1 = ((pa / float(sr.iloc[-21])) - 1) * 100
                if len(sr) >= 126: v6 = ((pa / float(sr.iloc[-126])) - 1) * 100
                if len(sr) >= 250: v12 = ((pa / float(sr.iloc[0])) - 1) * 100
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
        panel = "Principal" if tf in lider else "General"
        p = d.get("precio"); r = d.get("rsi"); v_ars = d.get("volumen_pesos_m"); pe = d.get("pe"); pb = d.get("pbv")
        v1m = d.get("var_1m"); v1m_usd = d.get("var_1m_usd")
        
        lec = "Lateralizando en zona de equilibrio."
        if v_ars is not None and v_ars < 100 and panel == "General": lec = "🔴 RIESGO DE ILIQUIDEZ EXTREMO."
        elif r is not None:
            if r > 70: lec = "¡Precaución! RSI en sobrecompra (>70)."
            elif r < 35: lec = "Señal de Sobreventa (RSI < 35)."
            elif pb and pb < 1: lec = "Subvaluada por fundamentales contables."
            
        res.append({
            "Ticker": tl, "Panel": panel, "Precio": round(p,2) if p else None, 
            "P/E": pe, "P/BV": pb, "Vol_ARS_M": v_ars, 
            "RSI": round(r, 2) if r else None, "Var_1M": v1m, "Var_1M_USD": v1m_usd, "Lectura": lec
        })
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
def generar_analisis_ia(m_arg, m_int, gics, estrategia="Crecimiento (Agresivo)", tickers_cartera=None):
    try:
        dp = obtener_datos_criticos_puente()
        val = obtener_valuaciones_mercado()
        dm = obtener_datos_merval()
        ev = obtener_eventos_macro_eeuu()
        
        ts_corte = dp.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")) if dp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cartera_str = ", ".join(tickers_cartera) if tickers_cartera else "Ninguna cargada aún (Evaluar universo completo)"
        
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
        inf_fecha = mc.get("inflacion_fecha", "N/D")
        emae_fecha = mc.get("emae_fecha", "N/D")
        al30_val = m_arg.get('bono_al30', {}).get('valor', 'N/D')
        al30_v1m = m_arg.get('bono_al30', {}).get('var_1m', 'N/D')
        
        def g(k, metric='valor'): return m_int.get(k, {}).get(metric, 'N/D')
        
        dols = m_arg.get("dolares", [])
        ccl = next((float(d['venta']) for d in dols if d['nombre']=='CCL'), None)
        ofi = next((float(d['venta']) for d in dols if d['nombre']=='Oficial'), None)
        brecha = f"{((ccl/ofi)-1)*100:.1f}%" if ccl and ofi else "N/D"
        
        p = (
            f"Actúa como CIO (Chief Investment Officer) para un fondo en Argentina. [Corte de Datos: {ts_corte}]\n"
            f"PERFIL DE ESTRATEGIA ACTIVO: {estrategia} | EXPOSICIÓN ACTUAL EN CARTERA DEL CLIENTE: [{cartera_str}]\n\n"
            "Redacta un Tablero de Decisiones basado EXCLUSIVAMENTE en los datos provistos. SIGUE ESTAS REGLAS ESTRICTAS:\n"
            "1. DATA QUALITY GATE: Respeta las fechas de corte de cada variable. Nunca inventes datos, porcentajes o catalizadores.\n"
            "2. ALINEACIÓN CON CARTERA Y PERFIL: Ajusta el riesgo al perfil activo y señala explícitamente si una recomendación duplica exposición ya existente en la cartera del cliente.\n"
            "3. SEPARA HECHOS de INTERPRETACIONES. Un P/BV < 1 es un hecho contable sujeto a distorsiones inflacionarias, NO una recomendación automática (Value Trap).\n"
            "4. MONEY MANAGEMENT: Cada recomendación debe declarar explícitamente: (a) Nivel de Confianza [Alto/Medio/Bajo], (b) Horizonte Temporal, (c) Entrada Escalonada y (d) Condición de Invalidación/Salida.\n\n"
            f"**1. MACRO ARGENTINA (Pre-calculado | Corte: {ts_corte}):**\n"
            f"| Merval: USD {m_arg.get('merval_usd',{}).get('valor','N/D')} | Bono AL30: ${al30_val} (Var 1M: {al30_v1m}%) | Brecha CCL: {brecha} | Reservas BCRA: USD {m_arg.get('reservas','N/D')} M (As of: {res_fecha}) |\n"
            f"| Riesgo País (As of: {rp_fecha}): {rp_act} pb | Var 1M: {rp_var_1m_pb} pb ({rp_var_1m_pct}%, base {rp_1m} pb) | Var 6M: {rp_var_6m_pb} pb ({rp_var_6m_pct}%, base {rp_6m} pb) |\n"
            f"| TNA PF 30D: {tna}% -> TEM (30/365): {f'{tem:.2f}%' if tem else 'N/D'} | Inflación Mensual (As of: {inf_fecha}): {inf}% | Tasa Real Efectiva: {f'{rend_real:.2f}%' if rend_real else 'N/D'} |\n"
            f"| Actividad EMAE (As of: {emae_fecha} - Dato estructural con rezago oficial): {m_arg.get('emae_ultimo','N/D')} |\n\n"
            f"**2. MACRO GLOBAL (Momentum Real 1M y 6M | Corte: {ts_corte}):**\n"
            f"- Tasas EE.UU 10Y: {g('Bono 10Y EE.UU (%)')}% (Var 1M: {g('Bono 10Y EE.UU (%)', 'var_1m')}% | Var 6M: {g('Bono 10Y EE.UU (%)', 'var_6m')}%) | DXY: {g('DXY (Índice Dólar)')} (Var 1M: {g('DXY (Índice Dólar)', 'var_1m')}%)\n"
            f"- Oro: USD {g('Oro (Refugio)')} (Var 1M: {g('Oro (Refugio)', 'var_1m')}% | Var 6M: {g('Oro (Refugio)', 'var_6m')}%) | VIX: {g('VIX (Miedo)')}\n\n"
        )
        if ev:
            p += f"**3. CALENDARIO ESTADOS UNIDOS (Corte: {ts_corte}):**\n"
            for e in ev[:4]: p += f"- {e['Evento']} ({e['Fecha/Hora']}): Actual {e['Actual']} vs Proy {e['Proyección']}\n"

        p += f"\n**4. LÍDERES SECTORIALES (VALUACIÓN TRAIL/FWD + MOMENTUM | Corte: {ts_corte}):**\n"
        for v in val.get("USA", []):
            p += f"- USA: {v['Activo']} ({v['Sector']}) | P/E: {v['P/E']} | Fwd P/E: {v.get('Forward P/E','N/D')} | EV/EBITDA: {v.get('EV/EBITDA','N/D')} | FCF Yield: {v.get('FCF Yield','N/D')} | Debt/Eq: {v.get('Debt/Equity','N/D')} | ROE: {v['ROE (%)']} | 1M: {v['1M']}% | 1Y: {v['1Y']}%\n"
        for v in val.get("ARG", []):
            p += f"- ARG: {v['Activo']} ({v['Sector']}) | P/E: {v['P/E']} | Fwd P/E: {v.get('Forward P/E','N/D')} | EV/EBITDA: {v.get('EV/EBITDA','N/D')} | FCF Yield: {v.get('FCF Yield','N/D')} | Debt/Eq: {v.get('Debt/Equity','N/D')} | ROE: {v['ROE (%)']} | 1M: {v['1M']}% | 1Y: {v['1Y']}%\n"
            
        p += f"\n**5. RADAR MERVAL (Volumen Promedio 20 Ruedas + Variación USD | Corte: {ts_corte}):**\n"
        ti = [m for m in dm if (isinstance(m['RSI'], (int, float)) and m['RSI'] < 38) or (isinstance(m['P/BV'], (int, float)) and m['P/BV'] < 1)][:10]
        for m in ti:
            p += f"- {m['Ticker']} ({m['Panel']}): Precio ${m['Precio']} | Var 1M ARS: {m.get('Var_1M', 'N/D')}% | Var 1M USD (CCL): {m.get('Var_1M_USD', 'N/D')}% | P/BV {m['P/BV']} | RSI {m['RSI']} | Vol 20d: ${round(m['Vol_ARS_M'],1) if m['Vol_ARS_M'] else 'N/D'} M ARS | {m['Lectura']}\n"
        
        p += "\nESTRUCTURA TU RESPUESTA EN 4 BLOQUES:\n1. Macro Local e Internacional (Riesgo País 1M/6M, AL30, Tasa Real y Rezago EMAE)\n2. Valuación Sectorial Avanzada (Comparando P/E vs Forward P/E, EV/EBITDA, FCF Yield y Deuda en USA y ADRs)\n3. Matriz de Oportunidades Merval (Alerta sobre Value Traps, liquidez 20d y cruce con exposición actual de cartera)\n4. Escenarios (Bull/Base/Bear) y Plan Operativo (Confianza, Horizonte, Entrada Escalonada e Invalidación)."
        
        return f"<div style='background-color:#0d1117; padding:15px; border-radius:8px;'><pre style='color:#c9d1d9; font-family:monospace; white-space: pre-wrap;'>{p}</pre></div>"
    except Exception as e: return f"Error generador IA: {e}"
