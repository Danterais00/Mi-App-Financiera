import requests
import feedparser
import yfinance as yf
import pandas as pd
import streamlit as st
import logging

# --- CONFIGURACIÓN DE LOGS ---
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

@st.cache_data(ttl=1800)
def obtener_macro_argentina():
    datos = {
        "dolares": [], "riesgo_pais": None, 
        "merval": {"valor": None, "var_diaria": None, "var_1m": None, "var_6m": None, "var_1y": None},
        "inflacion": None, "tasa_bcra": None, "reservas": None
    }
    
    try:
        res = requests.get("https://dolarapi.com/v1/dolares", timeout=15)
        if res.status_code == 200:
            for d in res.json():
                if d["casa"] in ["oficial", "blue", "bolsa", "contadoconliqui", "tarjeta"]:
                    nombre = "MEP" if d["casa"] == "bolsa" else "CCL" if d["casa"] == "contadoconliqui" else d["casa"].capitalize()
                    datos["dolares"].append({"nombre": nombre, "compra": d["compra"], "venta": d["venta"]})
    except Exception as e: logger.warning(f"Error DolarAPI: {e}")
    
    try:
        res_rp = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", timeout=15)
        if res_rp.status_code == 200:
            data_rp = res_rp.json()
            if isinstance(data_rp, list) and len(data_rp) > 0:
                datos["riesgo_pais"] = {"valor": data_rp[-1]["valor"], "variacion": ""}
        else: raise Exception("Saltar al respaldo")
    except Exception as e:
        try:
            res_rp_alt = requests.get("https://mercados.ambito.com/riesgopais/info", headers=HEADERS, timeout=15)
            if res_rp_alt.status_code == 200 and "valor" in res_rp_alt.json():
                datos["riesgo_pais"] = {"valor": res_rp_alt.json().get("valor"), "variacion": res_rp_alt.json().get("variacion")}
        except Exception as e2: logger.warning(f"Error Riesgo País (ambos): {e2}")

    try:
        res_inf = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", timeout=15)
        if res_inf.status_code == 200:
            data_inf = res_inf.json()
            if isinstance(data_inf, list) and len(data_inf) > 0:
                datos["inflacion"] = float(data_inf[-1]["valor"]) 
    except Exception as e: logger.warning(f"Error Inflación: {e}")

    try:
        res_tasa = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/politicaMonetaria", timeout=15)
        if res_tasa.status_code == 200:
            data_tasa = res_tasa.json()
            if isinstance(data_tasa, list):
                for item in reversed(data_tasa):
                    val = item.get("valor") or item.get("tasa")
                    if val is not None:
                        tasa_num = float(val)
                        datos["tasa_bcra"] = tasa_num * 100 if tasa_num < 2 else tasa_num
                        break 
        if datos["tasa_bcra"] is None: raise Exception("Saltar a Plazo Fijo")
    except Exception as e:
        try:
            res_tasa_alt = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo", timeout=15)
            if res_tasa_alt.status_code == 200:
                data_tasa_alt = res_tasa_alt.json()
                if isinstance(data_tasa_alt, list):
                    for item in reversed(data_tasa_alt):
                        val_alt = item.get("valor") or item.get("tasa")
                        if val_alt is not None:
                            tasa_num = float(val_alt)
                            datos["tasa_bcra"] = tasa_num * 100 if tasa_num < 2 else tasa_num
                            break
        except Exception as e2: logger.warning(f"Error Tasa BCRA: {e2}")

    try:
        res_bcra = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", timeout=15)
        if res_bcra.status_code == 200:
            data_bcra = res_bcra.json()
            if isinstance(data_bcra, list):
                for item in reversed(data_bcra):
                    if item.get("valor") is not None:
                        datos["reservas"] = float(item["valor"])
                        break
    except Exception as e: logger.warning(f"Error Reservas BCRA: {e}")

    try:
        merv = yf.Ticker("^MERV").history(period="1y")
        if len(merv) >= 2:
            act = merv['Close'].iloc[-1]
            datos["merval"]["valor"] = float(act)
            datos["merval"]["var_diaria"] = float(((act / merv['Close'].iloc[-2]) - 1) * 100)
            if len(merv) >= 21: datos["merval"]["var_1m"] = float(((act / merv['Close'].iloc[-21]) - 1) * 100)
            if len(merv) >= 126: datos["merval"]["var_6m"] = float(((act / merv['Close'].iloc[-126]) - 1) * 100)
            if len(merv) >= 250: datos["merval"]["var_1y"] = float(((act / merv['Close'].iloc[0]) - 1) * 100)
    except Exception as e: logger.warning(f"Error Merval: {e}")
    
    return datos

@st.cache_data(ttl=3600)
def obtener_macro_internacional():
    datos = {}
    tickers_macro = {
        "S&P 500 (Global)": "^GSPC",
        "Nasdaq (Tech)": "^IXIC",
        "Russell 2000 (Small Caps)": "^RUT",
        "Oro (Refugio)": "GC=F",
        "Petróleo Crudo (WTI)": "CL=F", 
        "DXY (Índice Dólar)": "DX-Y.NYB",
        "VIX (Miedo)": "^VIX",
        "Bono 10Y EE.UU (%)": "^TNX"
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
    activos_arg = {"YPF": "Energía", "GGAL": "Financiero", "BMA": "Financiero", "PAMP": "Energía", "CEPU": "Utilities"}
    activos_usa = {"SPY": "S&P 500", "QQQ": "Nasdaq", "XLE": "Energía", "XLF": "Financiero", "XLK": "Tecnología", "XLV": "Salud"}
    
    valuaciones = {"ARG": [], "USA": []}
    
    for ticker, sector in {**activos_arg, **activos_usa}.items():
        try:
            tk = yf.Ticker(ticker)
            info = tk.info
            pe = info.get("trailingPE") or info.get("forwardPE")
            pb = info.get("priceToBook")
            roe = info.get("returnOnEquity")
            dy = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
            
            dy_str = "N/D"
            if dy is not None:
                dy_val = dy * 100 if dy < 0.20 else dy
                dy_str = f"{dy_val:.2f}%"
            
            data = {
                "Activo": ticker,
                "Sector": sector,
                "Período": "Actual (TTM)",
                "P/E": f"{pe:.2f}" if pe else "N/D",
                "P/B": f"{pb:.2f}" if pb else "N/D",
                "ROE (%)": f"{roe*100:.1f}%" if roe else "N/D",
                "Div. Yield (%)": dy_str
            }
            if ticker in activos_arg: valuaciones["ARG"].append(data)
            else: valuaciones["USA"].append(data)
        except Exception as e: logger.warning(f"Error valuación {ticker}: {e}")
    return valuaciones

@st.cache_data(ttl=3600)
def obtener_datos_gics():
    etfs_sectores = {
        "Tecnología": "XLK", "Financiero": "XLF", "Energía": "XLE", 
        "Salud": "XLV", "Industriales": "XLI", "Cons. Discrecional": "XLY", 
        "Cons. Básico": "XLP", "Utilities": "XLU", "Materiales": "XLB", 
        "Real Estate": "XLRE", "Comunicaciones": "XLC"
    }
    
    pe_historico = {
        "Tecnología": 23.0, "Financiero": 13.5, "Energía": 14.5, 
        "Salud": 17.5, "Industriales": 18.0, "Cons. Discrecional": 24.0, 
        "Cons. Básico": 20.0, "Utilities": 17.5, "Materiales": 16.5, 
        "Real Estate": 35.0, "Comunicaciones": 19.0
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
        try:
            tk = yf.Ticker(ticker)
            info = tk.info
            pe = info.get("trailingPE") or info.get("forwardPE")
            pe_val = float(pe) if pe else None
            
            var_1m, var_6m = 0.0, 0.0
            if not df_close.empty and ticker in df_close.columns:
                serie = df_close[ticker].dropna()
                if len(serie) >= 20:
                    precio_actual = serie.iloc[-1]
                    precio_1m = serie.iloc[-21] if len(serie) >= 21 else precio_actual
                    precio_6m = serie.iloc[0]
                    var_1m = ((precio_actual / precio_1m) - 1) * 100
                    var_6m = ((precio_actual / precio_6m) - 1) * 100
            
            score = 50.0 
            score += (var_6m * 1.5) 
            
            if pe_val:
                benchmark = pe_historico.get(sector, 18.0)
                desviacion = (pe_val / benchmark) - 1 
                
                if desviacion < -0.15: score += 15       
                elif -0.15 <= desviacion <= 0.05: score += 5  
                elif 0.05 < desviacion <= 0.20: score -= 5    
                elif desviacion > 0.20: score -= 10      
            
            score = max(0, min(100, int(score))) 
            
            datos_sectores.append({
                "Sector": sector,
                "ETF": ticker,
                "P/E": pe_val,
                "1M (%)": var_1m,
                "6M (%)": var_6m,
                "Score": score
            })
        except Exception as e:
            logger.warning(f"Error procesando {sector}: {e}")
            datos_sectores.append({
                "Sector": sector, "ETF": ticker, "P/E": None,
                "1M (%)": 0.0, "6M (%)": 0.0, "Score": 50
            })
        
    return sorted(datos_sectores, key=lambda x: x["Score"], reverse=True)


def calcular_rsi_serie(serie, period=14):
    """Calcula el RSI (Relative Strength Index) de una serie de pandas"""
    delta = serie.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=3600)
def obtener_datos_merval():
    """Descarga e itera sobre todas las acciones del Merval y Panel General para el Screener"""
    # Panel Líder completo (22 Tickers)
    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", 
             "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", 
             "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    
    # Selección de los más líquidos del Panel General (~22 Tickers)
    general = ["AGRO.BA", "AUSO.BA", "BHIP.BA", "BOLT.BA", "BPAT.BA", "CAPX.BA", "CECO2.BA", 
               "CELU.BA", "CGPA2.BA", "CTIO.BA", "DGCU2.BA", "FERR.BA", "GBAN.BA", "GCLA.BA", 
               "HAVA.BA", "INVJ.BA", "LEDE.BA", "METR.BA", "MOLI.BA", "MORI.BA", "OEST.BA", "SAMI.BA"]
    
    todos_los_tickers = lider + general
    resultados = []
    
    try:
        # Descarga masiva para hacer el cálculo del RSI (últimos 3 meses)
        hist_data = yf.download(todos_los_tickers, period="3mo", progress=False)
        df_close = hist_data['Close'] if 'Close' in hist_data else pd.DataFrame()
    except Exception as e:
        logger.warning(f"Error en descarga masiva Merval: {e}")
        df_close = pd.DataFrame()

    for ticker in todos_los_tickers:
        try:
            panel = "Principal" if ticker in lider else "General"
            tk = yf.Ticker(ticker)
            info = tk.info
            
            # Limpiar el ticker para visualización
            ticker_limpio = ticker.replace(".BA", "")
            empresa = info.get("shortName", ticker_limpio)
            
            # Extraer ratios fundamentales
            pe = info.get("trailingPE", info.get("forwardPE"))
            pbv = info.get("priceToBook")
            
            pe_val = round(pe, 2) if isinstance(pe, (int, float)) else None
            pbv_val = round(pbv, 2) if isinstance(pbv, (int, float)) else None
            
            # Calcular RSI y Tendencia
            rsi_val, tendencia = None, "N/D"
            if not df_close.empty and ticker in df_close.columns:
                serie = df_close[ticker].dropna()
                if len(serie) >= 15:
                    rsi_serie = calcular_rsi_serie(serie)
                    if not rsi_serie.empty and not pd.isna(rsi_serie.iloc[-1]):
                        rsi_val = round(float(rsi_serie.iloc[-1]), 2)
                        
                        # Tendencia básica por SMA de 20 días
                        sma20 = serie.rolling(window=20).mean().iloc[-1]
                        precio_actual = serie.iloc[-1]
                        tendencia = "Alcista" if precio_actual > sma20 else "Bajista"

            # Redacción Dinámica de la Lectura del Asesor
            lectura = "Evaluando activo..."
            if rsi_val is not None:
                if rsi_val > 70:
                    lectura = "¡Precaución! Indicador RSI de euforia. Posible toma de ganancias inminente."
                elif rsi_val < 35:
                    lectura = "Oportunidad Técnica: Acción castigada (Sobreventa). Posible rebote."
                else:
                    if pbv_val and pbv_val < 1:
                        lectura = "Zona neutral, pero cotiza muy barata (P/BV < 1). Buena para acumular."
                    else:
                        lectura = "Lateralizando en zona de equilibrio. Sin urgencia técnica."
                        
                if panel == "General":
                    lectura += " (Atención: Liquidez limitada en Panel General)."

            resultados.append({
                "Ticker": ticker_limpio,
                "Empresa": empresa,
                "Panel": panel,
                "P/E": pe_val,
                "P/BV": pbv_val,
                "RSI": rsi_val,
                "Tendencia": tendencia,
                "Lectura": lectura
            })
        except Exception as e:
            logger.warning(f"No se pudieron cargar datos para {ticker}: {e}")
            
    # Ordenamos por defecto: Las más sobrevendidas (menor RSI) primero
    return sorted(resultados, key=lambda x: x["RSI"] if x["RSI"] is not None else 999)

@st.cache_data(ttl=1800)
def obtener_noticias_acciones(lista_tickers):
    noticias = {}
    for ticker in lista_tickers[:6]:
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
            feed = feedparser.parse(url)
            entradas = []
            for entry in feed.entries[:3]:
                entradas.append({"titulo": entry.title, "link": entry.link, "fecha": entry.published})
            noticias[ticker] = entradas
        except Exception as e: logger.warning(f"Error noticias {ticker}: {e}"); noticias[ticker] = []
    return noticias


# --- LA SOLUCIÓN 100% INFALIBLE Y COMPLETA ---
@st.cache_data(ttl=3600)
def generar_analisis_ia(macro_arg, macro_int, datos_gics):
    try:
        valuaciones = obtener_valuaciones_mercado()
        datos_merval = obtener_datos_merval()
        
        rp_val = macro_arg.get('riesgo_pais', {}).get('valor', 'N/D') if macro_arg.get('riesgo_pais') else 'N/D'
        inf_arg = macro_arg.get('inflacion', 'N/D')
        tasa_arg = macro_arg.get('tasa_bcra', 'N/D')
        merval_val = macro_arg.get('merval', {}).get('valor', 'N/D')
        reservas_val = macro_arg.get('reservas', 'N/D')
        
        dolares = macro_arg.get("dolares", [])
        brecha_str = "N/D"
        if dolares:
            try:
                val_oficial = next((float(d['venta']) for d in dolares if d['nombre'] == 'Oficial'), None)
                val_ccl = next((float(d['venta']) for d in dolares if d['nombre'] == 'CCL'), None)
                if val_oficial and val_ccl:
                    brecha = ((val_ccl / val_oficial) - 1) * 100
                    brecha_str = f"{brecha:.1f}%"
            except: pass
            
        def get_m(key): 
            return macro_int.get(key, {}).get('valor', 'N/D') if key in macro_int else 'N/D'
            
        bono_val = get_m('Bono 10Y EE.UU (%)')
        inf_us_val = get_m('Inflación EE.UU YoY (%)')
        curva_val = get_m('Yield Curve 2Y-10Y (pts)')
        oro_val = get_m('Oro (Refugio)')
        petroleo_val = get_m('Petróleo Crudo (WTI)')
        sp500_val = get_m('S&P 500 (Global)')
        nasdaq_val = get_m('Nasdaq (Tech)')
        
        prompt = (
            "Actúa como un Asesor Financiero experto y práctico para un inversor individual residente en Argentina.\n"
            "Tu objetivo es traducir los datos de mercado en decisiones de inversión claras, directas y sin jerga abstracta. "
            "Si mencionas un dato técnico, explica inmediatamente en qué afecta al bolsillo o a la decisión de comprar/vender.\n\n"
            
            "REGLAS ESTRICTAS DE RESPUESTA:\n"
            "1. NO hables en lenguaje teórico de Wall Street. Usa lenguaje sencillo.\n"
            "2. Provee EJEMPLOS CONCRETOS. Si sugieres Renta Fija Argentina, di si conviene comprar 'Lecaps' (Letras), 'Obligaciones Negociables (ONs)' o 'Bonos Soberanos (AL30/GD30)'.\n"
            "3. Si sugieres CEDEARs, menciona los tickers exactos (ej. SPY, QQQ, AAPL).\n"
            "4. Utiliza el formato de Semáforo: 🟢 (Comprar), 🟡 (Mantener/Neutro), 🔴 (Vender/Evitar).\n"
            "5. APLICA LA METODOLOGÍA DEL ASESOR PARA EL MERVAL: Busca Valor (P/BV bajo o P/E bajo), Momento de Entrada (NO comprar si RSI > 70, sugerir compra si RSI < 35, neutral 40-60), y evalúa el Riesgo de Liquidez (advierte si la sugerencia es del Panel General).\n\n"
            
            "ESTRUCTURA OBLIGATORIA DE TU RESPUESTA:\n"
            "### 1. Resumen Macro (Traducido al Inversor)\n"
            "[Explicación breve de si el mundo y Argentina están para tomar riesgo o ser conservadores]\n\n"
            "### 2. Oportunidades en Renta Fija Local (Pesos y Dólares)\n"
            "[Emoji] **Instrumentos Recomendados:** [Por qué elegirlos y tickers/tipos concretos]\n\n"
            "### 3. Oportunidades Globales (CEDEARs)\n"
            "[Emoji] **Sectores y Acciones a mirar:** [Explicación basada en los scores y las valuaciones. Tickers concretos]\n\n"
            "### 4. Oportunidades en el Merval Local (Pesos)\n"
            "[Emoji] **Acciones Argentinas:** [Analiza la tabla del Merval aplicando las reglas de P/BV y RSI]\n\n"
            
            "--- INICIO DE LOS DATOS RECOPILADOS (HOY) ---\n\n"
            
            "**MACROECONOMÍA ARGENTINA:**\n"
            f"- S&P Merval: {merval_val}\n"
            f"- Riesgo País: {rp_val} puntos\n"
            f"- Inflación Mensual: {inf_arg}%\n"
            f"- Tasa de Interés BCRA: {tasa_arg}%\n"
            f"- Brecha Cambiaria (CCL vs Oficial): {brecha_str}\n"
            f"- Reservas BCRA: USD {reservas_val} millones\n\n"
            
            "**MACROECONOMÍA INTERNACIONAL:**\n"
            f"- S&P 500: {sp500_val}\n"
            f"- Nasdaq: {nasdaq_val}\n"
            f"- Oro: {oro_val}\n"
            f"- Petróleo WTI: {petroleo_val}\n"
            f"- Bono del Tesoro 10 Años (Rendimiento): {bono_val}%\n"
            f"- Inflación Anual EE.UU: {inf_us_val}%\n"
            f"- Curva Inversión (2Y-10Y): {curva_val} puntos\n\n"
            
            "**VALUACIONES ACTUALES (NIVEL 2):**\n"
        )
        
        prompt += "- Mercado USA (ETFs e Índices):\n"
        for v in valuaciones.get("USA", []): prompt += f"  * {v['Activo']} ({v['Sector']}) -> P/E: {v['P/E']} | ROE: {v['ROE (%)']}\n"
            
        prompt += "- ADRs Argentinos:\n"
        for v in valuaciones.get("ARG", []): prompt += f"  * {v['Activo']} ({v['Sector']}) -> P/E: {v['P/E']} | ROE: {v['ROE (%)']}\n"
            
        prompt += "\n**PUNTAJES SECTORIALES GICS:**\n"
        for g in datos_gics:
            pe_str = f"{g['P/E']:.2f}" if g['P/E'] else "N/D"
            prompt += f"- Sector {g['Sector']} (ETF: {g['ETF']}) -> Score Quant: {g['Score']}/100 | Rendimiento 6M: {g['6M (%)']:.1f}% | P/E Actual: {pe_str}\n"

        # Filtramos un poco para la IA para no sobrecargar el prompt con 45 acciones
        top_interesantes = [m for m in datos_merval if (m['RSI'] and m['RSI'] < 40) or (m['RSI'] and m['RSI'] > 70) or (m['P/BV'] and m['P/BV'] < 1)][:15]
        prompt += "\n**TABLERO MERVAL (DESTACADOS DEL SCREENER):**\n"
        for m in top_interesantes:
            prompt += f"- {m['Ticker']} ({m['Empresa']}): P/E: {m['P/E']}x | P/BV: {m['P/BV']}x | RSI: {m['RSI']} | Panel: {m['Panel']} | Lectura: {m['Lectura']}\n"

        prompt += "\n--- FIN DE LOS DATOS ---\n¡Redacta tu análisis ahora aplicando estrictamente tus nuevas reglas!"

        mensaje_ui = (
            '<div style="margin-bottom: 15px; font-size: 1.05rem; color: #e2e8f0;">'
            '💡 <b>¡Tu Compilado Integral está listo!</b><br><br>'
            'Hemos actualizado las instrucciones. Ahora la IA analizará <b>todas las tablas</b> (Macro, Valuaciones, Sectores y <b>Merval Local</b>) y te dará recomendaciones prácticas con <b>instrumentos operables y aplicando tus propios filtros de análisis técnico y fundamental.</b><br><br>'
            '<b>Copia el texto del recuadro a continuación y pégalo en tu ChatGPT, Claude o Gemini web.</b>'
            '</div>'
            '<div style="background-color: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #30363d; overflow-x: auto;">'
            f'<pre style="color: #c9d1d9; font-family: monospace; font-size: 0.9rem; margin: 0; white-space: pre-wrap;">{prompt}</pre>'
            '</div>'
        )
        return mensaje_ui

    except Exception as e: 
        return f"❌ **Error al generar el compilado de datos:** Detalle: {e}"
