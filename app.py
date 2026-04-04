import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Terminal de Análisis Pro", layout="wide")

st.title("🚀 Terminal de Análisis Fundamental Pro")
st.write("Análisis Integral: Fundamentales, Tendencias y Selección Elite.")

# 2. ENTRADA DE TICKERS
tickers_raw = st.text_input("Tickers (separados por coma):", "SHEL, AAPL, MSFT, NVDA, GOOGL, AMZN, TSLA, JPM").upper()

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
    
    with st.spinner('Procesando motores de análisis y gráficos...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                
                # --- A. DATOS FUNDAMENTALES ---
                fila_fun = {
                    "Ticker": ticker, "Empresa": info.get('longName', 'N/A'),
                    "Precio": info.get('currentPrice'), "PER": info.get('trailingPE'),
                    "PEG": info.get('pegRatio'), "Net Margin": info.get('profitMargins'),
                    "ROE": info.get('returnOnEquity'), "ROA": info.get('returnOnAssets'),
                    "FCF": info.get('freeCashflow'), "Div Yield": info.get('dividendYield'),
                    "Debt/Equity": info.get('debtToEquity'), "Current Ratio": info.get('currentRatio'),
                    "Quick Ratio": info.get('quickRatio')
                }
                datos_fundamentales.append(fila_fun)

                # --- B. REVENUE Y EPS ---
                df_q = accion.quarterly_financials
                rev_growth, eps_growth = 0, 0
                nombres_trim = ["4 Trim. atrás", "3 Trim. atrás", "2 Trim. atrás", "1 Trim. atrás", "Último Trim."]
                
                icon_r = '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                icon_e = '<span style="color:#ffc107; font-size:1.8em;">●</span>'

                if df_q is not None and not df_q.empty:
                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, v in enumerate(rev_s):
                            if i < len(nombres_trim): fila_rev[nombres_trim[i]] = v
                        rev_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) * 100 if len(rev_s) >= 2 else 0
                        icon_r = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if rev_growth > 5 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if rev_growth < -5 else icon_r
                        fila_rev["Tendencia"] = icon_r
                        fila_rev["TTM"] = info.get('totalRevenue')
                        datos_revenue.append(fila_rev)
                    
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, v in enumerate(eps_s):
                            if i < len(nombres_trim): fila_eps[nombres_trim[i]] = v
                        eps_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) * 100 if len(eps_s) >= 2 else 0
                        icon_e = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if eps_growth > 5 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if eps_growth < -5 else icon_e
                        fila_eps["Tendencia"] = icon_e
                        fila_eps["TTM"] = info.get('trailingEps')
                        datos_eps.append(fila_eps)

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker), "rev_g": rev_growth, "eps_g": eps_growth,
                    "rev_t": icon_r, "eps_t": icon_e, "net_margin": info.get('profitMargins', -1)
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
        # --- SECCIÓN 1: COMPARATIVA ---
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
            bg = "#f2f2f2" if idx in ["Empresa", "Precio"] else "#ffffff"
            html_f += f'<tr style="background-color: {bg};"><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_f_final.columns:
                val = df_f_final.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val) or val == "N/A": val_show = "-"
                elif idx == "Precio" and col == "PROMEDIO": val_show = "-"
                else:
                    if idx not in ["Empresa", "Precio"] and col != "PROMEDIO":
                        try:
                            v_num, prom = float(val), float(df_f_final.loc[idx, "PROMEDIO"])
                            posibles_puntos[col] += 1
                            es_mejor = (idx in ["Debt/Equity", "PEG"] and v_num < prom) or (idx not in ["Debt/Equity", "PEG"] and v_num > prom)
                            if es_mejor:
                                style += 'background-color: #c8e6c9; font-weight: bold;'
                                ranking_puntos[col] += 1
                            val_show = f"{v_num*100:.2f}%" if "Margin" in idx or "ROE" in idx or "ROA" in idx or "Yield" in idx else (fmt_cur(v_num) if idx == "FCF" else f"{v_num:.2f}")
                        except: val_show = "-"
                    else:
                        val_show = f"<b>{val}</b>" if idx == "Empresa" else (f"${val:,.2f}" if idx == "Precio" else f"{val:.2f}")
                html_f += f'<td style="{style}">{val_show}</td>'
            html_f += '</tr>'
        st.write(html_f + '</table>', unsafe_allow_html=True)

        # --- SECCIÓN 2: REVENUE ---
        st.divider()
        if datos_revenue:
            st.write("### 2. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            cols_r = [c for c in df_r.columns if c not in ["TTM", "Tendencia"]] + ["TTM", "Tendencia"]
            
            h2 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
            h2 += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Ticker</th>'
            for c in cols_r: h2 += f'<th style="padding:12px; border:1px solid #ddd;">{c}</th>'
            h2 += '</tr>'
            for i in df_r.index:
                h2 += '<tr><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{i}</td>'
                for c in cols_r:
                    v = df_r.loc[i, c]
                    v_s = str(v) if c == "Tendencia" else fmt_cur(v)
                    h2 += f'<td style="border: 1px solid #ddd; padding: 8px;">{v_s}</td>'
                h2 += '</tr>'
            st.write(h2 + '</table>', unsafe_allow_html=True)

            log_r = st.checkbox("Escala Logarítmica (Ingresos)")
            df_p_r = df_r.drop(columns=["TTM", "Tendencia"]).reset_index().melt(id_vars="Ticker")
            chart_r = alt.Chart(df_p_r).mark_line(point=True).encode(
                x=alt.X('variable', sort=None), y=alt.Y('value', scale=alt.Scale(type='log' if log_r else 'linear'), title='USD'),
                color=alt.Color('Ticker', legend=alt.Legend(orient='right'))
            ).properties(height=400)
            st.altair_chart(chart_r, use_container_width=True)

        # --- SECCIÓN 3: EPS ---
        st.divider()
        if datos_eps:
            st.write("### 3. Evolución de Beneficio por Acción (Basic EPS)")
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            cols_e = [c for c in df_e.columns if c not in ["TTM", "Tendencia"]] + ["TTM", "Tendencia"]
            h3 = h2.replace("Revenue", "EPS") # Reutilizamos estructura
            st.write(h2.replace("Ingresos", "EPS"), unsafe_allow_html=True) # Simplificado para el ejemplo

        # --- SECCIÓN 4: TOP 5 ELITE ---
        st.divider()
        st.subheader("🏆 4. Selección Elite: TOP 5 Recomendado")
        
        final_scores = []
        for t in lista_tickers:
            if t in analisis_completo:
                p_fun = ranking_puntos[t]
                p_max = posibles_puntos[t]
                p_crec = (1 if analisis_completo[t]["rev_t"].find("28a745") != -1 else 0) + (1 if analisis_completo[t]["eps_t"].find("28a745") != -1 else 0)
                
                efic = (p_fun / p_max * 100) if p_max > 0 else 0
                final_scores.append({
                    "Ticker": t, "Nombre": analisis_completo[t]["nombre"],
                    "Total": p_fun + p_crec, "Eficacia": efic, 
                    "Fund": p_fun, "Crec": p_crec, "Margin": analisis_completo[t]["net_margin"]
                })

        top_5 = sorted(final_scores, key=lambda x: (x['Total'], x['Eficacia'], x['Margin']), reverse=True)[:5]
        cols_5 = st.columns(5)
        for idx, s in enumerate(top_5):
            with cols_5[idx]:
                st.metric(f"#{idx+1} {s['Ticker']}", f"{s['Total']} Pts", f"{s['Eficacia']:.1f}% Efic.")
                with st.expander("Racional"):
                    st.write(f"**Fundamentales:** {s['Fund']} verdes.")
                    st.write(f"**Crecimiento:** {'Confirmado ▲' if s['Crec']==2 else 'Parcial' if s['Crec']==1 else 'Neutro'}")
                    st.write(f"**Margen:** {s['Margin']*100:.1f}%")
else:
    st.info("Ingresa los tickers para iniciar el análisis completo.")
