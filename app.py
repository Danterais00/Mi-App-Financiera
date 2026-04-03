import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Terminal de Análisis Inteligente", layout="wide")

st.title("🚀 Terminal de Inversión: Selección y Recomendación")
st.write("Análisis profundo con sistema de recomendación basado en algoritmos de calidad.")

tickers_input = st.text_input("Tickers (separados por coma):", "AAPL, MSFT, NVDA, GOOGL, AMZN, TSLA").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20]
    
    datos_fundamentales = []
    datos_revenue = []
    datos_eps = []
    analisis_completo = {}
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    
    with st.spinner('Ejecutando algoritmo de selección...'):
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

                # --- 2. REVENUE Y EPS ---
                df_q = accion.quarterly_financials
                rev_growth = 0
                eps_growth = 0
                
                if df_q is not None and not df_q.empty:
                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        datos_revenue.append({"Ticker": ticker, **{d.strftime('%b %Y'): v for d, v in rev_s.items()}, "TTM": info.get('totalRevenue')})
                        if len(rev_s) >= 2: rev_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) * 100
                    
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        datos_eps.append({"Ticker": ticker, **{d.strftime('%b %Y'): v for d, v in eps_s.items()}, "TTM": info.get('trailingEps')})
                        if len(eps_s) >= 2: eps_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) * 100 if abs(eps_s.iloc[0]) > 0.01 else 0

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker),
                    "rev_growth": rev_growth,
                    "eps_growth": eps_growth
                }
            except Exception: pass

    if datos_fundamentales:
        # --- PREPARACIÓN DE TABLA 1 ---
        df_f = pd.DataFrame(datos_fundamentales).set_index("Ticker")
        df_f_final = df_f.T
        filas_num = df_f_final.index.drop("Empresa")
        
        # Calculamos promedios solo para filas numéricas
        df_f_final.loc[filas_num, "PROMEDIO"] = df_f_final.loc[filas_num].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        # --- RENDER TABLA 1 (HTML CORREGIDO) ---
        html_f = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        
        # Encabezados
        html_f += '<tr style="background-color: #f0f2f6;">'
        html_f += '<th style="border: 1px solid #ddd; padding: 12px;">Indicador</th>'
        for col in df_f_final.columns: 
            html_f += f'<th style="border: 1px solid #ddd; padding: 12px;">{col}</th>'
        html_f += '</tr>'

        # Filas de datos
        for idx in df_f_final.index:
            html_f += '<tr>'
            html_f += f'<td style="font-weight: bold; background-color: #fafafa; border: 1px solid #ddd; padding: 8px;">{idx}</td>'
            
            promedio = df_f_final.loc[idx, "PROMEDIO"]
            
            for col in df_f_final.columns:
                val = df_f_final.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                
                if idx == "Empresa":
                    # Limpiamos el 'nan' del promedio en la fila Empresa
                    val_show = f"<b>{val}</b>" if col != "PROMEDIO" else "-"
                elif col == "PROMEDIO":
                    try:
                        v_num = float(val)
                        val_show = f"{v_num*100:.2f}%" if "%" in idx else f"{v_num:.2f}"
                    except: val_show = "-"
                else:
                    try:
                        v_num = float(val)
                        es_mejor = (idx == "Debt/Equity" and v_num < promedio) or (idx != "Debt/Equity" and v_num > promedio)
                        if es_mejor:
                            style += 'background-color: #c8e6c9; font-weight: bold;'
                            ranking_puntos[col] += 1
                        val_show = f"{v_num*100:.2f}%" if "%" in idx else f"{v_num:.2f}"
                    except: val_show = "-"
                
                html_f += f'<td style="{style}">{val_show}</td>'
            html_f += '</tr>'
        
        html_f += '</table>' # <--- Cierre de tabla FUERA de los bucles
        
        st.write("### 1. Comparativa Fundamental")
        st.write(html_f, unsafe_allow_html=True)

        # --- TABLAS 2 Y 3 (REVENUE Y EPS) ---
        st.divider()
        if datos_revenue:
            st.write("### 2. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            st.table(df_r.map(lambda n: f"${n/1e9:.2f}B" if isinstance(n, (int, float)) and n >= 1e9 else f"${n/1e6:.2f}M" if isinstance(n, (int, float)) else n))
            st.write("#### 📈 Tendencia Trimestral de Ingresos")
            st.line_chart(df_r.drop(columns=["TTM"], errors='ignore').T)
        
        if datos_eps:
            st.divider()
            st.write("### 3. Evolución de Basic EPS")
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            st.table(df_e.map(lambda n: f"{n:.2f}" if isinstance(n, (int, float)) else n))
            st.write("#### 📈 Tendencia Trimestral de EPS")
            st.line_chart(df_e.drop(columns=["TTM"], errors='ignore').T)

        # --- 4. RESUMEN Y RECOMENDACIÓN FINAL ---
        st.divider()
        st.write("### 🏆 4. Recomendación de Inversión (Top 3)")
        
        puntuacion_final = []
        for ticker, pts in ranking_puntos.items():
            crecimiento_extra = 0
            if ticker in analisis_completo:
                if analisis_completo[ticker]["rev_growth"] > 0: crecimiento_extra += 1
                if analisis_completo[ticker]["eps_growth"] > 0: crecimiento_extra += 1
            puntuacion_final.append({
                "ticker": ticker, "puntos_fun": pts, "score_total": pts + crecimiento_extra, "datos": analisis_completo.get(ticker, {})
            })

        top_3 = sorted(puntuacion_final, key=lambda x: x["score_total"], reverse=True)[:3]
        cols_rec = st.columns(3)
        for i, rec in enumerate(top_3):
            with cols_rec[i]:
                st.subheader(f"#{i+1} {rec['ticker']}")
                st.metric("Score Calidad", f"{rec['score_total']}/9")
                rev_g, eps_g = rec['datos'].get('rev_growth', 0), rec['datos'].get('eps_growth', 0)
                just = f"**{rec['ticker']}** lidera el grupo con {rec['puntos_fun']} fortalezas fundamentales. "
                if rev_g > 0: just += f"Ventas subiendo un {rev_g:.1f}% "
                if eps_g > 0: just += f"y una rentabilidad (EPS) que se expandió un {eps_g:.1f}%."
                st.info(just)

        with st.expander("Ver ranking completo"):
            for item in sorted(puntuacion_final, key=lambda x: x["score_total"], reverse=True):
                st.write(f"**{item['ticker']}**: {item['score_total']} pts totales")
                st.progress(min(item['score_total'] / 9, 1.0))
else:
    st.info("Ingresa los tickers para iniciar.")
