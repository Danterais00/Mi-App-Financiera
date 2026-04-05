import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Terminal Pro: Multi-Estrategia", layout="wide")

# --- BARRA LATERAL (ESTRATEGIA) ---
st.sidebar.title("⚙️ Configuración")
modo_estrategia = st.sidebar.radio(
    "Selecciona tu Estrategia:",
    ["Crecimiento (Agresivo)", "Fortaleza (Defensivo)"],
    help="Agresivo: Premia el impulso y aceleración. Defensivo: Premia el balance y la subvaluación."
)

st.title("🚀 Terminal de Análisis Fundamental Pro")
st.write(f"Modo Activo: **{modo_estrategia}**")

# 2. ENTRADA DE TICKERS
tickers_raw = st.text_input("Tickers (separados por coma):", "KO, COST, PEP, PG, WMT, AAPL, MSFT, NVDA, JNJ, LLY").upper()

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

    with st.spinner('Sincronizando datos y aplicando filtros de estrategia...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                df_q = accion.quarterly_financials
                
                # --- VALUACIÓN ---
                p_actual = info.get('currentPrice')
                v_justo = info.get('targetMeanPrice')
                upside = ((v_justo / p_actual) - 1) if p_actual and v_justo else None

                # --- CAPTURA TOTAL ---
                fila_fun = {
                    "Ticker": ticker, "Empresa": info.get('longName', 'N/A'),
                    "Precio": p_actual, "Fair Value (Target)": v_justo, "Upside (%)": upside,
                    "PER": info.get('trailingPE'), "Margen Neto (%)": info.get('profitMargins'),
                    "ROE (%)": info.get('returnOnEquity'), "ROA (%)": info.get('returnOnAssets'),
                    "Free Cash Flow": info.get('freeCashflow'), "Div Yield (%)": info.get('dividendYield'),
                    "Debt/Equity": info.get('debtToEquity'), "Current Ratio": info.get('currentRatio'),
                    "Quick Ratio": info.get('quickRatio')
                }
                datos_fundamentales.append(fila_fun)

                # --- TENDENCIAS ---
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
                        for i, v in enumerate(rev_s):
                            if i < len(fechas_headers): fila_rev[fechas_headers[i]] = v
                        r_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) if len(rev_s) >= 2 else 0
                        icon_r = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if r_growth > 0.05 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if r_growth < -0.05 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_rev["Tendencia"] = icon_r # FIX: Agregado a la fila
                        datos_revenue.append(fila_rev)
                    
                    # EPS
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, v in enumerate(eps_s):
                            if i < len(fechas_headers): fila_eps[fechas_headers[i]] = v
                        e_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) if len(eps_s) >= 2 else 0
                        icon_e = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if e_growth > 0.05 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if e_growth < -0.05 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_eps["Tendencia"] = icon_e # FIX: Agregado a la fila
                        datos_eps.append(fila_eps)

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker), "rev_t": icon_r, "eps_t": icon_e, 
                    "net_margin": info.get('profitMargins', -1), "upside_val": upside if upside else -1
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

        # --- 1. VALUACIÓN (SIN PROMEDIO) ---
        st.write("### 1. Valuación y Datos de Empresa")
        df_val = df_total.loc[["Empresa", "Precio", "Fair Value (Target)", "Upside (%)"]]
        html_val = '<table style="width:100%; border-collapse: collapse; text-align: center;">'
        html_val += '<tr style="background-color: #f0f2f6;"><th>Indicador</th>'
        for col in df_val.columns: html_val += f'<th>{col}</th>'
        html_val += '</tr>'
        for idx in df_val.index:
            html_val += '<tr style="background-color: #f2f2f2;">'
            html_val += f'<td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_val.columns:
                val = df_val.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val): val_show = "-"
                elif idx == "Upside (%)":
                    v_n = float(val); val_show = f"{v_n*100:.2f}%"
                    if v_n > 0: style += 'background-color: #c8e6c9; color: #2e7d32; font-weight: bold;'
                elif idx == "Empresa": val_show = f"<b>{val}</b>"
                elif idx in ["Precio", "Fair Value (Target)"]: val_show = f"${float(val):,.2f}"
                else: val_show = str(val)
                html_val += f'<td style="{style}">{val_show}</td>'
            html_val += '</tr>'
        st.write(html_val + '</table>', unsafe_allow_html=True)

        # --- 2. FUNDAMENTAL (CON PROMEDIO) ---
        st.divider()
        st.write("### 2. Comparativa Fundamental Avanzada")
        df_fun = df_total.drop(["Precio", "Fair Value (Target)", "Upside (%)"])
        f_ratios = df_fun.index.drop("Empresa")
        df_fun.loc[f_ratios, "PROMEDIO"] = df_fun.loc[f_ratios].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        html_f = '<table style="width:100%; border-collapse: collapse; text-align: center;">'
        html_f += '<tr style="background-color: #f0f2f6;"><th>Indicador</th>'
        for col in df_fun.columns: html_f += f'<th>{col}</th>'
        html_f += '</tr>'
        for idx in df_fun.index:
            bg = "#f2f2f2" if idx == "Empresa" else "#ffffff"
            html_f += f'<tr style="background-color: {bg};"><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_fun.columns:
                val = df_fun.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val): val_show = "-"
                elif idx == "Empresa": val_show = f"<b>{val}</b>" if col != "PROMEDIO" else "-"
                else:
                    try:
                        v_n = float(val)
                        if col != "PROMEDIO":
                            prom = float(df_fun.loc[idx, "PROMEDIO"])
                            posibles_puntos[col] += 1
                            es_mejor = (idx == "Debt/Equity" and v_n < prom) or (idx != "Debt/Equity" and v_n > prom)
                            if es_mejor: style += 'background-color: #c8e6c9; font-weight: bold;'; ranking_puntos[col] += 1
                        if "%" in idx: val_show = f"{v_n*100:.2f}%"
                        elif idx == "Free Cash Flow": val_show = fmt_cur(v_n)
                        else: val_show = f"{v_n:.2f}"
                    except: val_show = str(val)
                html_f += f'<td style="{style}">{val_show}</td>'
            html_f += '</tr>'
        st.write(html_f + '</table>', unsafe_allow_html=True)

        # --- 3. EVOLUCIÓN DE INGRESOS ---
        st.divider()
        if datos_revenue:
            st.write("### 3. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            # Ordenamos para asegurar que Tendencia esté al final
            cols_r = [c for c in df_r.columns if c != "Tendencia"] + ["Tendencia"]
            
            h2 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
            h2 += '<tr style="background-color: #f0f2f6;"><th>Ticker</th>'
            for c in cols_r: h2 += f'<th>{c}</th>'
            h2 += '</tr>'
            for ticker_idx in df_r.index:
                h2 += f'<tr><td style="font-weight:bold; border:1px solid #ddd;">{ticker_idx}</td>'
                for c in cols_r:
                    val_c = df_r.loc[ticker_idx, c]
                    v_s = str(val_c) if c == "Tendencia" else fmt_cur(val_c)
                    h2 += f'<td style="border: 1px solid #ddd; padding: 8px;">{v_s}</td>'
                h2 += '</tr>'
            st.write(h2 + '</table>', unsafe_allow_html=True)
            
            # Gráfico
            df_p_r = df_r.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
            df_p_r['value_b'] = df_p_r['value'] / 1e9
            df_p_r['per'] = df_p_r['variable'].str.split('<').str[0]
            st.altair_chart(alt.Chart(df_p_r).mark_line(point=True).encode(x=alt.X('per', sort=None), y=alt.Y('value_b', title='Billions'), color='Ticker').properties(height=300), use_container_width=True)

        # --- 4. EVOLUCIÓN DE EPS ---
        st.divider()
        if datos_eps:
            st.write("### 4. Evolución de Beneficio por Acción (Basic EPS)")
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            cols_e = [c for c in df_e.columns if c != "Tendencia"] + ["Tendencia"]
            
            h3 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
            h3 += '<tr style="background-color: #f0f2f6;"><th>Ticker</th>'
            for c in cols_e: h3 += f'<th>{c}</th>'
            h3 += '</tr>'
            for ticker_idx in df_e.index:
                h3 += f'<tr><td style="font-weight:bold; border:1px solid #ddd;">{ticker_idx}</td>'
                for c in cols_e:
                    val_c = df_e.loc[ticker_idx, c]
                    v_s = str(val_c) if c == "Tendencia" else f"{val_c:.2f}" if pd.notna(val_c) else "-"
                    h3 += f'<td style="border: 1px solid #ddd; padding: 8px;">{v_s}</td>'
                h3 += '</tr>'
            st.write(h3 + '</table>', unsafe_allow_html=True)
            
            # Gráfico
            df_p_e = df_e.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
            df_p_e['per'] = df_p_e['variable'].str.split('<').str[0]
            st.altair_chart(alt.Chart(df_p_e).mark_line(point=True).encode(x=alt.X('per', sort=None), y=alt.Y('value', title='EPS'), color='Ticker').properties(height=300), use_container_width=True)

        # --- 5. TOP 5 ELITE ---
        st.divider()
        st.write(f"### 🏆 5. Selección Elite: TOP 5 ({modo_estrategia})")
        
        final_scores = []
        for t in lista_tickers:
            if t in analisis_completo:
                p_fun = ranking_puntos[t]
                p_crec = (1 if "28a745" in analisis_completo[t]["rev_t"] else 0) + (1 if "28a745" in analisis_completo[t]["eps_t"] else 0)
                p_up = 1 if analisis_completo[t]["upside_val"] > 0 else 0
                
                if modo_estrategia == "Crecimiento (Agresivo)":
                    score_total = p_fun + p_crec + p_up
                else: # Fortaleza (Defensivo)
                    score_total = p_fun + p_up

                final_scores.append({
                    "Ticker": t, "Nombre": analisis_completo[t]["nombre"],
                    "Total": score_total, "Bonus": p_crec, "Fund": p_fun, "Up": p_up,
                    "Eficacia": (p_fun/posibles_puntos[t]*100) if posibles_puntos[t]>0 else 0,
                    "Margin": analisis_completo[t]["net_margin"]
                })

        top_5 = sorted(final_scores, key=lambda x: (x['Total'], x['Eficacia'], x['Bonus'], x['Margin']), reverse=True)[:5]
        cols_5 = st.columns(5)
        for idx, s in enumerate(top_5):
            with cols_5[idx]:
                st.markdown(f"Puesto #{idx+1}")
                st.markdown(f"<h1 style='text-align: left; margin-top: -20px;'><b>{s['Ticker']}</b></h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size: 1.2em;'>{s['Total']} Puntos</p>", unsafe_allow_html=True)
                
                with st.expander("Ver Racional"):
                    st.write(f"**Fundamentales:**")
                    st.write(f"Posee **{s['Fund']}** indicadores superiores al promedio del grupo.")
                    
                    st.write(f"**Crecimiento:**")
                    if s['Bonus'] == 2:
                        st.write("Crecimiento dual confirmado: Ingresos y EPS al alza (▲).")
                    elif s['Bonus'] == 1:
                        st.write("Crecimiento parcial detectado.")
                    else:
                        st.write("Tendencia de crecimiento estable.")
                    
                    if s['Up'] > 0:
                        st.success("Potencial de Revalorización +")
                    
                    st.write(f"**Eficiencia:** Margen Neto {s['Margin']*100:.2f}%")
else:
    st.info("Ingresa tickers para analizar.")
