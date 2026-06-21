import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Terminal Pro: Inteligencia Financiera", layout="wide")

# --- DICCIONARIO DE DEFINICIONES (TOOLTIPS) ---
TOOLTIPS = {
    "Net Income": "indica el beneficio real neto tras restar absolutamente todos los gastos e impuestos.",
    "Cost of Revenue": "Gastos directos para fabricar o entregar el producto.",
    "PER": """0 - 10 (Bajo): indica que la acción está infravalorada o que el mercado tiene serias dudas sobre su futuro crecimiento. 
10 - 17 (Moderado): rango saludable y razonable para empresas establecidas. 
17 - 25 (Alto): acción sobrevalorada o que la empresa tiene buenas expectativas de crecimiento futuro que justifican pagar un precio mayor. 
Más de 25 (Muy alto): Típico de empresas de crecimiento agresivo. Los inversores pagan mucho hoy esperando beneficios gigantescos mañana.""",
    "Margen Neto (%)": "Es la eficiencia operativa. Indica qué porcentaje de las ventas totales se convierte en ganancia limpia.",
    "ROE (%)": "Rentabilidad sobre el capital: mide qué tan bien la directiva multiplica el dinero de los accionistas.",
    "ROA (%)": "Rentabilidad sobre activos: indica la ganancia generada por cada dólard de recurso (propio o deuda) que posee la empresa.",
    "Free Cash Flow": "Caja libre tras gastos operativos y de capital; es el dinero 'real' para dividendos o recompras.",
    "Div Yield (%)": "Rendimiento por dividendo: el interés en efectivo que recibes anualmente por poseer la acción.",
    "Debt/Equity": "Indica el nivel de deuda",
    "Current Ratio": "Mide la capacidad de la empresa para pagar sus deudas de corto plazo.",
    "Quick Ratio": "igual al Current Ratio pero excluye inventarios por ser más difíciles de vender rápido."
}

# --- BARRA LATERAL (ESTRATEGIA) ---
st.sidebar.title("⚙️ Configuración")
modo_estrategia = st.sidebar.radio(
    "Selecciona tu Estrategia:",
    ["Crecimiento (Agresivo)", "Fortaleza (Defensivo)"],
    help="Agresivo: Impulso operativo. Defensivo: Calidad de balance y valor."
)

st.title("🚀 Terminal de Análisis Fundamental Pro")
st.write(f"Modo Activo: **{modo_estrategia}**")
st.info("⚠️ Filtro Elite Activo: Beta < 1.5 y Upside > 0% obligatorio para el TOP 5. PER > 10 para punto de calidad.")

# 2. ENTRADA DE TICKERS
tickers_raw = st.text_input("Tickers (separados por coma):", "BP, CVX, ET, PBR, TEN, VIST, XOM, SHEL, AAPL.BA, MSFT.BA").upper()

def corregir_ticker(t):
    t = t.strip()
    if t == "BRKB": return "BRK-B"
    if t == "BRKA": return "BRK-A"
    return t

if tickers_raw:
    lista_tickers = [corregir_ticker(t) for t in tickers_raw.split(",") if t.strip()][:30]
    
    datos_fundamentales, datos_tecnicos, datos_revenue, datos_eps = [], [], [], []
    analisis_completo = {}
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    posibles_puntos = {ticker: 0 for ticker in lista_tickers}
    fechas_headers = []
    nombres_base = ["4 Trim. atrás", "3 Trim. atrás", "2 Trim. atrás", "1 Trim. atrás", "Último Trim."]

    with st.spinner('Sincronizando fundamentales de forma prioritaria y calculando métricas de mercado...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                if not info or 'currentPrice' not in info:
                    continue  # Si no hay conexión base con el ticker, saltar
            except Exception:
                continue

            # --- CAPTURA CAPA 1: DATOS FUNDAMENTALES (BLINDADO) ---
            p_actual = info.get('currentPrice')
            v_justo = info.get('targetMeanPrice')
            beta = info.get('beta')
            upside = ((v_justo / p_actual) - 1) if p_actual and v_justo else None

            de_raw = info.get('debtToEquity')
            de_final = de_raw / 100 if de_raw is not None else None
            
            net_income = info.get('netIncomeToCommon') or info.get('netIncome')
            total_rev = info.get('totalRevenue')
            gross_prof = info.get('grossProfits')
            cost_of_rev = (total_rev - gross_prof) if (total_rev and gross_prof) else None

            fila_fun = {
                "Ticker": ticker, "Empresa": info.get('longName', 'N/A'),
                "Precio": p_actual, "Fair Value (Target)": v_justo, "Upside (%)": upside,
                "Beta (Volatilidad)": beta,
                "Volumen Promedio": info.get('averageVolume'),
                "Net Income": net_income,
                "Cost of Revenue": cost_of_rev,
                "PER": info.get('trailingPE'), "Margen Neto (%)": info.get('profitMargins'),
                "ROE (%)": info.get('returnOnEquity'), "ROA (%)": info.get('returnOnAssets'),
                "Free Cash Flow": info.get('freeCashflow'), "Div Yield (%)": info.get('dividendYield'),
                "Debt/Equity": de_final, 
                "Current Ratio": info.get('currentRatio'), "Quick Ratio": info.get('quickRatio')
            }
            datos_fundamentales.append(fila_fun)

            # --- CAPTURA CAPA 2: MÓDULO TÉCNICO (AISLADO PARA EVITAR CAÍDAS) ---
            dist_ath, rsi_val, dist_sma = None, None, None
            estado_rsi = "Neutral"
            try:
                hist = accion.history(period="max")
                if not hist.empty and len(hist) >= 14:
                    close_s = hist['Close']
                    p_ref = p_actual if p_actual is not None else close_s.iloc[-1]
                    
                    ath = close_s.max()
                    dist_ath = ((p_ref / ath) - 1) * 100 if ath else None
                    
                    if len(hist) >= 200:
                        sma200 = close_s.rolling(window=200).mean().iloc[-1]
                        dist_sma = ((p_ref / sma200) - 1) * 100 if sma200 else None
                    
                    delta = close_s.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    if loss.iloc[-1] != 0:
                        rsi_val = 100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1])))
                    else:
                        rsi_val = 100 if gain.iloc[-1] > 0 else 50

                    if rsi_val < 30: estado_rsi = "Oportunidad (Sobreventa)"
                    elif rsi_val > 70: estado_rsi = "Eufórico (Sobrecompra)"
            except Exception:
                pass  # Si falla el historial técnico, las variables quedan en None y el script no se rompe

            fila_tec = {
                "Ticker": ticker,
                "Distancia a Máx Histórico": dist_ath,
                "RSI (14 días)": rsi_val,
                "Estado RSI": estado_rsi,
                "Distancia a Media 200d": dist_sma
            }
            datos_tecnicos.append(fila_tec)

            # --- CAPTURA CAPA 3: TENDENCIAS TRIMESTRALES (AISLADO) ---
            icon_r, icon_e = '●', '●'
            try:
                df_q = accion.quarterly_financials
                if df_q is not None and not df_q.empty:
                    if not fechas_headers:
                        fechas_raw = df_q.columns[:5][::-1]
                        for idx_f, d in enumerate(fechas_raw):
                            fechas_headers.append(f"{nombres_base[idx_f]}<br><small>{d.strftime('%d/%m/%Y')}</small>")

                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, v in enumerate(rev_s):
                            if i < len(fechas_headers): fila_rev[fechas_headers[i]] = v
                        r_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) if len(rev_s) >= 2 else 0
                        icon_r = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if r_growth > 0.05 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if r_growth < -0.05 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_rev["Tendencia"] = icon_r
                        datos_revenue.append(fila_rev)
                    
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, v in enumerate(eps_s):
                            if i < len(fechas_headers): fila_eps[fechas_headers[i]] = v
                        e_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) if len(eps_s) >= 2 else 0
                        icon_e = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if e_growth > 0.05 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if e_growth < -0.05 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_eps["Tendencia"] = icon_e
                        datos_eps.append(fila_eps)
            except Exception:
                pass

            # Guardar siempre en el diccionario base para no alterar el TOP 5
            analisis_completo[ticker] = {
                "nombre": info.get('longName', ticker), "rev_t": icon_r, "eps_t": icon_e, 
                "net_margin": info.get('profitMargins', -1) if info.get('profitMargins') is not None else -1, 
                "upside_val": upside if upside else -1,
                "beta_val": beta if beta is not None else 99,
                "rsi_val": rsi_val,
                "dist_sma": dist_sma
            }

    def fmt_num(n, es_moneda=True):
        if pd.isna(n) or n == 0: return "-"
        p = "$" if (n >= 0 and es_moneda) else ""
        if n < 0 and es_moneda: p = "-$"
        num = abs(n)
        if num >= 1e12: return f"{p}{num/1e12:.2f}T"
