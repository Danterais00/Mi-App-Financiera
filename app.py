import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Terminal de Análisis Pro", layout="wide")

st.title("🚀 Terminal de Análisis de Inversiones")
st.write("Análisis fundamental, tendencias de ingresos y ranking de selección.")

tickers_input = st.text_input("Tickers (separados por coma):", "AAPL, MSFT, NVDA, GOOGL").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20]
    
    datos_fundamentales = []
    datos_revenue = []
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    
    with st.spinner('Extrayendo estados financieros y métricas...'):
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

                # --- DATOS TABLA 2 (REVENUE CRONOLÓGICO) ---
                df_q = accion.quarterly_financials
                
                if df_q is not None and not df_q.empty and "Total Revenue" in df_q.index:
                    # Obtenemos los últimos 5 reportes
                    rev_series = df_q.loc["Total Revenue"].head(5)
                    
                    # --- EL TRUCO: Invertimos el orden (de antiguo a nuevo) ---
                    rev_series_cronologico = rev_series.iloc[::-1]
                    
                    fila_rev = {"Ticker": ticker}
                    for date, value in rev_series_cronologico.items():
                        fecha_str = date.strftime('%b %Y')
                        fila_rev[fecha_str] = value
                    
                    # TTM siempre al final
                    fila_rev["TTM (Anual)"] = info.get('totalRevenue', 'N/A')
                    datos_revenue.append(fila_rev)

            except Exception as e:
                st.warning(f"Error procesando {ticker}: {e}")

    if datos_fundamentales:
        # 1. RENDERIZAR TABLA 1
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
                        es_mejor = False
                        if idx == "Debt/Equity" and v_num < promedio: es_mejor = True
                        elif idx in ["PER (P/E)", "EPS", "ROE (%)", "ROA (%)", "Current Ratio", "Quick Ratio"] and v_num > promedio: es_mejor = True
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

        # 2. RENDERIZAR TABLA 2 (REVENUE CRONOLÓGICO)
        st.divider()
        st.write("### 2. Evolución de Ingresos (Total Revenue)")
        
        if datos_revenue:
            # Crear DataFrame. Las columnas aparecerán en el orden en que se metieron al dict.
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            
            def format_currency(n):
                if not isinstance(n, (int, float)): return "-"
                if n >= 1e12: return f"${n/1e12:.2f} T"
                if n >= 1e9: return f"${n/1e9:.2f} B"
                if n >= 1e6: return f"${n/1e6:.2f} M"
                return f"${n:,.0f}"

            df_r_styled = df_r.map(format_currency)
            st.table(df_r_styled)
        else:
            st.warning("No hay datos de ingresos disponibles.")

        # 3. RANKING
        st.divider()
        st.write("### 🏆 3. Resumen de Selección")
        ranking_ordenado = sorted(ranking_puntos.items(), key=lambda x: x[1], reverse=True)
        mejor = ranking_ordenado[0]
        st.success(f"La mejor opción es **{mejor[0]}** con **{mejor[1]}/7** puntos.")
        for ticker, pts in ranking_ordenado:
            st.write(f"- **{ticker}**: {pts} indicadores favorables")
            st.progress(pts / 7)
else:
    st.info("Ingresa tickers para comenzar.")
