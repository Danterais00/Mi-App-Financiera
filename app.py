import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Terminal de Análisis Pro", layout="wide")

st.title("🚀 Terminal de Análisis Fundamental Pro")
st.write("Análisis Integral: Valor Justo, Tendencias Trimestrales y Selección Elite TOP 5.")

# 2. ENTRADA DE TICKERS
tickers_raw = st.text_input("Tickers (separados por coma):", "KO, COST, PEP, PG, WMT, AAPL, MSFT, NVDA").upper()

def corregir_ticker(t):
    t = t.strip()
    if t == "BRKB": return "BRK-B"
    if t == "BRKA": return "BRK-A"
    return t

if tickers_raw:
    lista_tickers = [corregir_ticker(t) for t in tickers_raw.split(",") if t.strip()][:20]
    
    datos_fundamentales, datos_revenue, datos_eps = [], [], []
    analisis_completo = {}
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    posibles_puntos = {ticker: 0 for ticker in lista_tickers}
    
    fechas_headers = []

    with st.spinner('Sincronizando balances, fechas y proyecciones de analistas...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                df_q = accion.quarterly_financials
                
                # --- CÁLCULO DE VALOR TÉCNICO (FAIR VALUE) ---
                precio_actual = info.get('currentPrice')
                valor_justo = info.get('targetMeanPrice')
                upside = ((valor_justo / precio_actual) - 1) if precio_actual and valor_justo else None

                # --- A. DATOS FUNDAMENTALES ---
                fila_fun = {
                    "Ticker": ticker, 
                    "Empresa": info.get('longName', 'N/A'),
                    "Precio": precio_actual, 
                    "Fair Value (Target)": valor_justo,
                    "Upside (%)": upside,
                    "PER": info.get('trailingPE'),
                    "Margen Neto (%)": info.get('profitMargins'),
                    "ROE (%)": info.get('returnOnEquity'), 
                    "ROA (%)": info.get('returnOnAssets'),
                    "Free Cash Flow": info.get('freeCashflow'),
                    "Div Yield (%)": info.get('dividendYield'),
                    "Debt/Equity": info.get('debtToEquity'), 
                    "Current Ratio": info.get('currentRatio'),
                    "Quick Ratio": info.get('quickRatio')
                }
                datos_fundamentales.append(fila_fun)

                # --- B. PROCESAMIENTO DE TENDENCIAS Y FECHAS ---
                nombres_base = ["4 Trim. atrás", "3 Trim. atrás", "2 Trim. atrás", "1 Trim. atrás", "Último Trim."]
                icon_r, icon_e = '●', '●'
                
                if df_q is not None and not df_q.empty:
                    if not fechas_headers:
                        fechas_raw = df_q.columns[:5][::-1]
                        for i, d in enumerate(fechas_raw):
                            fechas_headers.append(f"{nombres_base[i]}<br><small>{d.strftime('%d/%m/%Y')}</small>")

                    # Ingresos
                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, v in enumerate(rev_s):
                            if i < len(nombres_base): fila_rev[fechas_headers[i]] = v
                        r_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) * 100 if len(rev_s) >= 2 else 0
                        icon_r = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if r_growth > 5 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if r_growth < -5 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_rev["Tendencia"] = icon_r
                        datos_revenue.append(fila_rev)
                    
                    # EPS
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, v in enumerate(eps_s):
                            if i < len(nombres_base): fila_eps[fechas_headers[i]] = v
                        e_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) * 100 if len(eps_s) >= 2 else 0
                        icon_e = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if e_growth > 5 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if e_growth < -5 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_eps["Tendencia"] = icon_e
                        datos_eps.append(fila_eps)

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker), 
                    "rev_t": icon_r, "eps_t": icon_e, "net_margin": info.get('profitMargins', -1),
                    "upside_val": upside if upside else -1
                }
            except Exception: pass

    # --- FUNCIONES DE FORMATEO ---
    def fmt_cur(n):
        if pd.isna(n) or n == 0: return "-"
        p = "$" if n >= 0 else "-$"
        num = abs(n)
        if num >= 1e12: return f"{p}{num/1e12:.2f}T"
        if num >= 1e9: return f"{p}{num/1e9:.2f}B"
        return f"{p}{num/1e6:.2f}M" if num >= 1e6 else f"{p}{num:,.2f}"

    if datos_fundamentales:
        # --- 1. COMPARATIVA FUNDAMENTAL ---
        df_f = pd.DataFrame(datos_fundamentales).set_index("Ticker")
        df_f_final = df_f.T
        filas_num = df_f_final.index.drop(["Empresa"])
        df_f_final.loc[filas_num, "PROMEDIO"] = df_f_final.loc[filas_num].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        st.write("### 1. Comparativa Fundamental Avanzada")
        html_f = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        html_f += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Indicador</th>'
        for col in df_f_final.columns: html_f += f'<th style="padding:12px; border:1px solid #ddd;">{col}</th>'
        html_f += '</tr>'
        for idx in df_f_final.index:
            bg = "#f2f2f2" if idx in ["Empresa", "Precio", "Fair Value (Target)", "Upside (%)"] else "#ffffff"
            html_f += f'<tr style="background-color: {bg};"><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_f_final.columns:
                val = df_f_final.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val) or val == "N/A": val_show = "-"
                elif idx == "Precio" and col == "PROMEDIO": val_show = "-"
                else:
                    try:
                        v_num = float(val)
                        if idx not in ["Empresa", "Precio", "Fair Value (Target)", "Upside (%)"] and col != "PROMEDIO":
                            prom = float(df_f_final.loc[idx, "PROMEDIO"])
                            posibles_puntos[col] += 1
                            es_
