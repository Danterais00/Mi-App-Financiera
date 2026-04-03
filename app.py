import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Terminal de Análisis Inteligente", layout="wide")

st.title("🚀 Terminal de Inversión: Selección y Recomendación")
st.write("Análisis profundo con auditoría de datos crudos en el ranking.")

tickers_input = st.text_input("Tickers (separados por coma):", "AAPL, MSFT, NVDA, GOOGL, AMZN, TSLA").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20]
    
    datos_fundamentales = []
    datos_revenue = []
    datos_eps = []
    analisis_completo = {}
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    
    with st.spinner('Procesando auditoría de datos...'):
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
                raw_rev = {}
                raw_eps = {}
                
                if df_q is not None and not df_q.empty:
                    # Revenue
                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        raw_rev = {d.strftime('%b %Y'): v for d, v in rev_s.items()}
                        datos_revenue.append({"Ticker": ticker, **raw_rev, "TTM": info.get('totalRevenue')})
                        if len(rev_s) >= 2: rev_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) * 100
                    
                    # EPS
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        raw_eps = {d.strftime('%b %Y'): v for d, v in eps_s.items()}
                        datos_eps.append({"Ticker": ticker, **raw_eps, "TTM": info.get('trailingEps')})
                        if len(eps_s) >= 2: eps_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) * 100 if abs(eps_s.iloc[0]) > 0.01 else 0

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker),
                    "rev_growth": rev_growth,
                    "eps_growth": eps_growth,
                    "fundamentales": fila_fun,
                    "raw_rev": raw_rev,
                    "raw_eps": raw_eps,
                    "ttm_rev": info.get('totalRevenue'),
                    "ttm_eps": info.get('trailingEps')
                }
            except Exception: pass

    if datos_fundamentales:
        # --- RENDER TABLA 1 ---
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
                else: val_show = f"<b>{val}</b>" if idx == "Empresa" else f"{val:.2f}" if isinstance(val, float) else val
                html_f += f'<td style="{style}">{val_show}</td>'
            html_f += '</tr>'
        html_f += '</table>'
        
        st.write("### 1. Comparativa Fundamental"); st.write(html_f, unsafe_allow_html=True)

        # --- TABLAS 2 Y 3 ---
        st.divider()
        if datos_revenue:
            st.write("### 2. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            st.table(df_r.map(lambda n: f"${n/1e9:.2f}B" if isinstance(n, (int, float)) and n >= 1e9 else f"${n/1e6:.2f}M" if isinstance(n, (int, float)) else n))
            st.line_chart(df_r.drop(columns=["TTM"], errors='ignore').T)
        
        if datos_eps:
            st.divider()
            st.write("### 3. Evolución de Basic EPS")
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            st.table(df_e.map(lambda n: f"{n:.2f}" if isinstance(n, (int, float)) else n))
            st.line_chart(df_e.drop(columns=["TTM"], errors='ignore').T)

        # --- 4. RECOMENDACIÓN Y RANKING EXPANDIDO ---
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
                st.info(f"**{rec['ticker']}** lidera con un crecimiento en ingresos del {rec['datos'].get('rev_growth',0):.1f}%.")

        # --- SECCIÓN DE AUDITORÍA (DATOS CRUDOS) ---
        with st.expander("🔍 Ver Ranking completo y Datos Crudos de Auditoría"):
            st.write("Aquí puedes ver toda la información utilizada para calcular los puntajes de cada empresa.")
            
            for item in sorted(puntuacion_final, key=lambda x: x["score_total"], reverse=True):
                ticker = item['ticker']
                datos = item['datos']
                
                st.markdown(f"#### {ticker} - {datos.get('nombre', '')}")
                st.write(f"**Puntaje Total:** {item['score_total']}/9 | **Fundamentales:** {item['puntos_fun']} | **Crecimiento:** {item['score_total'] - item['puntos_fun']}")
                st.progress(item['score_total'] / 9)
                
                # Columnas para organizar los datos crudos del ticker
                c1, c2, c3 = st.columns([1.5, 1, 1])
                
                with c1:
                    st.write("**Indicadores Fundamentales:**")
                    f_df = pd.DataFrame([datos['fundamentales']]).drop(columns=["Ticker", "Empresa"]).T
                    f_df.columns = ["Valor"]
                    st.dataframe(f_df, use_container_width=True)
                
                with c2:
                    st.write("**Histórico de Revenue (Raw):**")
                    rev_raw = datos['raw_rev'].copy()
                    rev_raw["TTM"] = datos['ttm_rev']
                    st.json(rev_raw)
                    st.write(f"📈 Crecimiento: **{datos['rev_growth']:.2f}%**")
                
                with c3:
                    st.write("**Histórico de EPS (Raw):**")
                    eps_raw = datos['raw_eps'].copy()
                    eps_raw["TTM"] = datos['ttm_eps']
                    st.json(eps_raw)
                    st.write(f"💎 Crecimiento: **{datos['eps_growth']:.2f}%**")
                
                st.write("---")
else:
    st.info("Ingresa los tickers para iniciar la auditoría completa.")
