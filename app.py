import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Terminal de Análisis Pro", layout="wide")

st.title("🚀 Terminal de Análisis Fundamental Pro")
st.write("Análisis Especializado: Valuación, Fundamentales y Selección Elite.")

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

    with st.spinner('Dividiendo métricas y calculando potenciales de subida...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                df_q = accion.quarterly_financials
                
                # --- CÁLCULO DE VALOR TÉCNICO ---
                precio_actual = info.get('currentPrice')
                valor_justo = info.get('targetMeanPrice')
                upside = ((valor_justo / precio_actual) - 1) if precio_actual and valor_justo else None

                # --- CAPTURA DE DATOS TOTALES ---
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

                # --- PROCESAMIENTO DE TENDENCIAS ---
                nombres_base = ["4 Trim. atrás", "3 Trim. atrás", "2 Trim. atrás", "1 Trim. atrás", "Último Trim."]
                icon_r, icon_e = '●', '●'
                if df_q is not None and not df_q.empty:
                    if not fechas_headers:
                        fechas_raw = df_q.columns[:5][::-1]
                        for i, d in enumerate(fechas_raw):
                            fechas_headers.append(f"{nombres_base[i]}<br><small>{d.strftime('%d/%m/%Y')}</small>")

                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, v in enumerate(rev_s):
                            if i < len(nombres_base): fila_rev[fechas_headers[i]] = v
                        icon_r = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) > 0.05 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) < -0.05 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_rev["Tendencia"] = icon_r
                        datos_revenue.append(fila_rev)
                    
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, v in enumerate(eps_s):
                            if i < len(nombres_base): fila_eps[fechas_headers[i]] = v
                        icon_e = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) > 0.05 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) < -0.05 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_eps["Tendencia"] = icon_e
                        datos_eps.append(fila_eps)

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker), "rev_t": icon_r, "eps_t": icon_e, 
                    "net_margin": info.get('profitMargins', -1), "upside_val": upside if upside else -1
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
        df_total = pd.DataFrame(datos_fundamentales).set_index("Ticker").T

        # --- TABLA 0: VALUACIÓN Y DATOS DE EMPRESA (NUEVA) ---
        st.write("### 1. Valuación y Datos de Empresa")
        df_val = df_total.loc[["Empresa", "Precio", "Fair Value (Target)", "Upside (%)"]]
        # No promediamos Precio ni Fair Value para evitar distorsiones
        df_val.loc[["Upside (%)"], "PROMEDIO"] = df_val.loc[["Upside (%)"]].apply(pd.to_numeric, errors='coerce').mean(axis=1)

        html_val = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        html_val += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Indicador</th>'
        for col in df_val.columns: html_val += f'<th style="padding:12px; border:1px solid #ddd;">{col}</th>'
        html_val += '</tr>'
        for idx in df_val.index:
            html_val += f'<tr style="background-color: #f2f2f2;"><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_val.columns:
                val = df_val.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val): val_show = "-"
                elif idx == "Upside (%)" and col != "PROMEDIO" and val > 0:
                    style += 'background-color: #c8e6c9; color: #2e7d32; font-weight: bold;'
                    val_show = f"{val*100:.2f}%"
                elif "%" in idx: val_show = f"{val*100:.2f}%" if pd.notnull(val) else "-"
                elif idx == "Empresa": val_show = f"<b>{val}</b>" if col != "PROMEDIO" else "-"
                elif idx in ["Precio", "Fair Value (Target)"]: 
                    val_show = f"${val:,.2f}" if col != "PROMEDIO" else "-"
                else: val_show = str(val)
                html_val += f'<td style="{style}">{val_show}</td>'
            html_val += '</tr>'
        st.write(html_val + '</table>', unsafe_allow_html=True)

        # --- TABLA 1: COMPARATIVA FUNDAMENTAL AVANZADA (SIN VALUACIÓN) ---
        st.divider()
        st.write("### 2. Comparativa Fundamental Avanzada")
        df_fun = df_total.drop(["Empresa", "Precio", "Fair Value (Target)", "Upside (%)"])
        df_fun.loc[:, "PROMEDIO"] = df_fun.apply(pd.to_numeric, errors='coerce').mean(axis=1)

        html_f = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        html_f += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Indicador</th>'
        for col in df_fun.columns: html_f += f'<th style="padding:12px; border:1px solid #ddd;">{col}</th>'
        html_f += '</tr>'
        for idx in df_fun.index:
            html_f += f'<tr><td style="font-weight:bold; background-color:#fafafa; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_fun.columns:
                val = df_fun.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val): val_show = "-"
                else:
                    try:
                        v_num = float(val)
                        if col != "PROMEDIO":
                            prom = float(df_fun.loc[idx, "PROMEDIO"])
                            posibles_puntos[col] += 1
                            es_mejor = (idx == "Debt/Equity" and v_num < prom) or (idx != "Debt/Equity" and v_num > prom)
                            if es_mejor:
                                style += 'background-color: #c8e6c9; font-weight: bold;'
                                ranking_puntos[col] += 1
                        if "%" in idx: val_show = f"{v_num*100:.2f}%"
                        elif idx == "Free Cash Flow": val_show = fmt_cur(v_num)
                        else: val_show = f"{v_num:.2f}"
                    except: val_show = str(val)
                html_f += f'<td style="{style}">{val_show}</td>'
            html_f += '</tr>'
        st.write(html_f + '</table>', unsafe_allow_html=True)

        # --- 2. REVENUE Y GRÁFICO ---
        st.divider()
        if datos_revenue:
            st.write("### 3. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            cols_r = [c for c in df_r.columns if c != "Tendencia"] + ["Tendencia"]
            h2 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
            h2 += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Ticker</th>'
            for c in cols_r: h2 += f'<th style="padding:12px; border:1px solid #ddd;">{c}</th>'
            h2 += '</tr>'
            for i in df_r.index:
                h2 += f'<tr><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{i}</td>'
                for c in cols_r:
                    v = df
