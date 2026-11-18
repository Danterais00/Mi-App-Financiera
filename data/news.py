import requests
import feedparser
import yfinance as yf
import pandas as pd
import streamlit as st
import logging
import time
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

@st.cache_data(ttl=1800)
def obtener_datos_criticos_puente():
    url_json = "https://raw.githubusercontent.com/Danterais00/Mi-App-Financiera/refs/heads/main/datos_criticos.json"
    try:
        respuesta = requests.get(url_json, timeout=5)
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
    except Exception as e:
        return {}

@st.cache_data(ttl=1800)
def obtener_macro_argentina():
    datos_UI = {
        "dolares": [],
        "riesgo_pais": None, 
        "merval": {"valor": None},
        "merval_usd": {"valor": None},
        "bono_al30": {"valor": None},
        "bono_al30d": {"valor": None},
        "inflacion": None,
        "tasa_bcra": None,
        "reservas": None
    }
    
    # 1. Leer datos reales extraídos por el Puente GitHub (sin valores estáticos)
    datos_puente = obtener_datos_criticos_puente()
    if datos_puente and "macro_arg_critica" in datos_puente:
        mc = datos_puente["macro_arg_critica"]
        datos_UI["dolares"] = mc.get("dolares", [])
        datos_UI["merval"]["valor"] = mc.get("merval_ars")
        datos_UI["merval_usd"]["valor"] = mc.get("merval_usd")
        datos_UI["bono_al30"]["valor"] = mc.get("bono_al30")
        datos_UI["bono_al30d"]["valor"] = mc.get("bono_al30d")
        datos_UI["tasa_bcra"] = mc.get("tasa_referencia")
        datos_UI["reservas"] = mc.get("reservas_m")

    # 2. Inflación Mensual (ArgentinaDatos)
    try:
        res_inf = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", headers=HEADERS, timeout=10)
        if res_inf.status_code == 200 and len(res_inf.json()) > 0:
            datos_UI["inflacion"] = round(float(res_inf.json()[-1]["valor"]), 1)
    except Exception as e:
        logger.warning(f"Error Inflación: {e}")

    # 3. Riesgo País en Puntos Básicos (ArgentinaDatos)
    try:
        res_rp = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", headers=HEADERS, timeout=10)
        if res_rp.status_code == 200 and len(res_rp.json()) > 0:
            datos_UI["riesgo_pais"] = {"valor": round(float(res_rp.json()[-1]["valor"])), "variacion": ""}
    except Exception as e:
        logger.warning(f"Error Riesgo País: {e}")

    # 4. Respaldo directo en vivo si el puente aún no corrió para Tasa, Reservas o AL30
    if datos_UI["tasa_bcra"] is None:
        try:
            res_tasa = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/depositos30Dias", headers=HEADERS, timeout=10)
            if res_tasa.status_code == 200 and len(res_tasa.json()) > 0:
                val = float(res_tasa.json()[-1].get("valor", 0))
                if val > 0:
                    datos_UI["tasa_bcra"] = round(val * 100, 1) if val < 2 else round(val, 1)
        except: pass

    if datos_UI["reservas"] is None:
        try:
            res_res = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", headers=HEADERS, timeout=10)
            if res_res.status_code == 200 and len(res_res.json()) > 0:
                val_r = float(res_res.json()[-1].get("valor", 0))
                if val_r > 0:
                    datos_UI["reservas"] = round(val_r)
        except: pass

    if datos_UI["bono_al30"]["valor"] is None:
        try:
            res_al30 = requests.get("https://data912.com/live/arg_bonds", headers=HEADERS, timeout=10)
            if res_al30.status_code == 200:
                for b in res_al30.json():
                    if b.get("symbol") == "AL30" or b.get("ticker") == "AL30":
                        p = float(b.get("c", b.get("price", 0)))
                        if p > 0:
                            datos_UI["bono_al30"]["valor"] = round(p * 100, 2) if p < 2000 else round(p, 2)
                            break
        except: pass
    
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

    try:
        if "FRED_API_KEY" in st.secrets:
            api_key = st.secrets["FRED_API_KEY"]
            fred_series = {
                "Tasa FED (%)": {"id": "FEDFUNDS", "units": "lin"},
                "Inflación EE.UU YoY (%)": {"id": "CPIAUCSL", "units": "pc1"},
                "Yield Curve 2Y-10Y (pts)": {"id": "T10Y2Y", "units": "lin"},
                "Desempleo EE.UU (%)": {"id": "UNRATE", "units": "lin"}
            }
            for nombre, config in fred_series.items():
                datos[nombre] = {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None}
                url = f"https://api.stlouisfed.org/fred/series/observations?series_id={config['id']}&api_key={api_key}&file_type=json&units={config['units']}&sort_order=desc&limit=15"
                try:
                    res = requests.get(url, timeout=10)
                    if res.status_code == 200:
                        obs = res.json().get("observations", [])
                        valid_obs = [float(o["value"]) for o in obs if o["value"] != "."]
                        if len(valid_obs) >= 1:
                            act = valid_obs[0]
                            datos[nombre]["valor"] = act
                            if len(valid_obs) >= 2:
                                datos[nombre]["var_diaria"] = act - valid_obs[1] 
                                datos[nombre]["var_1m"] = act - valid_obs[1] 
                            if len(valid_obs) >= 7: datos[nombre]["var_6m"] = act - valid_obs[6]
                            if len(valid_obs) >= 13: datos[nombre]["var_1y"] = act - valid_obs[12]
                except Exception as e: logger.warning(f"Error extrayendo {nombre} de FRED: {e}")
    except Exception as e: logger.warning(f"Error FRED general: {e}")
    
    return datos

@st.cache_data(ttl=3600)
def obtener_valuaciones_mercado():
    datos_puente = obtener_datos_criticos_puente()
    valuaciones = {"ARG": [], "USA": []}
    
    if datos_puente:
        for ticker, info in datos_puente.get("valuaciones_arg", {}).items():
            valuaciones["ARG"].append({
                "Activo": ticker,
                "Sector": info.get("Sector", "N/D"),
                "Período": "Actual (TTM)",
                "P/E": str(info.get("P/E", "N/D")),
                "ROE (%)": str(info.get("ROE (%)", "N/D"))
            })
        for ticker, info in datos_puente.get("valuaciones_usa", {}).items():
            valuaciones["USA"].append({
                "Activo": ticker,
                "Sector": info.get("Sector", "N/D"),
                "Período": "Actual (TTM)",
                "P/E": str(info.get("P/E", "N/D")),
                "ROE (%)": str(info.get("ROE (%)", "N/D"))
            })
    return valuaciones

@st.cache_data(ttl=3600)
def obtener_datos_gics():
    etfs_sectores = {
        "Tecnología": "XLK", "Financiero": "XLF", "Energía": "XLE", 
        "Salud": "XLV", "Industriales": "XLI", "Cons. Discrecional": "XLY", 
        "Cons. Básico": "XLP", "Utilities": "XLU", "Materiales": "XLB", 
        "Real Estate": "XLRE", "Comunicaciones": "XLC"
    }
    
    datos_sectores = []
    tickers = list(etfs_sectores.values())
    
    try:
        hist_data = yf.download(tickers, period="6mo", progress=False)
        df_close = hist_data['Close'] if 'Close' in hist_data else pd.DataFrame()
    except Exception as e:
        logger.warning(f"Error Batch Download GICS: {e}")
        df_close = pd.DataFrame()
        
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
        datos_sectores.append({
            "Sector": sector,
            "ETF": ticker,
            "1M (%)": var_1m,
            "6M (%)": var_6m,
            "Score": score
        })
        
    return sorted(datos_sectores, key=lambda x: x["Score"], reverse=True)

@st.cache_data(ttl=3600)
def obtener_datos_merval():
    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", 
             "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", 
             "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    
    datos_puente = obtener_datos_criticos_puente()
    cotizaciones = datos_puente.get("cotizaciones_merval", {}) if datos_puente else {}
    
    resultados = []
    for ticker_full, d in cotizaciones.items():
        ticker_limpio = ticker_full.replace(".BA", "")
        panel = "Principal" if ticker_full in lider else "General"
        precio = d.get("precio")
        sma20 = d.get("sma20")
        rsi_val = d.get("rsi")
        vol = d.get("volumen_m")
        pe_val = d.get("pe")
        pbv_val = d.get("pbv")
        
        tendencia = "Alcista" if (precio and sma20 and precio > sma20) else "Bajista" if (precio and sma20) else "N/D"
        
        lectura = "Lateralizando en zona de equilibrio."
        if vol is not None and vol < 0.05 and panel == "General":
            lectura = "🔴 RIESGO DE ILIQUIDEZ EXTREMO."
        elif rsi_val is not None:
            if rsi_val > 70:
                lectura = "¡Precaución! RSI en sobrecompra (>70)."
            elif rsi_val < 35:
                lectura = "Oportunidad Técnica: Sobreventa (RSI < 35)."
            elif pbv_val and pbv_val < 1:
                lectura = "Subvaluada por fundamentales (P/BV < 1)."

        resultados.append({
            "Ticker": ticker_limpio,
            "Panel": panel,
            "Precio (ARS)": round(precio, 2) if precio else None,
            "P/E": pe_val,
            "P/BV": pbv_val,
            "Vol. (M)": vol,
            "RSI": rsi_val,
            "Tendencia": tendencia,
            "Lectura": lectura
        })
            
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
        datos_criticos = obtener_datos_criticos_puente()
        
        contexto_noticias = "\n".join([f"- {n}" for n in noticias_globales]) if noticias_globales else "Sin titulares destacados."
        
        # Formateo estandarizado con escalas exactas para evitar errores de interpretación de la IA
        merv_ars = macro_arg.get('merval', {}).get('valor')
        merv_ars_str = f"{merv_ars:,.0f} pts" if merv_ars else "N/D"
        
        merv_usd = macro_arg.get('merval_usd', {}).get('valor')
        merv_usd_str = f"USD {merv_usd:,.0f} (ajustado por CCL)" if merv_usd else "N/D"
        
        al30_ars = macro_arg.get('bono_al30', {}).get('valor')
        al30_str = f"${al30_ars:,.2f} ARS / 100 VN" if al30_ars else "N/D"
        
        rp_val = macro_arg.get('riesgo_pais', {}).get('valor') if macro_arg.get('riesgo_pais') else None
        rp_str = f"{rp_val} pb" if rp_val else "N/D"
        
        inf_val = macro_arg.get('inflacion')
        inf_str = f"{inf_val}% mensual" if inf_val is not None else "N/D"
        
        tasa_val = macro_arg.get('tasa_bcra')
        tasa_str = f"{tasa_val}% TNA (Referencia Plazo Fijo / Mercado)" if tasa_val is not None else "N/D"
        
        res_val = macro_arg.get('reservas')
        res_str = f"USD {res_val:,.0f} M (Reservas Brutas)" if res_val else "N/D"
        
        dolares = macro_arg.get("dolares", [])
        ccl_str, mep_str, brecha_str = "N/D", "N/D", "N/D"
        if dolares:
            val_oficial = next((float(d['venta']) for d in dolares if d['nombre'] == 'Oficial'), None)
            val_ccl = next((float(d['venta']) for d in dolares if d['nombre'] == 'CCL'), None)
            val_mep = next((float(d['venta']) for d in dolares if d['nombre'] == 'MEP'), None)
            if val_ccl: ccl_str = f"${val_ccl:,.2f} ARS"
            if val_mep: mep_str = f"${val_mep:,.2f} ARS"
            if val_oficial and val_ccl:
                brecha_str = f"{((val_ccl / val_oficial) - 1) * 100:.1f}%"
            
        def get_m(key): 
            return macro_int.get(key, {}).get('valor', 'N/D') if key in macro_int else 'N/D'
            
        prompt = (
            "Actúa como un Asesor Financiero experto y práctico para un inversor individual residente en Argentina.\n"
            "Redacta un Resumen Matutino de Mercados con decisiones de inversión concretas basadas estrictamente en los datos estandarizados.\n\n"
            
            "REGLAS ESTRICTAS:\n"
            "1. Respeta exactamente las unidades y escalas provistas en la tabla (pts, USD, pb, ARS / 100 VN, % mensual, % TNA, USD M).\n"
            "2. Compara la Tasa de Referencia en TNA (dividida por 12) contra la Inflación mensual para determinar si la tasa real en pesos es positiva o negativa.\n"
            "3. Analiza el S&P Merval en USD (CCL) como termómetro real de valuación histórica.\n"
            "4. Utiliza Semáforo: 🟢 (Comprar/Sobreponderar), 🟡 (Mantener/Neutro), 🔴 (Evitar/Subponderar).\n"
            "5. Para acciones del Merval, aplica criterios de Valor (P/BV < 1 en Panel Líder) y Momentum Técnico (RSI < 35 sobreventa, RSI > 70 sobrecompra) alertando sobre liquidez.\n\n"
            
            "--- TABLA CONSOLIDADA DE DATOS (ESCALAS ESTANDARIZADAS) ---\n\n"
            "**1. MACROECONOMÍA ARGENTINA:**\n"
            f"| Parámetro | Valor Actual |\n"
            f"| :--- | :--- |\n"
            f"| S&P Merval (ARS) | {merv_ars_str} |\n"
            f"| S&P Merval (USD CCL) | {merv_usd_str} |\n"
            f"| Bono Soberano AL30 | {al30_str} |\n"
            f"| Riesgo País (EMBI+) | {rp_str} |\n"
            f"| Inflación | {inf_str} |\n"
            f"| Tasa Referencia Mercado | {tasa_str} |\n"
            f"| Reservas Internacionales BCRA | {res_str} |\n"
            f"| Dólar CCL / MEP | {ccl_str} / {mep_str} |\n"
            f"| Brecha Cambiaria (CCL vs Oficial) | {brecha_str} |\n\n"
            
            "**2. MACROECONOMÍA INTERNACIONAL:**\n"
            f"- S&P 500: {get_m('S&P 500 (Global)')} pts | Nasdaq: {get_m('Nasdaq (Tech)')} pts | Dow Jones: {get_m('Dow Jones')} pts\n"
            f"- Europa (Euro Stoxx 50): {get_m('Euro Stoxx 50 (Europa)')} pts | Japón (Nikkei 225): {get_m('Nikkei 225 (Japón)')} pts\n"
            f"- DXY (Índice Dólar): {get_m('DXY (Índice Dólar)')} | VIX (Volatilidad): {get_m('VIX (Miedo)')}\n"
            f"- Oro: USD {get_m('Oro (Refugio)')} | Plata: USD {get_m('Plata')} | Cobre: USD {get_m('Cobre (Industrial)')} | WTI: USD {get_m('Petróleo Crudo (WTI)')}\n"
            f"- Bitcoin: USD {get_m('Bitcoin (Cripto)')}\n"
            f"- Bono 10Y EE.UU.: {get_m('Bono 10Y EE.UU (%)')}% | Bono 10Y Japón: {get_m('Bono 10Y Japón (%)')}%\n"
            f"- Tasa FED: {get_m('Tasa FED (%)')}% | Inflación EE.UU. YoY: {get_m('Inflación EE.UU YoY (%)')}% | Desempleo EE.UU.: {get_m('Desempleo EE.UU (%)')}%\n\n"
            
            "**3. TITULARES GLOBALES:**\n"
            f"{contexto_noticias}\n\n"
            
            "**4. VALUACIONES FUNDAMENTALES (P/E y ROE):**\n"
        )
        
        for v in valuaciones.get("USA", []):
            prompt += f"- USA: {v['Activo']} ({v['Sector']}) -> P/E: {v['P/E']}x | ROE: {v['ROE (%)']}\n"
        for v in valuaciones.get("ARG", []):
            prompt += f"- ADR ARG: {v['Activo']} ({v['Sector']}) -> P/E: {v['P/E']}x | ROE: {v['ROE (%)']}\n"
            
        prompt += "\n**5. MOMENTUM SECTORIAL GICS (USA):**\n"
        for g in datos_gics:
            prompt += f"- {g['Sector']} ({g['ETF']}): Score {g['Score']}/100 | 1M: {g['1M (%)']:.1f}% | 6M: {g['6M (%)']:.1f}%\n"

        top_interesantes = [m for m in datos_merval if (m['RSI'] and m['RSI'] < 38) or (m['RSI'] and m['RSI'] > 70) or (m['P/BV'] and m['P/BV'] < 1)][:15]
        prompt += "\n**6. SCREENER MERVAL (DESTACADOS TÉCNICOS Y FUNDAMENTALES):**\n"
        for m in top_interesantes:
            prompt += f"- {m['Ticker']} [{m['Panel']}]: Precio ${m['Precio (ARS)']} | P/E: {m['P/E']}x | P/BV: {m['P/BV']}x | RSI: {m['RSI']} | Vol: {m['Vol. (M)']}M | {m['Lectura']}\n"

        prompt += "\n--- FIN DE LOS DATOS ---\nRedacta tu informe ejecutivo estructurado con recomendaciones accionables."

        mensaje_ui = (
            '<div style="margin-bottom: 15px; font-size: 1.05rem; color: #e2e8f0;">'
            '💡 <b>¡Tu Reporte Matutino Institucional está listo!</b><br><br>'
            'Todos los indicadores cuentan con <b>escalas estandarizadas y datos reales en vivo</b> sin valores congelados. Copia el bloque y pégalo en tu asistente IA.<br><br>'
            '</div>'
            '<div style="background-color: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #30363d; overflow-x: auto;">'
            f'<pre style="color: #c9d1d9; font-family: monospace; font-size: 0.9rem; margin: 0; white-space: pre-wrap;">{prompt}</pre>'
            '</div>'
        )
        return mensaje_ui

    except Exception as e: 
        return f"❌ **Error al generar el compilado de datos:** Detalle: {e}"
