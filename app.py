import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Terminal de Análisis Pro", layout="wide")

st.title("🚀 Terminal de Inversión Inteligente")
st.write("Análisis Fundamental con Indicadores de Tendencia en Ingresos y Beneficios.")

# 2. ENTRADA DE TICKERS
tickers_raw = st.text_input("Tickers (separados por coma):", "CRM, GOOGL, IBM, INTU, META, MSFT, NFLX, NOW, ORCL, PLTR").upper()

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
    
    with st.spinner('Analizando tendencias de rentabilidad...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                
                # --- A. DATOS FUNDAMENTALES ---
                fila_fun = {
                    "Ticker": ticker, "Empresa": info.get('longName', 'N/A'),
                    "Precio": info.get('currentPrice'), "PER (P/E)": info.get('trailingPE'),
                    "EPS": info.get('trailingEps'), "ROE (%)": info.get('returnOnEquity'),
                    "ROA (%)": info.get('returnOnAssets'), "Debt/Equity": info.get('debtToEquity'),
                    "Current Ratio": info.get('currentRatio'), "Quick Ratio": info.get('quickRatio')
                }
                datos_fundamentales.append(fila_fun)

                # --- B. REVENUE Y EPS ---
                df_q = accion.quarterly_financials
                rev_growth, eps_growth = 0, 0
                nombres_trimestres = ["4 Trim. atrás", "3 Trim. atrás", "2 Trim. atrás", "1 Trim. atrás", "Último Trim."]
                
                if df_q is not None and not df_q.empty:
                    # Procesar Revenue (Tendencia)
                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, value in enumerate(rev_s):
                            if i < len(nombres_trimestres): fila_rev[nombres_trimestres[i]] = value
                        
                        if len(rev_s) >= 2:
                            rev_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) * 100
                        
                        if rev_growth > 5: fila_rev["Tendencia"] = "⬆️"
                        elif rev_growth < -5: fila_rev["Tendencia"] = "⬇️"
                        else: fila_rev["Tendencia"] = "🟡"
                        
                        fila_rev["TTM"] = info.get('totalRevenue')
                        datos_revenue.append(fila_rev)
                    
                    # Procesar EPS (Tendencia) - NUEVO REQUISITO
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, value in enumerate(eps_s):
                            if i < len(nombres_trimestres): fila_eps[nombres_trimestres[i]] = value
                        
                        if len(eps_s) >= 2:
                            # Usamos abs en el denominador para manejar casos donde el EPS inicial es negativo
                            denom = abs(eps_s.iloc[0]) if abs(eps_s.iloc[0]) > 0.01 else 0.01
                            eps_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / denom) * 100
                        
                        if eps_growth > 5: fila_eps["Tendencia"] = "⬆️"
                        elif eps_growth < -5: fila_eps["Tendencia"] = "⬇️"
                        else: fila_eps["Tendencia"] = "🟡"
                        
                        fila_eps["TTM"] = info.get('trailingEps')
                        datos_eps.append(fila_eps)

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker), "rev_growth": rev_growth, "eps_growth": eps_growth,
                    "ttm_rev": info.get('totalRevenue', 0), "ttm_eps": info.get('trailingEps', 0)
                }
            except Exception: pass

    # --- FUNCIONES DE FORMATEO ---
    def fmt_cur(n):
        if pd.isna(n) or n == 0: return "-"
        if n >= 1e12: return f"${n/1e12:.2f}T"
        if n >= 1e9: return f"${n/1e9:.2f}B"
        return f"${n/1e6:.2f}M" if n >= 1e6 else f"${n:,.2f}"

    def generar_html_unificado(df, tipo="normal"):
        html = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        html += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Ticker</th>'
        for col in df.columns: html += f'<th style="padding:12px; border:1px solid #ddd;">{col}</th>'
        html += '</tr>'
        for idx in df.index:
            html += '<tr>'
            html += f'<td style="font-weight:bold; background-color:#fafafa; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df.columns:
                val = df.loc[idx, col]
                if col == "Tendencia":
                    val_show = str(val)
                elif tipo == "moneda":
                    val_show = fmt_cur(val)
                elif tipo == "eps":
                    val_show = f"{val:.2f}" if pd.notna(val) else "-"
                else:
                    val_show = str(val) if pd.notna(val) else "-"
                html += f'<td style="border: 1px solid #ddd; padding: 8px;">{val_show}</td>'
            html += '</tr>'
        return html + '</table>'

    if datos_fundamentales:
        # 1. TABLA FUNDAMENTAL
        df_f = pd.DataFrame(datos_fundamentales).set_index("Ticker")
        df_f_final = df_f.T
        filas_num = df_f_final.index.drop("Empresa")
        df_f_final.loc[filas_num, "PROMEDIO"] = df_f_final.loc[filas_num].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        st.write("### 1. Comparativa Fundamental")
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
                if pd.isna(val) or val == "N/A": val_show = "-"
                else:
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
        st.write(html_f, unsafe_allow_html=True)

        # 2. REVENUE (Con Tendencia)
        st.divider()
        if datos_revenue:
            st.write("### 2. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            columnas_r = [c for c in df_r.columns if c not in ["TTM", "Tendencia"]] + ["TTM", "Tendencia"]
            df_r = df_r[columnas_r]
            st.write(generar_html_unificado(df_r, tipo="moneda"), unsafe_allow_html=True)
            
            st.write("#### 📈 Tendencia Trimestral de Ingresos")
            log_scale = st.checkbox("Usar Escala Logarítmica", value=False)
            df_plot_r = df_r.drop(columns=["TTM", "Tendencia"], errors='ignore').reset_index().melt(id_vars="Ticker")
            df_plot_r['value_b'] = df_plot_r['value'] / 1e9
            chart_r = alt.Chart(df_plot_r).mark_line(point=True).encode(
                x=alt.X('variable', sort=None, title='Periodo'),
                y=alt.Y('value_b', scale=alt.Scale(type='log' if log_scale else 'linear'), title='Revenue ($ Billions)'),
                color=alt.Color('Ticker', legend=alt.Legend(orient='right'))
            ).properties(height=400)
            st.altair_chart(chart_r, use_container_width=True)

        # 3. EPS (Con Tendencia) - AHORA CON FLECHAS
        if datos_eps:
            st.divider()
            st.write("### 3. Evolución de Beneficio por Acción (Basic EPS)")
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            # Ordenamos columnas para que Tendencia esté al final
            columnas_e = [c for c in df_e.columns if c not in ["TTM", "Tendencia"]] + ["TTM", "Tendencia"]
            df_e = df_e[columnas_e]
            
            st.write(generar_html_unificado(df_e, tipo="eps"), unsafe_allow_html=True)
            
            st.write("#### 📈 Tendencia Trimestral de EPS")
            df_plot_e = df_e.drop(columns=["TTM", "Tendencia"], errors='ignore').reset_index().melt(id_vars="Ticker")
            chart_e = alt.Chart(df_plot_e).mark_line(point=True).encode(
                x=alt.X('variable', sort=None, title='Periodo'),
                y=alt.Y('value', title='EPS ($)'),
                color=alt.Color('Ticker', legend=alt.Legend(orient='right'))
            ).properties(height=400)
            st.altair_chart(chart_e, use_container_width=True)

        # 4. RECOMENDACIÓN
        st.divider()
        st.write("### 🏆 4. Recomendación de Inversión (Top 3)")
        puntuacion_final = []
        for ticker, pts in ranking_puntos.items():
            c_extra = 0
            if ticker in analisis_completo:
                if analisis_completo[ticker]["rev_growth"] > 5: c_extra += 1
                if analisis_completo[ticker]["eps_growth"] > 5: c_extra += 1
            puntuacion_final.append({"ticker": ticker, "puntos_fun": pts, "score_total": pts + c_extra, "datos": analisis_completo.get(ticker, {})})

        top_3 = sorted(puntuacion_final, key=lambda x: x["score_total"], reverse=True)[:3]
        cols_rec = st.columns(3)
        for i, rec in enumerate(top_3):
            with cols_rec[i]:
                st.subheader(f"#{i+1} {rec['ticker']}")
                st.metric("Score Calidad", f"{rec['score_total']}/9")
                st.info(f"**{rec['ticker']}** es líder en rentabilidad y balance.")
else:
    st.info("Ingresa los tickers para iniciar el análisis.")
