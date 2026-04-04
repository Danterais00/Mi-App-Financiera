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

    with st.spinner('Sincronizando datos y regenerando el TOP 5 Elite...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                df_q = accion.quarterly_financials
                
                # --- CÁLCULO DE VALOR TÉCNICO ---
                p_actual = info.get('currentPrice')
                v_justo = info.get('targetMeanPrice')
                upside = ((v_justo / p_actual) - 1) if p_actual and v_justo else None

                # --- CAPTURA DE DATOS TOTALES ---
                fila_fun = {
                    "Ticker": ticker, 
                    "Empresa": info.get('longName', 'N/A'),
                    "Precio": p_actual, 
                    "Fair Value (Target)": v_justo,
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
                        for idx_f, d in enumerate(fechas_raw):
                            fechas_headers.append(f"{nombres_base[idx_f]}<br><small>{d.strftime('%d/%m/%Y')}</small>")

                    # Ingresos
                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for idx_r, val_r in enumerate(rev_s):
                            if idx_r < len(fechas_headers): fila_rev[fechas_headers[idx_r]] = val_r
                        crec_r = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) if len(rev_s) >= 2 else 0
                        icon_r = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if crec_r > 0.05 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if crec_r < -0.05 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_rev["Tendencia"] = icon_r
                        datos_revenue.append(fila_rev)
                    
                    # EPS
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for idx_e, val_e in enumerate(eps_s):
                            if idx_e < len(fechas_headers): fila_eps[fechas_headers[idx_e]] = val_e
                        crec_e = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) if len(eps_s) >= 2 else 0
                        icon_e = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if crec_e > 0.05 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if crec_e < -0.05 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_eps["Tendencia"] = icon_e
                        datos_eps.append(fila_eps)

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker), 
                    "rev_t": icon_r, "eps_t": icon_e, 
                    "net_margin": info.get('profitMargins', -1), 
                    "upside_val": upside if upside else -1
                }
            except Exception: pass

    def fmt_cur(n):
        if pd.isna(n) or n == 0: return "-"
        p = "$" if n >= 0 else "-$"
        num = abs(n)
        if num >= 1e12: return f"{p}{num/1e12:.2f}T"
        if num >= 1e9: return f"{p}{num/1e9:.2f}B"
        return f"{p}{num/1e6:.2f}M" if num >= 1e6 else f"{p}{num:,.2f}"

    if datos_fundamentales:
        df_total = pd.DataFrame(datos_fundamentales).set_index("Ticker").T

        # --- 1. VALUACIÓN Y DATOS DE EMPRESA ---
        st.write("### 1. Valuación y Datos de Empresa")
        df_val = df_total.loc[["Empresa", "Precio", "Fair Value (Target)", "Upside (%)"]]
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
                else:
                    if idx == "Upside (%)":
                        val_show = f"{float(val)*100:.2f}%"
                        if col != "PROMEDIO" and float(val) > 0:
                            style += 'background-color: #c8e6c9; color: #2e7d32; font-weight: bold;'
                    elif idx == "Empresa": val_show = f"<b>{val}</b>" if col != "PROMEDIO" else "-"
                    elif idx in ["Precio", "Fair Value (Target)"]: 
                        val_show = f"${float(val):,.2f}" if col != "PROMEDIO" else "-"
                    else: val_show = str(val)
                html_val += f'<td style="{style}">{val_show}</td>'
            html_val += '</tr>'
        st.write(html_val + '</table>', unsafe_allow_html=True)

        # --- 2. COMPARATIVA FUNDAMENTAL AVANZADA ---
        st.divider()
        st.write("### 2. Comparativa Fundamental Avanzada")
        df_fun = df_total.drop(["Precio", "Fair Value (Target)", "Upside (%)"])
        filas_ratios = df_fun.index.drop("Empresa")
        df_fun.loc[filas_ratios, "PROMEDIO"] = df_fun.loc[filas_ratios].apply(pd.to_numeric, errors='coerce').mean(axis=1)

        html_f = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        html_f += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Indicador</th>'
        for col in df_fun.columns: html_f += f'<th style="padding:12px; border:1px solid #ddd;">{col}</th>'
        html_f += '</tr>'
        for idx in df_fun.index:
            bg_f = "#f2f2f2" if idx == "Empresa" else "#ffffff"
            html_f += f'<tr style="background-color: {bg_f};"><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_fun.columns:
                val = df_fun.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val): val_show = "-"
                else:
                    if idx == "Empresa":
                        val_show = f"<b>{val}</b>" if col != "PROMEDIO" else "-"
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

        # --- 3. EVOLUCIÓN DE INGRESOS ---
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
                    val_c = df_r.loc[i, c]
                    v_s = str(val_c) if c == "Tendencia" else fmt_cur(val_cell := val_c)
                    h2 += f'<td style="border: 1px solid #ddd; padding: 8px;">{v_s}</td>'
                h2 += '</tr>'
            st.write(h2 + '</table>', unsafe_allow_html=True)
            df_p_r = df_r.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
            df_p_r['value_b'] = df_p_r['value'] / 1e9; df_p_r['periodo'] = df_p_r['variable'].str.split('<').str[0]
            st.altair_chart(alt.Chart(df_p_r).mark_line(point=True).encode(x=alt.X('periodo', sort=None), y=alt.Y('value_b', title='Billions ($)'), color='Ticker').properties(height=300), use_container_width=True)

        # --- 4. EVOLUCIÓN DE EPS ---
        st.divider()
        if datos_eps:
            st.write("### 4. Evolución de Beneficio por Acción (Basic EPS)")
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            cols_e = [c for c in df_e.columns if c != "Tendencia"] + ["Tendencia"]
            h3 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
            h3 += '<tr style="background-color: #f0f2f6;"><th style="padding:12px; border:1px solid #ddd;">Ticker</th>'
            for c in cols_e: h3 += f'<th style="padding:12px; border:1px solid #ddd;">{c}</th>'
            h3 += '</tr>'
            for i in df_e.index:
                h3 += f'<tr><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{i}</td>'
                for c in cols_e:
                    val_c = df_e.loc[i, c]
                    v_s = str(val_c) if c == "Tendencia" else f"{val_c:.2f}" if pd.notna(val_c) else "-"
                    h3 += f'<td style="border: 1px solid #ddd; padding: 8px;">{v_s}</td>'
                h3 += '</tr>'
            st.write(h3 + '</table>', unsafe_allow_html=True)
            df_p_e = df_e.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker"); df_p_e['periodo'] = df_p_e['variable'].str.split('<').str[0]
            st.altair_chart(alt.Chart(df_p_e).mark_line(point=True).encode(x=alt.X('periodo', sort=None), y=alt.Y('value', title='EPS ($)'), color='Ticker').properties(height=300), use_container_width=True)

        # --- 5. TOP 5 ELITE (INFORMACIÓN DETALLADA RESTAURADA) ---
        st.divider()
        st.write("### 🏆 5. Selección Elite: TOP 5 Recomendado")
        final_scores = []
        for t in lista_tickers:
            if t in analisis_completo:
                p_fun = ranking_puntos[t]
                p_max = posibles_puntos[t]
                p_crec = (1 if "28a745" in analisis_completo[t]["rev_t"] else 0) + (1 if "28a745" in analisis_completo[t]["eps_t"] else 0)
                p_up = 1 if analisis_completo[t]["upside_val"] > 0 else 0
                efic = (p_fun / p_max * 100) if p_max > 0 else 0
                final_scores.append({
                    "Ticker": t, 
                    "Nombre": analisis_completo[t]["nombre"], 
                    "Total": p_fun + p_crec + p_up, 
                    "Eficacia": efic, 
                    "Fund": p_fun, 
                    "Crec": p_crec, 
                    "Up": p_up, 
                    "Margin": analisis_completo[t]["net_margin"]
                })

        top_5 = sorted(final_scores, key=lambda x: (x['Total'], x['Eficacia'], x['Margin']), reverse=True)[:5]
        cols_5 = st.columns(5)
        for idx, s in enumerate(top_5):
            with cols_5[idx]:
                st.markdown(f"Puesto #{idx+1}")
                st.markdown(f"<h1 style='text-align: left; color: #1E1E1E; margin-top: -20px; padding-bottom: 0px;'><b>{s['Ticker']}</b></h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size: 1.2em; color: #555;'>{s['Total']} Puntos</p>", unsafe_allow_html=True)
                st.caption(f"{s['Eficacia']:.1f}% Eficacia Relativa")
                
                # --- RACIONAL DETALLADO ---
                with st.expander("Ver Racional"):
                    st.write(f"**Fundamentales:**")
                    st.write(f"Posee **{s['Fund']}** indicadores superiores al promedio del grupo (celdas verdes en la tabla fundamental).")
                    
                    st.write(f"**Crecimiento:**")
                    if s['Crec'] == 2:
                        st.write("Crecimiento dual confirmado: Ingresos y EPS al alza (▲).")
                    elif s['Crec'] == 1:
                        st.write("Crecimiento parcial detectado en ingresos o beneficios.")
                    else:
                        st.write("Tendencia de crecimiento neutra o en consolidación.")
                    
                    if s['Up'] > 0:
                        st.success("Potencial de Revalorización: Acción subvaluada respecto al Fair Value.")
                    
                    st.write(f"**Eficiencia:**")
                    st.write(f"Margen Neto: **{s['Margin']*100:.2f}%**")
else:
    st.info("Ingresa los tickers para iniciar el análisis.")
