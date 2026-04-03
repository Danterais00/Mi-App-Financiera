import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

st.set_page_config(page_title="Terminal de Análisis Pro", layout="wide")

st.title("🚀 Terminal de Inversión: Selección y Auditoría")
st.write("Análisis estandarizado con diseño visual unificado en todas las tablas.")

tickers_input = st.text_input("Tickers (separados por coma):", "CRM, GOOGL, IBM, INTU, META, MSFT, NFLX, NOW, ORCL, PLTR").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20]
    
    datos_fundamentales, datos_revenue, datos_eps = [], [], []
    analisis_completo = {}
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    
    with st.spinner('Unificando formatos y extrayendo datos...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                
                # --- 1. FUNDAMENTALES ---
                fila_fun = {
                    "Ticker": ticker, "Empresa": info.get('longName', 'N/A'),
                    "Precio": info.get('currentPrice'), "PER (P/E)": info.get('trailingPE'),
                    "EPS": info.get('trailingEps'), "ROE (%)": info.get('returnOnEquity'),
                    "ROA (%)": info.get('returnOnAssets'), "Debt/Equity": info.get('debtToEquity'),
                    "Current Ratio": info.get('currentRatio'), "Quick Ratio": info.get('quickRatio')
                }
                datos_fundamentales.append(fila_fun)

                # --- 2. REVENUE Y EPS (ESTANDARIZADOS) ---
                df_q = accion.quarterly_financials
                rev_growth, eps_growth = 0, 0
                nombres_trimestres = ["4 Trim. atrás", "3 Trim. atrás", "2 Trim. atrás", "1 Trim. atrás", "Último Trim."]
                
                if df_q is not None and not df_q.empty:
                    # Revenue
                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, value in enumerate(rev_s):
                            if i < len(nombres_trimestres): fila_rev[nombres_trimestres[i]] = value
                        fila_rev["TTM"] = info.get('totalRevenue')
                        datos_revenue.append(fila_rev)
                        if len(rev_s) >= 2: rev_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) * 100
                    
                    # EPS
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, value in enumerate(eps_s):
                            if i < len(nombres_trimestres): fila_eps[nombres_trimestres[i]] = value
                        fila_eps["TTM"] = info.get('trailingEps')
                        datos_eps.append(fila_eps)
                        if len(eps_s) >= 2: eps_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) * 100

                analisis_completo[ticker] = {"nombre": info.get('longName', ticker), "rev_growth": rev_growth, "eps_growth": eps_growth}
            except Exception: pass

    # --- FUNCIONES DE FORMATEO ---
    def fmt_cur(n):
        if not isinstance(n, (int, float)): return "-"
        if n >= 1e12: return f"${n/1e12:.2f}T"
        if n >= 1e9: return f"${n/1e9:.2f}B"
        return f"${n/1e6:.2f}M" if n >= 1e6 else f"${n:,.0f}"

    def fmt_val(n):
        return f"{n:.2f}" if isinstance(n, (int, float)) else "-"

    # --- FUNCIÓN PARA GENERAR TABLAS HTML CON FORMATO UNIFICADO ---
    def generar_html_unificado(df, tipo="normal"):
        html = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        # Encabezado Gris
        html += '<tr style="background-color: #f0f2f6;">'
        html += f'<th style="padding:12px; border:1px solid #ddd;">{df.index.name if df.index.name else "Indicador"}</th>'
        for col in df.columns:
            html += f'<th style="padding:12px; border:1px solid #ddd;">{col}</th>'
        html += '</tr>'
        # Filas
        for idx in df.index:
            html += '<tr>'
            # Primera columna Gris y Negrita
            html += f'<td style="font-weight:bold; background-color:#fafafa; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df.columns:
                val = df.loc[idx, col]
                val_show = fmt_cur(val) if tipo == "moneda" else fmt_val(val) if tipo == "eps" else str(val)
                html += f'<td style="border: 1px solid #ddd; padding: 8px;">{val_show}</td>'
            html += '</tr>'
        return html + '</table>'

    if datos_fundamentales:
        # --- TABLA 1 (FUNDAMENTALES - CON COLORES) ---
        df_f = pd.DataFrame(datos_fundamentales).set_index("Ticker")
        df_f_final = df_f.T
        filas_num = df_f_final.index.drop("Empresa")
        df_f_final.loc[filas_num, "PROMEDIO"] = df_f_final.loc[filas_num].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        html_f = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        html_f += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Indicador</th>'
        for col in df_f_final.columns: html_f += f'<th style="padding:12px; border:1px solid #ddd;">{col}</th>'
        html_f += '</tr>'
        for idx in df_f_final.index:
            html_f += '<tr>'
            html_f += f'<td style="font-weight:bold; background-color:#fafafa; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_f_final.columns:
                val = df_f_final.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if idx != "Empresa" and col != "PROMEDIO":
                    try:
                        v_num, prom = float(val), float(df_f_final.loc[idx, "PROMEDIO"])
                        es_mejor = (idx == "Debt/Equity" and v_num < prom) or (idx != "Debt/Equity" and v_num > prom)
                        if es_mejor:
                            style += 'background-color: #c8e6c9; font-weight: bold;'
                            ranking_puntos[col] += 1
                        val_show = f"{v_num*100:.2f}%" if "%" in idx else f"{v_num:.2f}"
                    except: val_show = "-"
                else:
                    if idx == "Empresa" and col == "PROMEDIO": val_show = "-"
                    else: val_show = f"<b>{val}</b>" if idx == "Empresa" else f"{val:.2f}" if isinstance(val, float) else val
                html_f += f'<td style="{style}">{val_show}</td>'
            html_f += '</tr>'
        html_f += '</table>'
        st.write("### 1. Comparativa Fundamental"); st.write(html_f, unsafe_allow_html=True)

        # --- TABLA 2 (REVENUE HTML) ---
        st.divider()
        if datos_revenue:
            st.write("### 2. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            st.write(generar_html_unificado(df_r, tipo="moneda"), unsafe_allow_html=True)
            
            # Gráfico Altair
            df_plot = df_r.drop(columns=["TTM"], errors='ignore').reset_index().melt(id_vars="Ticker")
            chart_r = alt.Chart(df_plot).mark_line(point=True).encode(
                x=alt.X('variable', sort=None, title='Periodo'),
                y=alt.Y('value', title='Revenue USD'),
                color=alt.Color('Ticker', legend=alt.Legend(orient='right'))
            ).properties(height=400)
            st.altair_chart(chart_r, use_container_width=True)
        
        # --- TABLA 3 (EPS HTML) ---
        if datos_eps:
            st.divider()
            st.write("### 3. Evolución de Basic EPS")
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            st.write(generar_html_unificado(df_e, tipo="eps"), unsafe_allow_html=True)
            
            # Gráfico Altair
            df_plot_e = df_e.drop(columns=["TTM"], errors='ignore').reset_index().melt(id_vars="Ticker")
            chart_e = alt.Chart(df_plot_e).mark_line(point=True).encode(
                x=alt.X('variable', sort=None, title='Periodo'),
                y=alt.Y('value', title='EPS USD'),
                color=alt.Color('Ticker', legend=alt.Legend(orient='right'))
            ).properties(height=400)
            st.altair_chart(chart_e, use_container_width=True)

        # --- 4. RECOMENDACIÓN ---
        st.divider()
        st.write("### 🏆 4. Recomendación de Inversión (Top 3)")
        puntuacion_final = []
        for ticker, pts in ranking_puntos.items():
            c_extra = 2 if (analisis_completo.get(ticker, {}).get("rev_growth", 0) > 0 and analisis_completo.get(ticker, {}).get("eps_growth", 0) > 0) else 0
            puntuacion_final.append({"ticker": ticker, "puntos_fun": pts, "score_total": pts + c_extra, "datos": analisis_completo.get(ticker, {})})

        top_3 = sorted(puntuacion_final, key=lambda x: x["score_total"], reverse=True)[:3]
        cols = st.columns(3)
        for i, rec in enumerate(top_3):
            with cols[i]:
                st.subheader(f"#{i+1} {rec['ticker']}")
                st.info(f"**Score:** {rec['score_total']}/9. Posee una tendencia de crecimiento sólida.")

        with st.expander("🔍 Ver Ranking completo y Auditoría"):
            for item in sorted(puntuacion_final, key=lambda x: x["score_total"], reverse=True):
                st.write(f"**{item['ticker']}**: {item['puntos_fun']}/7 Fundamentales | Ingresos: {item['datos'].get('rev_growth',0):.2f}%")
else:
    st.info("Ingresa los tickers para iniciar.")
