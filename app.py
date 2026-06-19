import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Terminal Pro: Inteligencia Financiera", layout="wide")

# --- DICCIONARIO DE DEFINICIONES (TOOLTIPS) ---
TOOLTIPS = {
    "Net Income": "indica el beneficio real neto tras restar absolutamente todos los gastos e impuestos.",
    "Cost of Revenue": "Gastos directos para fabricar o entregar el producto.",
    "PER": ("0 - 10 (Bajo): indica que la acción está infravalorada o que el mercado tiene serias dudas sobre su futuro crecimiento. "
            "10 - 17 (Moderado): rango saludable y razonable para empresas establecidas. "
            "17 - 25 (Alto): acción sobrevalorada o que la empresa tiene buenas expectativas de crecimiento futuro que justifican pagar un precio mayor. "
            "Más de 25 (Muy alto): Típico de empresas de crecimiento agresivo. Los inversores pagan mucho hoy esperando beneficios gigantescos mañana."),
    "Margen Neto (%)": "Es la eficiencia operativa. Indica qué porcentaje de las ventas totales se convierte en ganancia limpia.",
    "ROE (%)": "Rentabilidad sobre el capital: mide qué tan bien la directiva multiplica el dinero de los accionistas.",
    "ROA (%)": "Rentabilidad sobre activos: indica la ganancia generada por cada dólard de recurso (propio o deuda) que posee la empresa.",
    "Free Cash Flow": "Caja libre tras gastos operativos y de capital; es el dinero 'real' para dividendos o recompras.",
    "Div Yield (%)": "Rendimiento por dividendo: el interés en efectivo que recibes anualmente por poseer la acción.",
    "Debt/Equity": "Indica el nivel de deuda",
    "Current Ratio": "Mide la capacidad de la empresa para pagar sus deudas de corto plazo.",
    "Quick Ratio": "igual al Current Ratio pero excluye inventarios por ser más difíciles de vender rápido."
}

# --- BARRA LATERAL (ESTRATEGIA) ---
st.sidebar.title("⚙️ Configuración")
modo_estrategia = st.sidebar.radio(
    "Selecciona tu Estrategia:",
    ["Crecimiento (Agresivo)", "Fortaleza (Defensivo)"],
    help="Agresivo: Impulso operativo. Defensivo: Calidad de balance y valor."
)

st.title("🚀 Terminal de Análisis Fundamental Pro")
st.write(f"Modo Activo: **{modo_estrategia}**")
st.info("⚠️ Filtro Elite Activo: Beta < 1.5 y Upside > 0% obligatorio para el TOP 5. PER > 10 para punto de calidad.")

# 2. ENTRADA DE TICKERS
tickers_raw = st.text_input("Tickers (separados por coma):", "BP, CVX, ET, PBR, TEN, VIST, XOM, SHEL, AAPL.BA, MSFT.BA").upper()

def corregir_ticker(t):
    t = t.strip()
    if t == "BRKB": return "BRK-B"
    if t == "BRKA": return "BRK-A"
    return t

if tickers_raw:
    lista_tickers = [corregir_ticker(t) for t in tickers_raw.split(",") if t.strip()][:30]
    
    datos_fundamentales, datos_revenue, datos_eps = [], [], []
    analisis_completo = {}
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    posibles_puntos = {ticker: 0 for ticker in lista_tickers}
    fechas_headers = []

    with st.spinner('Filtrando volúmenes estructurales y procesando balances...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                df_q = accion.quarterly_financials
                
                # --- VALUACIÓN Y BETA ---
                p_actual = info.get('currentPrice')
                v_justo = info.get('targetMeanPrice')
                beta = info.get('beta')
                upside = ((v_justo / p_actual) - 1) if p_actual and v_justo else None

                # --- CAPTURA DE DATOS TOTALES ---
                de_raw = info.get('debtToEquity')
                de_final = de_raw / 100 if de_raw is not None else None
                
                net_income = info.get('netIncomeToCommon') or info.get('netIncome')
                total_rev = info.get('totalRevenue')
                gross_prof = info.get('grossProfits')
                cost_of_rev = (total_rev - gross_prof) if (total_rev and gross_prof) else None

                fila_fun = {
                    "Ticker": ticker, "Empresa": info.get('longName', 'N/A'),
                    "Precio": p_actual, "Fair Value (Target)": v_justo, "Upside (%)": upside,
                    "Beta (Volatilidad)": beta,
                    "Volumen Promedio": info.get('averageVolume'), # Solo conservamos la métrica estructural
                    "Net Income": net_income,
                    "Cost of Revenue": cost_of_rev,
                    "PER": info.get('trailingPE'), "Margen Neto (%)": info.get('profitMargins'),
                    "ROE (%)": info.get('returnOnEquity'), "ROA (%)": info.get('returnOnAssets'),
                    "Free Cash Flow": info.get('freeCashflow'), "Div Yield (%)": info.get('dividendYield'),
                    "Debt/Equity": de_final, 
                    "Current Ratio": info.get('currentRatio'), "Quick Ratio": info.get('quickRatio')
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

                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, v in enumerate(rev_s):
                            if i < len(fechas_headers): fila_rev[fechas_headers[i]] = v
                        r_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) if len(rev_s) >= 2 else 0
                        icon_r = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if r_growth > 0.05 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if r_growth < -0.05 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_rev["Tendencia"] = icon_r
                        datos_revenue.append(fila_rev)
                    
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, v in enumerate(eps_s):
                            if i < len(fechas_headers): fila_eps[fechas_headers[i]] = v
                        e_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) if len(eps_s) >= 2 else 0
                        icon_e = '<span style="color:#28a745; font-size:1.8em;">▲</span>' if e_growth > 0.05 else '<span style="color:#dc3545; font-size:1.8em;">▼</span>' if e_growth < -0.05 else '<span style="color:#ffc107; font-size:1.8em;">●</span>'
                        fila_eps["Tendencia"] = icon_e
                        datos_eps.append(fila_eps)

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker), "rev_t": icon_r, "eps_t": icon_e, 
                    "net_margin": info.get('profitMargins', -1), 
                    "upside_val": upside if upside else -1,
                    "beta_val": beta if beta is not None else 99
                }
            except Exception: pass

    # --- FUNCIÓN DE FORMATEO ---
    def fmt_num(n, es_moneda=True):
        if pd.isna(n) or n == 0: return "-"
        p = "$" if (n >= 0 and es_moneda) else ""
        if n < 0 and es_moneda: p = "-$"
        num = abs(n)
        if num >= 1e12: return f"{p}{num/1e12:.2f}T"
        if num >= 1e9: return f"{p}{num/1e9:.2f}B"
        return f"{p}{num/1e6:.2f}M" if num >= 1e6 else f"{p}{num:,.2f}"

    if datos_fundamentales:
        df_total = pd.DataFrame(datos_fundamentales).set_index("Ticker").T

        # --- 1. VALUACIÓN (SÓLO CON VOLUMEN PROMEDIO) ---
        st.write("### 1. Valuación y Datos de Empresa")
        df_val = df_total.loc[["Empresa", "Precio", "Fair Value (Target)", "Upside (%)", "Beta (Volatilidad)", "Volumen Promedio"]]
        
        h1 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        h1 += '<tr style="background-color: #f0f2f6;"><th>Indicador</th>'
        for col in df_val.columns: h1 += f'<th>{col}</th>'
        h1 += '</tr>'
        for idx in df_val.index:
            h1 += f'<tr style="background-color: #f2f2f2;"><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{idx}</td>'
            for col in df_val.columns:
                val = df_val.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val): val_show = "-"
                elif idx == "Beta (Volatilidad)":
                    v_b = float(val)
                    if v_b <= 1: val_show = f"<span style='color:#28a745; font-size:1.5em;'><strong>⇠</strong></span><br><small>{v_b:.2f}</small>"
                    elif v_b <= 1.5: val_show = f"<span style='color:#ffc107; font-size:1.5em;'><strong>⇡</strong></span><br><small>{v_b:.2f}</small>"
                    else: val_show = f"<span style='color:#dc3545; font-size:1.5em;'><strong>⇢</strong></span><br><small>{v_b:.2f}</small>"
                elif idx == "Upside (%)":
                    v_n = float(val); val_show = f"{v_n*100:.2f}%"
                    if v_n > 0: style += 'background-color: #c8e6c9; color: #2e7d32; font-weight: bold;'
                elif idx == "Empresa": val_show = f"<b>{val}</b>"
                elif idx in ["Precio", "Fair Value (Target)"]: val_show = f"${float(val):,.2f}"
                elif idx == "Volumen Promedio": val_show = fmt_num(val, es_moneda=False)
                else: val_show = str(val)
                h1 += f'<td style="{style}">{val_show}</td>'
            h1 += '</tr>'
        st.write(h1 + '</table>', unsafe_allow_html=True)

        # --- 2. COMPARATIVA FUNDAMENTAL AVANZADA ---
        st.divider()
        st.write("### 2. Comparativa Fundamental Avanzada")
        # Ajuste de drop: quitamos Volumen Promedio de la lista fundamental
        df_fun = df_total.drop(["Precio", "Fair Value (Target)", "Upside (%)", "Beta (Volatilidad)", "Volumen Promedio"])
        f_ratios = df_fun.index.drop("Empresa")
        df_fun.loc[f_ratios, "PROMEDIO"] = df_fun.loc[f_ratios].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        h2 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
        h2 += '<tr style="background-color: #f0f2f6;"><th>Indicador</th>'
        for col in df_fun.columns: h2 += f'<th>{col}</th>'
        h2 += '</tr>'
        for idx in df_fun.index:
            bg = "#f2f2f2" if idx == "Empresa" else "#ffffff"
            t_text = TOOLTIPS.get(idx, "")
            t_attr = f'title="{t_text}"' if t_text else ""
            c_style = "cursor: help;" if t_text else ""
            
            h2 += f'<tr style="background-color: {bg};">'
            h2 += f'<td {t_attr} style="font-weight:bold; border:1px solid #ddd; padding:8px; {c_style}">{idx}</td>'
            
            for col in df_fun.columns:
                val = df_fun.loc[idx, col]
                style = 'border: 1px solid #ddd; padding: 8px;'
                if pd.isna(val): val_show = "-"
                elif idx == "Empresa": val_show = f"<b>{val}</b>" if col != "PROMEDIO" else "-"
                else:
                    try:
                        v_n = float(val)
                        if col != "PROMEDIO":
                            posibles_puntos[col] += 1
                            prom = float(df_fun.loc[idx, "PROMEDIO"])
                            
                            if idx == "PER":
                                es_mejor = v_n > 10
                            elif idx in ["Debt/Equity", "Cost of Revenue"]:
                                es_mejor = v_n < prom
                            else:
                                es_mejor = v_n > prom
                                
                            if es_mejor:
                                style += 'background-color: #c8e6c9; font-weight: bold;'
                                ranking_puntos[col] += 1
                        
                        if "%" in idx: val_show = f"{v_n*100:.2f}%"
                        elif idx in ["Free Cash Flow", "Net Income", "Cost of Revenue"]: val_show = fmt_num(v_n, es_moneda=True)
                        else: val_show = f"{v_n:.2f}"
                    except: val_show = str(val)
                h2 += f'<td style="{style}">{val_show}</td>'
            h2 += '</tr>'
        st.write(h2 + '</table>', unsafe_allow_html=True)

        # --- 3. REVENUE ---
        st.divider()
        if datos_revenue:
            st.write("### 3. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            cols_r = [c for c in df_r.columns if c != "Tendencia"] + ["Tendencia"]
            h3 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
            h3 += '<tr style="background-color: #f0f2f6;"><th>Ticker</th>'
            for c in cols_r: h3 += f'<th>{c}</th>'
            h3 += '</tr>'
            for t_idx in df_r.index:
                h3 += f'<tr><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{t_idx}</td>'
                for c in cols_r:
                    val_c = df_r.loc[t_idx, c]
                    v_s = str(val_c) if c == "Tendencia" else fmt_num(val_c, es_moneda=True)
                    h3 += f'<td style="border: 1px solid #ddd; padding: 8px;">{v_s}</td>'
                h3 += '</tr>'
            st.write(h3 + '</table>', unsafe_allow_html=True)
            df_p_r = df_r.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
            df_p_r['v_b'] = df_p_r['value'] / 1e9; df_p_r['per'] = df_p_r['variable'].str.split('<').str[0]
            st.altair_chart(alt.Chart(df_p_r).mark_line(point=True).encode(x=alt.X('per', sort=None), y=alt.Y('v_b', title='Billions'), color='Ticker').properties(height=300), use_container_width=True)

        # --- 4. EPS ---
        st.divider()
        if datos_eps:
            st.write("### 4. Evolución de Beneficio por Acción (Basic EPS)")
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            cols_e = [c for c in df_e.columns if c != "Tendencia"] + ["Tendencia"]
            h4 = '<table style="width:100%; border-collapse: collapse; text-align: center; border: 1px solid #ddd;">'
            h4 += '<tr style="background-color: #f0f2f6;"><th>Ticker</th>'
            for c in cols_e: h4 += f'<th>{c}</th>'
            h4 += '</tr>'
            for t_idx in df_e.index:
                h4 += f'<tr><td style="font-weight:bold; border:1px solid #ddd; padding:8px;">{t_idx}</td>'
                for c in cols_e:
                    val_c = df_e.loc[t_idx, c]
                    v_s = str(val_c) if c == "Tendencia" else f"{val_c:.2f}"
                    h4 += f'<td style="border: 1px solid #ddd; padding: 8px;">{v_s}</td>'
                h4 += '</tr>'
            st.write(h4 + '</table>', unsafe_allow_html=True)
            df_p_e = df_e.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker"); df_p_e['per'] = df_p_e['variable'].str.split('<').str[0]
            st.altair_chart(alt.Chart(df_p_e).mark_line(point=True).encode(x=alt.X('per', sort=None), y=alt.Y('value', title='EPS ($)'), color='Ticker').properties(height=300), use_container_width=True)

        # --- 5. TOP 5 ELITE ---
        st.divider()
        st.write(f"### 🏆 5. Selección Elite: TOP 5 ({modo_estrategia})")
        final_scores = []
        for t in lista_tickers:
            if t in analisis_completo:
                meets_beta = analisis_completo[t]["beta_val"] < 1.5
                meets_upside = analisis_completo[t]["upside_val"] > 0
                if meets_beta and meets_upside:
                    p_fun = ranking_puntos[t]
                    p_crec = (1 if "28a745" in analisis_completo[t]["rev_t"] else 0) + (1 if "28a745" in analisis_completo[t]["eps_t"] else 0)
                    score_total = (p_fun + p_crec + 1) if modo_estrategia == "Crecimiento (Agresivo)" else (p_fun + 1)
                    final_scores.append({
                        "Ticker": t, "Nombre": analisis_completo[t]["nombre"], "Total": score_total,
                        "Bonus": p_crec, "Fund": p_fun, "Beta": analisis_completo[t]["beta_val"],
                        "Upside": analisis_completo[t]["upside_val"], "Margin": analisis_completo[t]["net_margin"],
                        "Eficacia": (p_fun/posibles_puntos[t]*100) if posibles_puntos[t]>0 else 0
                    })

        top_5 = sorted(final_scores, key=lambda x: (x['Total'], x['Eficacia'], x['Bonus'], x['Margin']), reverse=True)[:5]
        if not top_5:
            st.warning("Ningún ticker cumple: Beta < 1.5 y Upside > 0%.")
        else:
            cols_5 = st.columns(5)
            for idx, s in enumerate(top_5):
                with cols_5[idx]:
                    st.markdown(f"Puesto #{idx+1}")
                    st.markdown(f"<h1 style='text-align: left; margin-top: -20px;'><b>{s['Ticker']}</b></h1>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size: 1.2em;'>{s['Total']} Puntos</p>", unsafe_allow_html=True)
                    with st.expander("Ver Racional"):
                        st.success("✅ **Filtros Sin-Equanon:**")
                        st.write(f"- Beta: **{s['Beta']:.2f}** (< 1.5)")
                        st.write(f"- Upside: **{s['Upside']*100:.1f}%** (> 0)")
                        st.write(f"**🛡️ Fortaleza:** {s['Fund']} pts sobre la media (PER > 10 incluido).")
                        st.write("**📈 Momentum:** ▲▲" if s['Bonus']==2 else "▲" if s['Bonus']==1 else "Estable")
                        st.write(f"**💰 Eficiencia:** Margen {s['Margin']*100:.2f}%")
else:
    st.info("Ingresa los tickers para iniciar el análisis.")
