import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Terminal de Análisis Pro", layout="wide")

st.title("🚀 Terminal de Análisis de Inversiones")
st.write("Análisis integral: Fundamentales, Ingresos, EPS y Selección Inteligente.")

tickers_input = st.text_input("Tickers (separados por coma):", "AAPL, MSFT, NVDA, GOOGL").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20]
    
    datos_fundamentales = []
    datos_revenue = []
    datos_eps = []
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    
    with st.spinner('Procesando estados financieros y calculando tendencias...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                
                # --- DATOS TABLA 1 (FUNDAMENTALES) ---
                fila_fun = {
                    "Ticker": ticker,
                    "Empresa": info.get('longName', 'N/A'),
                    "Precio": info.get('currentPrice'),
                    "PER (P/E)": info.get('trailingPE'),
                    "EPS": info.get('trailingEps'),
                    "ROE (%)": info.get('returnOnEquity'),
                    "ROA (%)": info.get('returnOnAssets'),
                    "Debt/Equity": info.get('debtToEquity'),
                    "Current Ratio": info.get('currentRatio'),
                    "Quick Ratio": info.get('quickRatio')
                }
                datos_fundamentales.append(fila_fun)

                # --- DATOS TABLA 2 (REVENUE) Y TABLA 3 (EPS) ---
                df_q = accion.quarterly_financials
                if df_q is not None and not df_q.empty:
                    # Revenue
                    if "Total Revenue" in df_q.index:
                        rev_series = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for date, value in rev_series.items():
                            fila_rev[date.strftime('%b %Y')] = value
                        fila_rev["TTM (Anual)"] = info.get('totalRevenue', 'N/A')
                        datos_revenue.append(fila_rev)
                    
                    # Basic EPS
                    et_eps = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_eps:
                        eps_series = df_q.loc[et_eps].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for date, value in eps_series.items():
                            fila_eps[date.strftime('%b %Y')] = value
                        fila_eps["TTM (Anual)"] = info.get('trailingEps', 'N/A')
                        datos_eps.append(fila_eps)

            except Exception as e:
                st.warning(f"Error procesando {ticker}: {e}")

    if datos_fundamentales:
        # 1. TABLA FUNDAMENTALES
        df_f = pd.DataFrame(datos_fundamentales).set_index("Ticker")
        df_f_final = df_f.T
        filas_num = df_f_final.index.drop("Empresa")
        df_f_final.loc[filas_num, "PROMEDIO"] = df_f_final.loc[filas_num].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        html_f = '<table style="width:100%; border-collapse: collapse; text-align: center;">'
        html_f += '<tr style="background-color: #f0f2f6;"><th>Indicador</th>'
        for col in df_f_final.columns: html_f += f'<th>{col}</th>'
        html_f += '</tr>'
        for idx in df_f_final.index:
            html_f += '<tr>'
            html_f += f'<td style="font-weight: bold; background-color: #fafafa; border: 1px solid #ddd; padding: 8px;">{idx}</td>'
            promedio = df_f_final.loc[idx, "PROMEDIO"]
            for col in df_f_final.columns:
                val = df_f_final.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if idx != "Empresa" and col != "PROMEDIO":
                    try:
                        v_num = float(val)
                        es_mejor = (idx == "Debt/Equity" and v_num < promedio) or \
                                   (idx in ["PER (P/E)", "EPS", "ROE (%)", "ROA (%)", "Current Ratio", "Quick Ratio"] and v_num > promedio)
                        if es_mejor:
                            style += 'background-color: #c8e6c9; font-weight: bold;'
                            ranking_puntos[col] += 1
                        val_show = f"{v_num*100:.2f}%" if "%" in idx else f"{v_num:.2f}"
                    except: val_show = "-"
                else:
                    val_show = f"<b>{val}</b>" if idx == "Empresa" else f"{val:.2f}" if isinstance(val, float) else val
                html_f += f'<td style="{style}">{val_show}</td>'
            html_f += '</tr>'
        html_f += '</table>'
        st.write("### 1. Tabla Comparativa de Fundamentales")
        st.write(html_f, unsafe_allow_html=True)

        # 2. EVOLUCIÓN DE INGRESOS (REVENUE)
        st.divider()
        st.write("### 2. Evolución de Ingresos (Total Revenue)")
        if datos_revenue:
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            def fmt_cur(n):
                if not isinstance(n, (int, float)): return "-"
                if n >= 1e12: return f"${n/1e12:.2f} T"; 
                if n >= 1e9: return f"${n/1e9:.2f} B"; 
                return f"${n/1e6:.2f} M" if n >= 1e6 else f"${n:,.0f}"
            st.table(df_r.map(fmt_cur))
            st.write("#### 📈 Tendencia Trimestral de Ingresos")
            st.line_chart(df_r.drop(columns=["TTM (Anual)"], errors='ignore').T)

        # 3. EVOLUCIÓN DE BASIC EPS
        st.divider()
        st.write("### 3. Evolución de Beneficio por Acción (Basic EPS)")
        if datos_eps:
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            st.table(df_e.map(lambda n: f"{n:.2f}" if isinstance(n, (int, float)) else "-"))
            st.write("#### 📈 Tendencia Trimestral de EPS")
            st.line_chart(df_e.drop(columns=["TTM (Anual)"], errors='ignore').T)

        # 4. RANKING Y RESUMEN FINAL
        st.divider()
        st.write("### 🏆 4. Resumen de Selección")
        ranking_ord = sorted(ranking_puntos.items(), key=lambda x: x[1], reverse=True)
        st.success(f"La mejor opción es **{ranking_ord[0][0]}** con **{ranking_ord[0][1]}/7** puntos.")

        for ticker, pts in ranking_ord:
            st.write(f"#### {ticker}")
            st.write(f"Indicadores favorables: **{pts} de 7**")
            st.progress(pts / 7)
            
            # --- COMENTARIOS DE REVENUE ---
            if datos_revenue:
                df_rev_check = pd.DataFrame(datos_revenue).set_index("Ticker")
                if ticker in df_rev_check.index:
                    vals = [i for i in df_rev_check.loc[ticker].drop("TTM (Anual)", errors='ignore').values if isinstance(i, (int, float))]
                    if len(vals) >= 2:
                        crec = ((vals[-1] - vals[0]) / abs(vals[0])) * 100
                        txt = f"💰 **Ingresos:** {'✅ Crece' if crec > 5 else '⚠️ Cae' if crec < -5 else '➡️ Estable'} ({crec:.1f}% en 5Q)."
                        st.info(txt)
            
            # --- COMENTARIOS DE EPS ---
            if datos_eps:
                df_eps_check = pd.DataFrame(datos_eps).set_index("Ticker")
                if ticker in df_eps_check.index:
                    vals_e = [i for i in df_eps_check.loc[ticker].drop("TTM (Anual)", errors='ignore').values if isinstance(i, (int, float))]
                    if len(vals_e) >= 2:
                        e_ini, e_fin = vals_e[0], vals_e[-1]
                        # Evitar división por cero si el EPS inicial es muy cercano a 0
                        crec_e = ((e_fin - e_ini) / abs(e_ini)) * 100 if abs(e_ini) > 0.01 else 0
                        
                        if e_ini < 0 and e_fin > 0:
                            msg = "🚀 **EPS (Beneficio):** ¡Turnaround! La empresa pasó de pérdidas a ganancias."
                        elif crec_e > 5:
                            msg = f"💎 **EPS (Beneficio):** En expansión (+{crec_e:.1f}%). La rentabilidad está subiendo."
                        elif crec_e < -5:
                            msg = f"📉 **EPS (Beneficio):** En declive ({crec_e:.1f}%). Los márgenes podrían estar sufriendo."
                        else:
                            msg = "⚖️ **EPS (Beneficio):** Sin variaciones significativas."
                        st.info(msg)
            st.write("---")
else:
    st.info("Ingresa los tickers para iniciar el análisis.")
