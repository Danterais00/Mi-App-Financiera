import requests
import feedparser
import yfinance as yf
import pandas as pd
import streamlit as st
import logging
import urllib3
import xml.etree.ElementTree as ET

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

@st.cache_data(ttl=300)
def obtener_macro_argentina():
    dUI = {"dolares": [], "riesgo_pais": None, "merval": {"valor": None}, "merval_usd": {"valor": None}, "bono_al30": {"valor": None}, "inflacion": None, "tasa_bcra": None, "reservas": None, "emae_ultimo": None}
    dp = obtener_datos_criticos_puente()
    if dp and "macro_arg_critica" in dp:
        mc = dp["macro_arg_critica"]
        dUI["dolares"] = mc.get("dolares", [])
        dUI["tasa_bcra"] = mc.get("tasa_bcra")
        dUI["reservas"] = mc.get("reservas_m")
        dUI["inflacion"] = mc.get("inflacion_mensual")
        dUI["emae_ultimo"] = mc.get("emae_ultimo")
        
        rp_act = mc.get("riesgo_pais_actual")
        if rp_act: dUI["riesgo_pais"] = rp_act
        
        # Cálculo Merval USD con CCL
        if "cotizaciones_merval" in dp:
            cot = dp["cotizaciones_merval"]
            p_ggal, p_ypfd, p_pamp, p_bma = cot.get("GGAL.BA", {}).get("precio", 0), cot.get("YPFD.BA", {}).get("precio", 0), cot.get("PAMP.BA", {}).get("precio", 0), cot.get("BMA.BA", {}).get("precio", 0)
            if p_ggal and p_ypfd and p_pamp and p_bma:
                merv_calc = round((p_ggal * 165) + (p_ypfd * 145) + (p_pamp * 110) + (p_bma * 75))
                dUI["merval"]["valor"] = merv_calc
                ccl_v = next((float(d['venta']) for d in dUI["dolares"] if d['nombre'] == 'CCL'), None)
                if ccl_v and ccl_v > 0: dUI["merval_usd"]["valor"] = round(merv_calc / ccl_v)
    
    # Bono AL30
    try:
        res_al30 = requests.get("https://data912.com/live/arg_bonds", headers=HEADERS, timeout=8)
        if res_al30.status_code == 200:
            for b in res_al30.json():
                sym = b.get("symbol") or b.get("ticker")
                if sym == "AL30": dUI["bono_al30"]["valor"] = float(b.get("c", b.get("price", 0))) * 100 if float(b.get("c", b.get("price", 0))) < 2000 else float(b.get("c", b.get("price", 0)))
    except: pass
        
    return dUI

@st.cache_data(ttl=3600)
def obtener_macro_internacional():
    dp = obtener_datos_criticos_puente()
    if dp and "macro_int_critica" in dp: return dp["macro_int_critica"]
    return {}

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
                    if len(evs)<10: evs.append({"Evento": tit, "Fecha/Hora": f"{e.find('date').text} {e.find('time').text}", "Actual": act if act else "-", "Proyección": forcast if forcast else "-"})
    except: pass
    return evs

@st.cache_data(ttl=3600)
def obtener_valuaciones_mercado():
    dp = obtener_datos_criticos_puente()
    val = {"ARG": [], "USA": []}
    if dp:
        for t, i in dp.get("valuaciones_arg", {}).items(): val["ARG"].append({"Activo": t, "Sector": i.get("Sector", "N/D"), "P/E": i.get("P/E"), "ROE (%)": i.get("ROE (%)"), "1M": i.get("1M"), "6M": i.get("6M"), "1Y": i.get("1Y")})
        for t, i in dp.get("valuaciones_usa", {}).items(): val["USA"].append({"Activo": t, "Sector": i.get("Sector", "N/D"), "P/E": i.get("P/E"), "ROE (%)": i.get("ROE (%)"), "1M": i.get("1M"), "6M": i.get("6M"), "1Y": i.get("1Y")})
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
        v1, v6, v12, pa = 0.0, 0.0, 0.0, None
        if not dfc.empty and t in dfc.columns:
            sr = dfc[t].dropna()
            if len(sr) >= 20:
                pa = float(sr.iloc[-1])
                if len(sr) >= 21: v1 = ((pa / float(sr.iloc[-21])) - 1) * 100
                if len(sr) >= 126: v6 = ((pa / float(sr.iloc[-126])) - 1) * 100
                if len(sr) >= 250: v12 = ((pa / float(sr.iloc[0])) - 1) * 100
        sc = max(0, min(100, int(50.0 + (v6 * 1.5))))
        ds.append({"Sector": s, "ETF": t, "1M (%)": v1, "6M (%)": v6, "12M (%)": v12, "Score": sc, "P/E": None})
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
        v1m = d.get("var_1m"); v6m = d.get("var_6m")
        
        lec = "Lateralizando en zona de equilibrio."
        # Liquidez en base a PESOS REALES (Filtro Rojo: Menos de $100M operados)
        if v_ars is not None and v_ars < 100 and panel == "General": lec = "🔴 RIESGO DE ILIQUIDEZ EXTREMO."
        elif r is not None:
            if r > 70: lec = "¡Precaución! RSI en sobrecompra (>70)."
            elif r < 35: lec = "Oportunidad Técnica: Sobreventa (RSI < 35)."
            elif pb and pb < 1: lec = "Subvaluada por fundamentales contables."
            
        res.append({
            "Ticker": tl, "Panel": panel, "Precio": round(p,2) if p else None, 
            "P/E": pe, "P/BV": pb, "Vol_ARS_M": v_ars, 
            "RSI": round(r, 2) if r else None, "Var_1M": v1m, "Lectura": lec
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
def generar_analisis_ia(m_arg, m_int, gics):
    try:
        dp = obtener_datos_criticos_puente()
        dm = obtener_datos_merval()
        ev = obtener_eventos_macro_eeuu()
        
        # Matemática: Tasa Efectiva Mensual (TEM) vs Inflación
        tna = m_arg.get('tasa_bcra')
        inf = m_arg.get('inflacion')
        tem = tna * (30/365) if tna else None
        rend_real = (tem - inf) if (tem is not None and inf is not None) else None
        
        # Carga Historial Riesgo País
        mc = dp.get("macro_arg_critica", {}) if dp else {}
        rp_act = mc.get("riesgo_pais_actual", {}).get("valor", "N/D")
        rp_1m = mc.get("riesgo_pais_1m", {}).get("valor", "N/D")
        
        def g(k, metric='valor'): return m_int.get(k, {}).get(metric, 'N/D')
        
        dols = m_arg.get("dolares", [])
        ccl = next((float(d['venta']) for d in dols if d['nombre']=='CCL'), None)
        ofi = next((float(d['venta']) for d in dols if d['nombre']=='Oficial'), None)
        brecha = f"{((ccl/ofi)-1)*100:.1f}%" if ccl and ofi else "N/D"
        
        p = (
            "Actúa como CIO (Chief Investment Officer) para un fondo en Argentina.\n"
            "Redacta un Tablero de Decisiones basado EXCLUSIVAMENTE en los datos provistos. SIGUE ESTAS REGLAS ESTRICTAS:\n"
            "1. PROHIBIDO inventar datos, porcentajes o catalizadores. Si un dato falta, indica 'N/D'.\n"
            "2. SEPARA HECHOS de INTERPRETACIONES. Un P/BV < 1 es un hecho contable, NO una recomendación automática (Value Trap).\n"
            "3. MONEY MANAGEMENT: Las recomendaciones de compra deben sugerir 'entradas escalonadas' y definir una condición de salida/invalidación.\n\n"
            "**1. MACRO ARGENTINA (Datos Pre-calculados en Backend):**\n"
            f"| Merval: USD {m_arg.get('merval_usd',{}).get('valor','N/D')} | Brecha CCL: {brecha} | Reservas BCRA: USD {m_arg.get('reservas','N/D')} M |\n"
            f"| Riesgo País: {rp_act} pb (Hace 30 días: {rp_1m} pb) |\n"
            f"| TNA: {tna}% -> Equivale a TEM de {tem:.2f}%. Frente a Inflación ({inf}%), el Rendimiento Mensual Real es: {rend_real:.2f}% |\n"
            f"| Actividad EMAE (Dato con 3 meses de rezago oficial): {m_arg.get('emae_ultimo','N/D')} |\n\n"
            "**2. MACRO GLOBAL (Momentum Real 1 Mes):**\n"
            f"- Tasas EE.UU 10Y: {g('Bono 10Y EE.UU (%)')} (Var 1M: {g('Bono 10Y EE.UU (%)', 'var_1m')}%) | DXY: {g('DXY (Índice Dólar)')}\n"
            f"- Oro: {g('Oro (Refugio)')} (Var 1M: {g('Oro (Refugio)', 'var_1m')}%) | VIX: {g('VIX (Miedo)')}\n\n"
        )
        if ev:
            p += "**3. CALENDARIO ESTADOS UNIDOS:**\n"
            for e in ev[:3]: p += f"- {e['Evento']}: {e['Actual']} vs Proy {e['Proyección']}\n"
            
        p += "\n**4. RADAR MERVAL (Filtro de Sobreventa y Valuación Contable):**\n"
        ti = [m for m in dm if (isinstance(m['RSI'], (int, float)) and m['RSI'] < 38) or (isinstance(m['P/BV'], (int, float)) and m['P/BV'] < 1)][:10]
        for m in ti: p += f"- {m['Ticker']} ({m['Panel']}): Precio ${m['Precio']} | Caída 1 Mes: {m.get('Var_1M', 'N/D')}% | P/BV {m['P/BV']} | RSI {m['RSI']} | Vol: ${m['Vol_ARS_M']} M de Pesos | {m['Lectura']}\n"
        
        p += "\nESTRUCTURA TU RESPUESTA EN 4 BLOQUES:\n1. Macro Local e Internacional (Interpretación del Riesgo País y Tasa Real)\n2. Valuación Sectorial\n3. Matriz de Oportunidades Merval (Alerta sobre Value Traps si P/BV es bajo por distorsión)\n4. Escenarios (Base/Bear) y Estrategia Escalonada."
        
        return f"<div style='background-color:#0d1117; padding:15px; border-radius:8px;'><pre style='color:#c9d1d9; font-family:monospace;'>{p}</pre></div>"
    except Exception as e: return f"Error generador IA: {e}"
