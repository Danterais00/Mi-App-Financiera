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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

@st.cache_data(ttl=300)
def obtener_datos_criticos_puente():
    url_json = "https://raw.githubusercontent.com/Danterais00/Mi-App-Financiera/refs/heads/main/datos_criticos.json"
    try:
        respuesta = requests.get(url_json, timeout=6)
        if respuesta.status_code == 200:
            return respuesta.json()
    except Exception as e:
        logger.warning(f"Error leyendo el JSON puente: {e}")
    return None

@st.cache_data(ttl=86400) 
def obtener_info_ticker_cached(ticker):
    time.sleep(0.3) 
    try:
        info = yf.Ticker(ticker).info
        return dict(info)
    except Exception:
        return {}

@st.cache_data(ttl=300)
def obtener_macro_argentina():
    datos_UI = {
        "dolares": [],
        "riesgo_pais": None, 
        "merval": {"valor": None},
        "merval_usd": {"valor": None},
        "bono_al30": {"valor": None},
        "bono_al30d": {"valor": None},
        "inflacion": None,
        "tasa_tamar": None,
        "tasa_badlar": None,
        "tasa_tna": None,
        "reservas": None
    }
    
    datos_puente = obtener_datos_criticos_puente()
    if datos_puente and "macro_arg_critica" in datos_puente:
        mc = datos_puente["macro_arg_critica"]
        datos_UI["dolares"] = mc.get("dolares", [])
        datos_UI["merval"]["valor"] = mc.get("merval_ars")
        datos_UI["merval_usd"]["valor"] = mc.get("merval_usd")
        datos_UI["bono_al30"]["valor"] = mc.get("bono_al30")
        datos_UI["bono_al30d"]["valor"] = mc.get("bono_al30d")
        datos_UI["tasa_tamar"] = mc.get("tasa_tamar")
        datos_UI["tasa_badlar"] = mc.get("tasa_badlar")
        datos_UI["tasa_tna"] = mc.get("tasa_tna")
        datos_UI["reservas"] = mc.get("reservas_m")

        if datos_UI["merval"]["valor"] is None and "cotizaciones_merval" in datos_puente:
            cot = datos_puente["cotizaciones_merval"]
            p_ggal = cot.get("GGAL.BA", {}).get("precio", 0)
            p_ypfd = cot.get("YPFD.BA", {}).get("precio", 0)
            p_pamp = cot.get("PAMP.BA", {}).get("precio", 0)
            p_bma = cot.get("BMA.BA", {}).get("precio", 0)
            if p_ggal and p_ypfd and p_pamp and p_bma:
                merv_calc = round((p_ggal * 165) + (p_ypfd * 145) + (p_pamp * 110) + (p_bma * 75))
                datos_UI["merval"]["valor"] = merv_calc
                ccl_v = next((float(d['venta']) for d in datos_UI["dolares"] if d['nombre'] == 'CCL'), None)
                if ccl_v and ccl_v > 0:
                    datos_UI["merval_usd"]["valor"] = round(merv_calc / ccl_v)

    try:
        res_inf = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", headers=HEADERS, timeout=10)
        if res_inf.status_code == 200 and len(res_inf.json()) > 0:
            datos_UI["inflacion"] = round(float(res_inf.json()[-1]["valor"]), 1)
    except Exception as e: logger.warning(f"Error Inflación: {e}")

    try:
        res_rp = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", headers=HEADERS, timeout=10)
        if res_rp.status_code == 200 and len(res_rp.json()) > 0:
            datos_UI["riesgo_pais"] = {"valor": round(float(res_rp.json()[-1]["valor"])), "variacion": ""}
    except Exception as e: logger.warning(f"Error Riesgo País: {e}")

    if datos_UI["tasa_tna"] is None or datos_UI["tasa_badlar"] is None or datos_UI["tasa_tamar"] is None:
        try:
            res_tna = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/depositos30Dias", headers=HEADERS, timeout=8)
            if res_tna.status_code == 200 and len(res_tna.json()) > 0:
                val = float(res_tna.json()[-1].get("valor", 0))
                if val > 0 and datos_UI["tasa_tna"] is None:
                    datos_UI["tasa_tna"] = round(val * 100, 2) if val < 2 else round(val, 2)
        except Exception: pass
        try:
            res_pf = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo", headers=HEADERS, timeout=8)
            if res_pf.status_code == 200 and isinstance(res_pf.json(), list):
                tasas_30 = [float(e["tnaClientes"]) * 100 for e in res_pf.json() if e.get("tnaClientes")]
                if tasas_30:
                    if datos_UI["tasa_tna"] is None: datos_UI["tasa_tna"] = round(sum(tasas_30) / len(tasas_30), 2)
                    top5 = sorted(tasas_30, reverse=True)[:5]
                    if datos_UI["tasa_badlar"] is None: datos_UI["tasa_badlar"] = round(sum(top5) / len(top5), 2)
                    if datos_UI["tasa_tamar"] is None: datos_UI["tasa_tamar"] = round(datos_UI["tasa_badlar"] + 0.85, 2)
        except Exception: pass

    if datos_UI["bono_al30"]["valor"] is None:
        try:
            res_al30 = requests.get("https://data912.com/live/arg_bonds", headers=HEADERS, timeout=8)
            if res_al30.status_code == 200:
                for b in res_al30.json():
                    sym = b.get("symbol") or b.get("ticker")
                    p = float(b.get("c", b.get("price", 0)))
                    if sym == "AL30" and p > 0: datos_UI["bono_al30"]["valor"] = round(p * 100, 2) if p < 2000 else round(p, 2)
                    if sym == "AL30D" and p > 0: datos_UI["bono_al30d"]["valor"] = round(p, 2)
        except Exception: pass

    if datos_UI["reservas"] is None:
        try:
            url_res = "https://apis.datos.gob.ar/series/api/series/?ids=300.1_AP_ACT_RESTER_0_M_21&limit=1&sort=desc&format=json"
            r_res = requests.get(url_res, headers=HEADERS, timeout=10)
            if r_res.status_code == 200:
                rows = r_res.json().get("data", [])
                if rows and len(rows[0]) >= 2 and rows[0][1] is not None:
                    val_usd = float(rows[0][1])
                    datos_UI["reservas"] = round(val_usd / 1_000_000) if val_usd > 1_000_000_000 else round(val_usd)
        except Exception as e: logger.warning(f"Error Reservas datos.gob.ar: {e}")
    
    return datos_UI

@st.cache_data(ttl=3600)
def obtener_macro_internacional():
    datos = {}
    tickers_macro = {
        "S&P 500 (Global)": "^GSPC",
        "Dow Jones": "^DJI",
        "Nasdaq (Tech)": "^IXIC",
        "Futuros S&P 500": "ES=F",       
        "Futuros Nasdaq": "NQ=F",        
        "Russell 2000 (Small Caps)": "^RUT",
        "Euro Stoxx 50 (Europa)": "^STOXX50E",
        "Nikkei 225 (Japón)": "^N225",
        "Oro (Refugio)": "GC=F",
        "Plata": "SI=F",                 
        "Cobre (Industrial)": "HG=F",    
        "Petróleo Crudo (WTI)": "CL=F", 
        "DXY (Índice Dólar)": "DX-Y.NYB",
        "VIX (Miedo)": "^VIX",
        "Bono 10Y EE.UU (%)": "^TNX",
        "Bono 10Y Japón (%)": "^JGBS",
        "Bitcoin (Cripto)": "BTC-USD"    
    }
    
    for nombre in tickers_macro.keys():
        datos[nombre] = {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None}
    
    lista_tickers = list(tickers_macro.values())
    try:
        hist_data = yf.download(lista_tickers, period="1y", progress=False)
        if not hist_data.empty and 'Close' in hist_data:
            df_close = hist_data['Close']
            for nombre, t in tickers_macro.items():
                if t in df_close.columns:
                    serie = df_close[t].dropna()
                    if len(serie) >= 2:
                        actual = float(serie.iloc[-1])
                        datos[nombre]["valor"] = actual
                        datos[nombre]["var_diaria"] = float(((actual / serie.iloc[-2]) - 1) * 100)
                        if len(serie) >= 21: datos[nombre]["var_1m"] = float(((actual / serie.iloc[-21]) - 1) * 100)
                        if len(serie) >= 126: datos[nombre]["var_6m"] = float(((actual / serie.iloc[-126]) - 1) * 100)
                        if len(serie) >= 250: datos[nombre]["var_1y"] = float(((actual / serie.iloc[0]) - 1) * 100)
    except Exception as e: logger.warning(f"Error Batch Download Macro: {e}")
    return datos

@st.cache_data(ttl=1800)
def obtener_eventos_macro_eeuu():
    """Descarga los eventos macroeconómicos de la semana (ForexFactory) filtrando los de alto impacto."""
    eventos = []
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.xml", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for event in root.findall("event"):
                impacto = event.find("impact").text if event.find("impact") is not None else ""
                if impacto == "High" or impacto == "Medium":
                    pais = event.find("country").text if event.find("country") is not None else ""
                    if pais == "USD":
                        titulo = event.find("title").text if event.find("title") is not None else ""
                        actual = event.find("actual").text if event.find("actual") is not None else ""
                        forecast = event.find("forecast").text if event.find("forecast") is not None else ""
                        fecha_str = event.find("date").text if event.find("date") is not None else ""
                        hora_str = event.find("time").text if event.find("time") is not None else ""
                        
                        estado = "Pendiente" if not actual else "Publicado"
                        color_act = "#a3a8b8"
                        if actual and forecast:
                            try:
                                a_val = float(actual.replace('%','').replace('B','').replace('K','').replace('M',''))
                                f_val = float(forecast.replace('%','').replace('B','').replace('K','').replace('M',''))
                                color_act = "#2ecca6" if a_val > f_val else "#ff6b6b" if a_val < f_val else "#ffd54f"
                            except: pass
                        
                        if len(eventos) < 10:
                            eventos.append({
                                "Evento": titulo,
                                "Fecha/Hora": f"{fecha_str} {hora_str}",
                                "Estado": estado,
                                "Actual": f"<span style='color:{color_act}; font-weight:bold;'>{actual}</span>" if actual else "-",
                                "Proyección": forecast if forecast else "-"
                            })
    except Exception as e:
        logger.warning(f"Error leyendo ForexFactory: {e}")
    return eventos

@st.cache_data(ttl=3600)
def obtener_valuaciones_mercado():
    datos_puente = obtener_datos_criticos_puente()
    valuaciones = {"ARG": [], "USA": []}
    if datos_puente:
        for ticker, info in datos_puente.get("valuaciones_arg", {}).items():
            valuaciones["ARG"].append({"Activo": ticker, "Sector": info.get("Sector", "N/D"), "Período": "Actual (TTM)", "P/E": str(info.get("P/E", "N/D")), "ROE (%)": str(info.get("ROE (%)", "N/D"))})
        for ticker, info in datos_puente.get("valuaciones_usa", {}).items():
            valuaciones["USA"].append({"Activo": ticker, "Sector": info.get("Sector", "N/D"), "Período": "Actual (TTM)", "P/E": str(info.get("P/E", "N/D")), "ROE (%)": str(info.get("ROE (%)", "N/D"))})
    return valuaciones

@st.cache_data(ttl=3600)
def obtener_datos_gics():
    etfs_sectores = {
        "Tecnología": "XLK", "Financiero": "XLF", "Energía": "XLE", "Salud": "XLV", "Industriales": "XLI", 
        "Cons. Discrecional": "XLY", "Cons. Básico": "XLP", "Utilities": "XLU", "Materiales": "XLB", "Real Estate": "XLRE", "Comunicaciones": "XLC"
    }
    datos_sectores = []
    tickers = list(etfs_sectores.values())
    try:
        hist_data = yf.download(tickers, period="6mo", progress=False)
        df_close = hist_data['Close'] if 'Close' in hist_data else pd.DataFrame()
    except Exception: df_close = pd.DataFrame()
        
    for sector, ticker in etfs_sectores.items():
        var_1m, var_6m = 0.0, 0.0
        if not df_close.empty and ticker in df_close.columns:
            serie = df_close[ticker].dropna()
            if len(serie) >= 20:
                precio_actual = serie.iloc[-1]
                precio_1m = serie.iloc[-21] if len(serie) >= 21 else precio_actual
                precio_6m = serie.iloc[0]
                var_1m = ((precio_actual / precio_1m) - 1) * 100
                var_6m = ((precio_actual / precio_6m) - 1) * 100
        score = max(0, min(100, int(50.0 + (var_6m * 1.5))))
        datos_sectores.append({"Sector": sector, "ETF": ticker, "1M (%)": var_1m, "6M (%)": var_6m, "Score": score})
    return sorted(datos_sectores, key=lambda x: x["Score"], reverse=True)

@st.cache_data(ttl=3600)
def obtener_datos_merval():
    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    datos_puente = obtener_datos_criticos_puente()
    cotizaciones = datos_puente.get("cotizaciones_merval", {}) if datos_puente else {}
    resultados = []
    for ticker_full, d in cotizaciones.items():
        ticker_limpio = ticker_full.replace(".BA", "")
        panel = "Principal" if ticker_full in lider else "General"
        precio, sma20, rsi_val, vol, pe_val, pbv_val = d.get("precio"), d.get("sma20"), d.get("rsi"), d.get("volumen_m"), d.get("pe"), d.get("pbv")
        tendencia = "Alcista" if (precio and sma20 and precio > sma20) else "Bajista" if (precio and sma20) else "N/D"
        lectura = "Lateralizando en zona de equilibrio."
        if vol is not None and vol < 0.05 and panel == "General": lectura = "🔴 RIESGO DE ILIQUIDEZ EXTREMO."
        elif rsi_val is not None:
            if rsi_val > 70: lectura = "¡Precaución! RSI en sobrecompra (>70)."
            elif rsi_val < 35: lectura = "Oportunidad Técnica: Sobreventa (RSI < 35)."
            elif pbv_val and pbv_val < 1: lectura = "Subvaluada por fundamentales (P/BV < 1)."
        resultados.append({"Ticker": ticker_limpio, "Panel": panel, "Precio (ARS)": round(precio, 2) if precio else None, "P/E": pe_val, "P/BV": pbv_val, "Vol. (M)": vol, "RSI": rsi_val, "Tendencia": tendencia, "Lectura": lectura})
    return sorted(resultados, key=lambda x: x["RSI"] if x["RSI"] is not None else 999)

@st.cache_data(ttl=1800)
def obtener_noticias_acciones(lista_tickers):
    noticias = {}
    for ticker in lista_tickers[:6]:
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
            feed = feedparser.parse(url)
            entradas = [{"titulo": e.title, "link": e.link, "fecha": e.published} for e in feed.entries[:3]]
            noticias[ticker] = entradas
        except Exception:
            noticias[ticker] = []
    return noticias

@st.cache_data(ttl=1800)
def obtener_noticias_globales():
    try:
        url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC,CL=F,GC=F,^TNX&region=US&lang=en-US"
        feed = feedparser.parse(url)
        return [entry.title for entry in feed.entries[:5]]
    except Exception:
        return []

@st.cache_data(ttl=3600)
def generar_analisis_ia(macro_arg, macro_int, datos_gics):
    try:
        valuaciones = obtener_valuaciones_mercado()
        datos_merval = obtener_datos_merval()
        noticias_globales = obtener_noticias_globales()
        eventos_eeuu = obtener_eventos_macro_eeuu()
        
        contexto_noticias = "\n".join([f"- {n}" for n in noticias_globales]) if noticias_globales else "Sin titulares destacados."
        
        merv_ars = macro_arg.get('merval', {}).get('valor')
        merv_ars_str = f"{merv_ars:,.0f} pts" if merv_ars else "N/D"
        merv_usd = macro_arg.get('merval_usd', {}).get('valor')
        merv_usd_str = f"USD {merv_usd:,.0f} (ajustado por CCL)" if merv_usd else "N/D"
        al30_ars = macro_arg.get('bono_al30', {}).get('valor')
        al30_usd = macro_arg.get('bono_al30d', {}).get('valor')
        al30_str = f"${al30_ars:,.2f} ARS / 100 VN (USD {al30_usd})" if (al30_ars and al30_usd) else f"${al30_ars:,.2f} ARS / 100 VN" if al30_ars else "N/D"
        rp_val = macro_arg.get('riesgo_pais', {}).get('valor') if macro_arg.get('riesgo_pais') else None
        rp_str = f"{rp_val} pb" if rp_val else "N/D"
        inf_val = macro_arg.get('inflacion')
        inf_str = f"{inf_val}% mensual" if inf_val is not None else "N/D"
        tamar_val = macro_arg.get('tasa_tamar')
        tamar_str = f"{tamar_val}% TNA (Mayorista +$1.000M)" if tamar_val is not None else "N/D"
        badlar_val = macro_arg.get('tasa_badlar')
        badlar_str = f"{badlar_val}% TNA (Mayorista +$1M)" if badlar_val is not None else "N/D"
        tna_val = macro_arg.get('tasa_tna')
        tna_str = f"{tna_val}% TNA (Plazo Fijo Minorista 30d)" if tna_val is not None else "N/D"
        res_val = macro_arg.get('reservas')
        res_str = f"USD {res_val:,.0f} M (Reservas Brutas)" if res_val else "N/D"
        
        dolares = macro_arg.get("dolares", [])
        ccl_str, mep_str, brecha_str, mayorista_str = "N/D", "N/D", "N/D", "N/D"
        if dolares:
            val_oficial = next((float(d['venta']) for d in dolares if d['nombre'] == 'Oficial'), None)
            val_ccl = next((float(d['venta']) for d in dolares if d['nombre'] == 'CCL'), None)
            val_mep = next((float(d['venta']) for d in dolares if d['nombre'] == 'MEP'), None)
            val_mayo = next((float(d['venta']) for d in dolares if d['nombre'] == 'Mayorista'), None)
            if val_ccl: ccl_str = f"${val_ccl:,.2f} ARS"
            if val_mep: mep_str = f"${val_mep:,.2f} ARS"
            if val_mayo: mayorista_str = f"${val_mayo:,.2f} ARS"
            if val_oficial and val_ccl: brecha_str = f"{((val_ccl / val_oficial) - 1) * 100:.1f}%"
            
        def get_m(key): return macro_int.get(key, {}).get('valor', 'N/D') if key in macro_int else 'N/D'
            
        prompt = (
            "Actúa como un Asesor Financiero experto y práctico para un inversor individual residente en Argentina.\n"
            "Redacta un Resumen Matutino de Mercados con decisiones de inversión concretas basadas estrictamente en los datos estandarizados.\n\n"
            "--- TABLA CONSOLIDADA DE DATOS ---\n\n"
            "**1. MACROECONOMÍA ARGENTINA:**\n"
            f"| S&P Merval (ARS) | {merv_ars_str} |\n"
            f"| S&P Merval (USD CCL) | {merv_usd_str} |\n"
            f"| Bono Soberano AL30 | {al30_str} |\n"
            f"| Riesgo País (EMBI+) | {rp_str} |\n"
            f"| Inflación | {inf_str} |\n"
            f"| Tasa TAMAR | {tamar_str} |\n"
            f"| Tasa BADLAR | {badlar_str} |\n"
            f"| Tasa Plazo Fijo (TNA) | {tna_str} |\n"
            f"| Reservas Internacionales BCRA | {res_str} |\n"
            f"| Dólar CCL / MEP / Mayorista | {ccl_str} / {mep_str} / {mayorista_str} |\n"
            f"| Brecha Cambiaria (CCL vs Oficial) | {brecha_str} |\n\n"
            
            "**2. MACROECONOMÍA INTERNACIONAL:**\n"
            f"- S&P 500: {get_m('S&P 500 (Global)')} pts | Nasdaq: {get_m('Nasdaq (Tech)')} pts\n"
            f"- DXY: {get_m('DXY (Índice Dólar)')} | VIX: {get_m('VIX (Miedo)')}\n"
            f"- Oro: USD {get_m('Oro (Refugio)')} | WTI: USD {get_m('Petróleo Crudo (WTI)')} | Bitcoin: USD {get_m('Bitcoin (Cripto)')}\n"
            f"- Bono 10Y EE.UU.: {get_m('Bono 10Y EE.UU (%)')}%\n\n"
            
            "**3. EVENTOS MACRO EE.UU. RECIENTES (Calendario Económico):**\n"
        )
        if eventos_eeuu:
            for ev in eventos_eeuu: prompt += f"- {ev['Evento']}: Actual {ev['Actual']} vs Proyección {ev['Proyección']}\n"
        else:
            prompt += "- Sin eventos macro relevantes programados para hoy.\n"
            
        prompt += f"\n**4. TITULARES GLOBALES:**\n{contexto_noticias}\n\n**5. VALUACIONES FUNDAMENTALES (P/E y ROE):**\n"
        for v in valuaciones.get("USA", []): prompt += f"- USA: {v['Activo']} ({v['Sector']}) -> P/E: {v['P/E']}x | ROE: {v['ROE (%)']}\n"
        for v in valuaciones.get("ARG", []): prompt += f"- ADR ARG: {v['Activo']} ({v['Sector']}) -> P/E: {v['P/E']}x | ROE: {v['ROE (%)']}\n"
            
        prompt += "\n**6. SCREENER MERVAL (DESTACADOS TÉCNICOS Y FUNDAMENTALES):**\n"
        top_interesantes = [m for m in datos_merval if (m['RSI'] and m['RSI'] < 38) or (m['RSI'] and m['RSI'] > 70) or (m['P/BV'] and m['P/BV'] < 1)][:15]
        for m in top_interesantes: prompt += f"- {m['Ticker']}: Precio ${m['Precio (ARS)']} | P/E: {m['P/E']}x | P/BV: {m['P/BV']}x | RSI: {m['RSI']} | {m['Lectura']}\n"

        prompt += "\n--- FIN DE LOS DATOS ---\nRedacta tu informe ejecutivo estructurado con recomendaciones accionables."

        mensaje_ui = (
            '<div style="margin-bottom: 15px; font-size: 1.05rem; color: #e2e8f0;">'
            '💡 <b>¡Tu Reporte Matutino Institucional está listo!</b><br><br>'
            'Copia el bloque y pégalo en tu asistente IA.<br><br>'
            '</div>'
            '<div style="background-color: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #30363d; overflow-x: auto;">'
            f'<pre style="color: #c9d1d9; font-family: monospace; font-size: 0.9rem; margin: 0; white-space: pre-wrap;">{prompt}</pre>'
            '</div>'
        )
        return mensaje_ui

    except Exception as e: 
        return f"❌ **Error al generar el compilado de datos:** Detalle: {e}"
