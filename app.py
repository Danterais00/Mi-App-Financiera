import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Terminal de Análisis Pro", layout="wide")

st.title("🚀 Terminal de Análisis Fundamental Pro")
st.write("Análisis visual de tendencias con semáforo de rendimiento (Iconos Grandes).")

# 2. ENTRADA DE TICKERS
tickers_raw = st.text_input("Tickers (separados por coma):", "SHEL, AAPL, MSFT, NVDA, GOOGL, AMZN").upper()

def corregir_ticker(t):
    t = t.strip()
    if t == "BRKB": return "BRK-B"
    if t == "BRKA": return "BRK-A"
    return t

if tickers_raw:
    lista_tickers = [corregir_ticker(t) for t in tickers_raw.split(",")][:20]
    
    datos_fundamentales, datos_revenue, datos_eps = [], [], []
    analisis_completo = {}
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    
    with st.spinner('Agrandando iconos de tendencia y analizando métricas...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                
                # --- A. DATOS FUNDAMENTALES ---
                fila_fun = {
                    "Ticker": ticker, "Empresa": info.get('longName', 'N/A'),
                    "Precio": info.get('currentPrice'), "PER (P/E)": info.get('trailingPE'),
                    "PEG Ratio": info.get('pegRatio'), "Margen Neto (%)": info.get('profitMargins'),
                    "ROE (%)": info.get('returnOnEquity'), "ROA (%)": info.get('returnOnAssets'),
                    "Free Cash Flow": info.get('freeCashflow'), "Div. Yield (%)": info.get('dividendYield'),
                    "Debt/Equity": info.get('debtToEquity'), "Current Ratio": info.get('currentRatio'),
                    "Quick Ratio": info.get('quickRatio')
                }
                datos_fundamentales.append(fila_fun)

                # --- B. REVENUE Y EPS ---
                df_q = accion.quarterly_financials
                rev_growth, eps_growth = 0, 0
                nombres_trim = ["4 Trim. atrás", "3 Trim. atrás", "2 Trim. atrás", "1 Trim. atrás", "Último Trim."]
                
                if df_q is not None and not df_q.empty:
                    # Revenue
                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, v in enumerate(rev_s):
                            if i < len(nombres_trim): fila_rev[nombres_trim[i]] = v
                        rev_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) * 100 if len(rev_s) >= 2 else 0
                        
                        # Definición de iconos con HTML (font-size aumentado a 1.8em)
                        if rev_growth > 5: 
                            fila_rev["Tendencia"] = '<span style="color: #28a745; font-size: 1.8em;">▲</span>'
                        elif rev_growth < -5: 
                            fila_rev["Tendencia"] = '<span style="color: #dc3545; font-size: 1.8em;">▼</span>'
                        else: 
                            fila_rev["Tendencia"] = '<span style="color: #ffc107; font-size: 1.8em;">●</span>'
                        
                        fila_rev["TTM"] = info.get('totalRevenue')
                        datos_revenue.append(fila_rev)
                    
                    # EPS
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, v in enumerate(eps_s):
                            if i < len(nombres_trim): fila_eps[nombres_trim[i]] = v
                        eps_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) * 100 if len(eps_s) >= 2 else 0
                        
                        # Iconos grandes para EPS
                        if eps_growth > 5: 
                            fila_eps["Tendencia"] = '<span style="color: #28a745; font-size: 1.8em;">▲</span>'
                        elif eps_growth < -5: 
                            fila_eps["Tendencia"] = '<span style="color: #dc3545; font-size: 1.8em;">▼</span>'
                        else: 
                            fila_eps["Tendencia"] = '<span style="color: #ffc107; font-size: 1.8em;">●</span>'
                        
                        fila_eps["TTM"] = info.get('trailingEps')
                        datos_eps.append(fila_eps)

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker), 
                    "rev_g": rev_growth, "eps_g": eps_growth
                }
            except Exception: pass

    # --- FUNCIONES DE FORMATEO ---
    def fmt_cur(n):
        if pd.isna(n) or n == 0: return "-"
        prefix = "$" if n >= 0 else "-$"
        num = abs(n)
        if num >= 1e12: return f"{prefix}{num/1e12:.2f}T"
        if num >= 1e9: return f"{prefix}{num/1e9:.2f}B"
        if num >= 1e6: return f"{prefix}{num/1e6:.2f}M"
        return f"{prefix}{num:,.2f}"

    if datos_fundamentales:
        # --- 1. TABLA COMPARATIVA ---
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
            fila_bg = "#f2f2f2" if idx in ["Empresa", "Precio"] else "#ffffff"
            html_f += f'<tr style="background-color: {fila_bg};">'
            html_f += f'<td style="font-weight:bold; background-color:#fafafa; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_f_final.columns:
                val = df_f_final.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val) or val == "N/A": val_show = "-"
                elif idx == "Precio" and col == "PROMEDIO": val_show = "-"
                else:
                    if idx not in ["Empresa", "Precio"] and col != "PROMEDIO":
                        try:
                            v_num, prom = float(val), float(df_f_final.loc[idx, "PROMEDIO"])
                            es_mejor = (idx in ["Debt/Equity", "PEG Ratio"] and v_num < prom) or (idx not in ["Debt/Equity", "PEG Ratio"] and v_num > prom)
                            if es_mejor:
                                style += 'background-color: #c8e6c9; font-weight: bold;'
                                ranking_puntos[col] += 1
                            if "%" in idx: val_show = f"{v_num*100:.2f}%"
                            elif idx == "Free Cash Flow": val_show = fmt_cur(v_num)
                            else: val_show = f"{v_num:.2f}"
                        except: val_show = "-"
                    else:
                        if idx == "Empresa": val_show = f"<b>{val}</b>" if col != "PROMEDIO" else "-"
                        elif idx == "Precio": val_show = f"${val:,.2f}"
                        elif idx == "Free Cash Flow": val_show = fmt_cur(val)
                        else: val_show = f"{val*100:.2f}%" if "%" in idx else f"{val:.2f}"
                html_f += f'<td style="{style}">{val_show}</td>'
            html_f += '</tr>'
        st.write(html_f + '</table>', unsafe_allow_html=True)

        # --- 2. REVENUE Y GRÁFICO ---
        st.divider()
        if datos_revenue:
            st.write("### 2. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            cols_r = [c for c in df_r.columns if c not in ["TTM", "Tendencia"]] + ["TTM", "Tendencia"]
            
            # Generar Tabla HTML (usando write con unsafe_allow_html para renderizar iconos HTML)
            h2 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
            h2 += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Ticker</th>'
            for c in cols_r: h2 += f'<th style="padding:12px; border:1px solid #ddd;">{c}</th>'
            h2 += '</tr>'
            for i in df_r.index:
                h2 += '<tr>'
                h2 += f'<td style="font-weight:bold; background-color:#fafafa; border:1px solid #ddd; padding:8px;">{i}</td>'
                for c in cols_r:
                    v = df_r.loc[i, c]
                    # No formateamos la columna Tendencia (ya es HTML)
                    v_s = str(v) if c == "Tendencia" else fmt_cur(v)
                    h2 += f'<td style="border: 1px solid #ddd; padding: 8px;">{v_s}</td>'
                h2 += '</tr>'
            st.write(h2 + '</table>', unsafe_allow_html=True)
            
            st.write("#### 📈 Tendencia Trimestral de Ingresos")
            log_scale = st.checkbox("Usar Escala Logarítmica (Ingresos)", value=False)
            # Para el gráfico, eliminamos columnas HTML
            df_plot_r = df_r.drop(columns=["TTM", "Tendencia"]).reset_index().melt(id_vars="Ticker")
            df_plot_r['value_b'] = df_plot_r['value'] / 1e9
            chart_r = alt.Chart(df_plot_r).mark_line(point=True).encode(
                x=alt.X('variable', sort=None, title='Periodo'),
                y=alt.Y('value_b', scale=alt.Scale(type='log' if log_scale else 'linear'), title='Revenue ($ Billions)'),
                color=alt.Color('Ticker', legend=alt.Legend(orient='right'))
            ).properties(height=400)
            st.altair_chart(chart_r, use_container_width=True)

        # --- 3. EPS Y GRÁFICO ---
        st.divider()
        if datos_eps:
            st.write("### 3. Evolución de Beneficio por Acción (Basic EPS)")
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            cols_e = [c for c in df_e.columns if c not in ["TTM", "Tendencia"]] + ["TTM", "Tendencia"]
            
            h3 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
            h3 += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Ticker</th>'
            for c in cols_e: h3 += f'<th style="padding:12px; border:1px solid #ddd;">{c}</th>'
            h3 += '</tr>'
            for i in df_e.index:
                h3 += '<tr>'
                h3 += f'<td style="font-weight:bold; background-color:#fafafa; border:1px solid #ddd; padding:8px;">{i}</td>'
                for c in cols_e:
                    v = df_e.loc[i, c]
                    # No formateamos Tendencia, formateamos el resto a 2 decimales
                    v_s = str(v) if c == "Tendencia" else f"{v:.2f}" if pd.notna(v) else "-"
                    h3 += f'<td style="border: 1px solid #ddd; padding: 8px;">{v_s}</td>'
                h3 += '</tr>'
            st.write(h3 + '</table>', unsafe_allow_html=True)
            
            st.write("#### 📈 Tendencia Trimestral de EPS")
            df_plot_e = df_e.drop(columns=["TTM", "Tendencia"]).reset_index().melt(id_vars="Ticker")
            chart_e = alt.Chart(df_plot_e).mark_line(point=True).encode(
                x=alt.X('variable', sort=None, title='Periodo'),
                y=alt.Y('value', title='EPS ($)'),
                color=alt.Color('Ticker', legend=alt.Legend(orient='right'))
            ).properties(height=400)
            st.altair_chart(chart_e, use_container_width=True)

        # --- 4. RECOMENDACIÓN ---
        st.divider()
        st.write("### 🏆 4. Recomendación de Inversión (Top 3)")
        puntuacion_final = []
        for ticker, pts_fund in ranking_puntos.items():
            pts_crec = 0
            if ticker in analisis_completo:
                if analisis_completo[ticker]["rev_g"] > 5: pts_crec += 1
                if analisis_completo[ticker]["eps_g"] > 5: pts_crec += 1
            puntuacion_final.append({"ticker": ticker, "fundamentales": pts_fund, "crecimiento": pts_crec, "total": pts_fund + pts_crec})
        
        top_3 = sorted(puntuacion_final, key=lambda x: x["total"], reverse=True)[:3]
        cols_rec = st.columns(3)
        for i, rec in enumerate(top_3):
            with cols_rec[i]:
                st.subheader(f"#{i+1} {rec['ticker']}")
                st.write(f"**Fundamentales:** {rec['fundamentales']} 🟢 | **Crecimiento:** {rec['crecimiento']} 📈")
                st.metric("Score Final", f"{rec['total']}/11")
else:
    st.info("Ingresa los tickers para iniciar el análisis.")
