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
    "PER": ("0 - 10 (Bajo): indica que la acción está infravalorada o que el mercado tiene serias dudas sobre su futuro crecimiento. "
            "10 - 17 (Moderado): rango saludable y razonable para empresas establecidas. "
            "17 - 25 (Alto): acción sobrevalorada o que la empresa tiene buenas expectativas de crecimiento futuro que justifican pagar un precio mayor. "
            "Más de 25 (Muy alto): Típico de empresas de crecimiento agresivo. Los inversores pagan mucho hoy esperando beneficios gigantescos mañana."),
    "Margen Neto (%)": "Es la eficiencia operativa. Indica qué porcentaje de las ventas totales se convierte en ganancia limpia.",
    "ROE (%)": "Rentabilidad sobre el capital: mide qué tan bien la directiva multiplica el dinero de los accionistas.",
    "ROA (%)": "Rentabilidad sobre activos: indica la ganancia generada por cada dólar de recurso (propio o deuda) que posee la empresa.",
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

    with st.spinner('Sincronizando fundamentales e inyectando semáforo técnico...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                df_q = accion.quarterly_financials
                
                # --- VALUACIÓN Y BETA ---
                p_actual = info.get('currentPrice')
                v_justo = info.get('targetMeanPrice')
                beta = info.get('beta')
                upside = ((v_justo / p_actual) - 1) if p_actual and v_justo else None

                # --- CAPTURA DE DATOS TOTALES ---
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

                # --- CAPTURA: MÓDULO TÉCNICO ---
                hist = accion.history(period="max")
                dist_ath, rsi_val, dist_sma = None, None, None
                if not hist.empty and len(hist) >= 200:
                    close_s = hist['Close']
                    p_ref = p_actual if p_actual is not None else close_s.iloc[-1]
                    
                    ath = close_s.max()
                    dist_ath = ((p_ref / ath) - 1) * 100 if ath else None
                    
                    sma200 = close_s.rolling(window=200).mean().iloc[-1]
                    dist_sma = ((p_ref / sma200) - 1) * 100 if sma200 else None
                    
                    delta = close_s.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    if loss.iloc[-1] == 0:
                        rsi_val = 100 if gain.iloc[-1] > 0 else 50
                    else:
                        rsi_val = 100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1])))

                estado_rsi = "Neutral"
                if rsi_val:
                    if rsi_val < 30: estado_rsi = "Oportunidad (Sobreventa)"
                    elif rsi_val > 70: estado_rsi = "Eufórico (Sobrecompra)"

                fila_tec = {
                    "Ticker": ticker,
                    "Distancia a Máx Histórico": dist_ath,
                    "RSI (14 días)": rsi_val,
                    "Estado RSI": estado_rsi,
                    "Distancia a Media 200d": dist_sma
                }
                datos_tecnicos.append(fila_tec)

                # Pasamos los datos técnicos clave al diccionario de análisis completo para usarlos en el Racional de la sección 5
                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker), "rev_t": icon_r, "eps_t": icon_e, 
                    "net_margin": info.get('profitMargins', -1), 
                    "upside_val": upside if upside else -1,
                    "beta_val": beta if beta is not None else 99,
                    "rsi_val": rsi_val,
                    "dist_sma": dist_sma
                }
            except Exception: pass

    def fmt_num(n, es_moneda=True):
        if pd.isna(n) or n == 0: return "-"
        p = "$" if (n >= 0 and es_moneda) else ""
        if n < 0 and es_moneda: p = "-$"
        num = abs(n)
        if num >= 1e12: return f"{p}{num/1e12:.2f}T"
        if num >= 1e9: return f"{p}{num/1e9:.2f}B"
        return f"{p}{num/1e6:.2f}M" if num >= 1e6 else f"{p}{num:,.2f}"

    if datos_fundamentales:
        df_total = pd.DataFrame(datos_fundamentales).set_index("Ticker").T

        # --- 1. VALUACIÓN ---
        st.write("### 1. Valuación y Datos de Empresa")
        df_val = df_total.loc[["Empresa", "Precio", "Fair Value (Target)", "Upside (%)", "Beta (Volatilidad)", "Volumen Promedio"]]
        
        h1 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        h1 += '<tr style="background-color: #f0f2f6;"><th>Indicador</th>'
        for col in df_val.columns: h1 += f'<th>{col}</th>'
        h1 += '</tr>'
        for idx in df_val.index:
            h1 += f'<tr style="background-color: #f2f2f2;"><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_val.columns:
                val = df_val.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val): val_show = "-"
                elif idx == "Beta (Volatilidad)":
                    v_b = float(val)
                    if v_b <= 1: val_show = f"<span style='color:#28a745; font-size:1.5em;'><strong>⇠</strong></span><br><small>{v_b:.2f}</small>"
                    elif v_b <= 1.5: val_show = f"<span style='color:#ffc107; font-size:1.5em;'><strong>⇡</strong></span><br><small>{v_b:.2f}</small>"
                    else: val_show = f"<span style='color:#dc3545; font-size:1.5em;'><strong>⇢</strong></span><br><small>{v_b:.2f}</small>"
                elif idx == "Upside (%)":
                    v_n = float(val); val_show = f"{v_n*100:.2f}%"
                    if v_n > 0: style += 'background-color: #c8e6c9; color: #2e7d32; font-weight: bold;'
                elif idx == "Empresa": val_show = f"<b>{val}</b>"
                elif idx in ["Precio", "Fair Value (Target)"]: val_show = f"${float(val):,.2f}"
                elif idx == "Volumen Promedio": 
                    try: val_show = f"{float(val)/1e6:.2f}M"
                    except: val_show = "-"
                else: val_show = str(val)
                h1 += f'<td style="{style}">{val_show}</td>'
            h1 += '</tr>'
        st.write(h1 + '</table>', unsafe_allow_html=True)

        # --- 2. COMPARATIVA FUNDAMENTAL AVANZADA ---
        st.divider()
        st.write("### 2. Comparativa Fundamental Avanzada")
        df_fun = df_total.drop(["Precio", "Fair Value (Target)", "Upside (%)", "Beta (Volatilidad)", "Volumen Promedio"])
        f_ratios = df_fun.index.drop("Empresa")
        df_fun.loc[f_ratios, "PROMEDIO"] = df_fun.loc[f_ratios].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        h2 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        h2 += '<tr style="background-color: #f0f2f6;"><th>Indicador</th>'
        for col in df_fun.columns: h2 += f'<th>{col}</th>'
        h2 += '</tr>'
        for idx in df_fun.index:
            bg = "#f2f2f2" if idx == "Empresa" else "#ffffff"
            t_text = TOOLTIPS.get(idx, "")
            t_attr = f'title="{t_text}"' if t_text else ""
            c_style = "cursor: help;" if t_text else ""
            
            h2 += f'<tr style="background-color: {bg};">'
            h2 += f'<td {t_attr} style="font-weight:bold; border:1px solid #ddd; padding:8px; {c_style}">{idx}</td>'
            
            for col in df_fun.columns:
                val = df_fun.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val): val_show = "-"
                elif idx == "Empresa": val_show = f"<b>{val}</b>" if col != "PROMEDIO" else "-"
                else:
                    try:
                        v_n = float(val)
                        if col != "PROMEDIO":
                            posibles_puntos[col] += 1
                            prom = float(df_fun.loc[idx, "PROMEDIO"])
                            
                            if idx == "PER":
                                es_mejor = v_n > 10
                            elif idx in ["Debt/Equity", "Cost of Revenue"]:
                                es_mejor = v_n < prom
                            else:
                                es_mejor = v_n > prom
                                
                            if es_mejor:
                                style += 'background-color: #c8e6c9; font-weight: bold;'
                                ranking_puntos[col] += 1
                        
                        if "%" in idx: val_show = f"{v_n*100:.2f}%"
                        elif idx in ["Free Cash Flow", "Net Income", "Cost of Revenue"]: val_show = fmt_num(v_n, es_moneda=True)
                        else: val_show = f"{v_n:.2f}"
                    except: val_show = str(val)
                h2 += f'<td style="{style}">{val_show}</td>'
            h2 += '</tr>'
        st.write(h2 + '</table>', unsafe_allow_html=True)

        # --- 3. EVOLUCIÓN DE INGRESOS ---
        st.divider()
        if datos_revenue:
            st.write("### 3. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            cols_r = [c for c in df_r.columns if c != "Tendencia"] + ["Tendencia"]
            h3 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px
