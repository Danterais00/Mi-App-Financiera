import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Terminal Pro: Inteligencia Financiera", layout="wide", initial_sidebar_state="expanded")

# --- INYECCIÓN DE CSS PARA UX/UI (MODO OSCURO Y RESPONSIVO) ---
st.markdown("""
<style>
    /* Forzar fondo oscuro general */
    .stApp {
        background-color: #000000;
        color: #e0e0e0;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    /* Contenedor de tablas responsivo (evita scroll de toda la página) */
    .table-container {
        overflow-x: auto;
        margin-bottom: 2rem;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(255,255,255,0.02);
        border: 1px solid #333;
    }
    
    /* Estilos base de la tabla */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        text-align: center;
        font-size: 0.9rem;
        background-color: #0a0a0a;
    }
    
    .custom-table th {
        background-color: #1a1a1a;
        color: #ffffff;
        padding: 12px 15px;
        border-bottom: 2px solid #333;
        font-weight: 600;
        white-space: nowrap;
    }
    
    .custom-table td {
        padding: 10px 15px;
        border-bottom: 1px solid #222;
        color: #d1d1d1;
    }
    
    .custom-table tr:hover td {
        background-color: #1a1c23;
        transition: background-color 0.2s ease;
    }

    /* Columna de Ticker/Empresa fijada visualmente */
    .col-header {
        font-weight: bold;
        background-color: #111 !important;
        border-right: 1px solid #333;
    }

    /* Clases de resaltado adaptadas a Modo Oscuro */
    .highlight-green {
        background-color: rgba(46, 125, 50, 0.2) !important;
        color: #81c784 !important;
        font-weight: bold;
    }
    .highlight-red {
        background-color: rgba(198, 40, 40, 0.2) !important;
        color: #e57373 !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- DICCIONARIO DE DEFINICIONES (TOOLTIPS) ---
TOOLTIPS = {
    "Net Income": "indica el beneficio real neto tras restar absolutamente todos los gastos es impuestos.",
    "Cost of Revenue": "Gastos directos para fabricar o entregar el producto.",
    "PER": """0 - 10 (Bajo): indica que la acción está infravalorada o que el mercado tiene serias dudas sobre su futuro crecimiento. 
10 - 17 (Moderado): rango saludable y razonable para empresas establecidas. 
17 - 25 (Alto): acción sobrevalorada o que la empresa tiene buenas expectativas de crecimiento futuro que justifican pagar un precio mayor. 
Más de 25 (Muy alto): Típico de empresas de crecimiento agresivo. Los inversores pagan mucho hoy esperando beneficios gigantescos mañana.""",
    "Margen Neto (%)": "Es la eficiencia operativa. Indica qué porcentaje de las ventas totales se convierte en ganancia limpia.",
    "ROE (%)": "Rentabilidad sobre el capital: mide qué tan bien la directiva multiplica el dinero de los accionistas.",
    "ROA (%)": "Rentabilidad sobre activos: indica la ganancia generada por cada dólar de recurso (propio o deuda) que posee la empresa.",
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
st.markdown(f"<h4 style='color: #888;'>Modo Activo: <span style='color: #fff;'>{modo_estrategia}</span></h4>", unsafe_allow_html=True)
st.info("⚠️ Filtro Elite Activo: Beta < 1.5. Upside > 0% (si está disponible) para el TOP 10. PER > 0 y < Promedio para punto de calidad.")

# 2. ENTRADA DE TICKERS
tickers_raw = st.text_input("Tickers (separados por coma):", "BP, CVX, ET, PBR, TEN, VIST, XOM, SHEL, AAPL.BA, MSFT.BA, GOOGL.BA, AMZN.BA, MELI.BA, NVDA.BA").upper()

def corregir_ticker(t):
    t = t.strip()
    if t == "BRKB": return "BRK-B"
    if t == "BRKA": return "BRK-A"
    return t

if tickers_raw:
    lista_tickers = [corregir_ticker(t) for t in tickers_raw.split(",") if t.strip()][:30]
    
    datos_fundamentales, datos_tecnicos, datos_revenue, datos_eps = [], [], [], []
    analisis_completo = {}
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    posibles_puntos = {ticker: 0 for ticker in lista_tickers}
    fechas_headers = []
    nombres_base = ["4 Trim. atrás", "3 Trim. atrás", "2 Trim. atrás", "1 Trim. atrás", "Último Trim."]

    with st.spinner('Sincronizando canales de datos paralelos e incrementando capacidad a TOP 10...'):
        for ticker in lista_tickers:
            # --- CAPTURA SEGURO DE INFO BASE ---
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                if info is None: info = {}
            except Exception as e:
                print(f"Error obteniendo info de {ticker}: {e}")
                info = {}

            # --- SISTEMA DE RESPALDO PARA PRECIO ACTUAL ---
            p_actual = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            try:
                if not p_actual or pd.isna(p_actual):
                    hist_backup = accion.history(period="2d")
                    if not hist_backup.empty:
                        p_actual = hist_backup['Close'].iloc[-1]
            except Exception as e:
                print(f"Error en precio de respaldo {ticker}: {e}")

            if not p_actual or pd.isna(p_actual):
                continue

            # --- SISTEMA DE RESPALDO PARA VOLUMEN PROMEDIO ---
            vol_prom = info.get('averageVolume')
            try:
                if not vol_prom or pd.isna(vol_prom):
                    hist_vol = accion.history(period="20d")
                    if not hist_vol.empty:
                        vol_prom = hist_vol['Volume'].mean()
            except Exception as e:
                print(f"Error en volumen de respaldo {ticker}: {e}")

            # --- EXTRACCIÓN FUNDAMENTAL ---
            v_justo = info.get('targetMeanPrice')
            beta = info.get('beta')
            upside = ((v_justo / p_actual) - 1) if p_actual and v_justo else None

            de_raw = info.get('debtToEquity')
            de_final = de_raw / 100 if de_raw is not None else None
            
            net_income = info.get('netIncomeToCommon') or info.get('netIncome')
            total_rev = info.get('totalRevenue')
            gross_prof = info.get('grossProfits')
            cost_of_rev = (total_rev - gross_prof) if (total_rev and gross_prof) else None

            fila_fun = {
                "Ticker": ticker, "Empresa": info.get('longName', ticker),
                "Precio": p_actual, "Fair Value (Target)": v_justo, "Upside (%)": upside,
                "Beta (Volatilidad)": beta,
                "Volumen Promedio": vol_prom,
                "Net Income": net_income,
                "Cost of Revenue": cost_of_rev,
                "PER": info.get('trailingPE'), "Margen Neto (%)": info.get('profitMargins'),
                "ROE (%)": info.get('returnOnEquity'), "ROA (%)": info.get('returnOnAssets'),
                "Free Cash Flow": info.get('freeCashflow'), "Div Yield (%)": info.get('dividendYield'),
                "Debt/Equity": de_final, 
                "Current Ratio": info.get('currentRatio'), "Quick Ratio": info.get('quickRatio')
            }
            datos_fundamentales.append(fila_fun)

            # --- CAPTURA CAPA TÉCNICA ---
            dist_ath, rsi_val, dist_sma = None, None, None
            estado_rsi = "Neutral"
            try:
                hist = accion.history(period="max")
                if not hist.empty and len(hist) >= 14:
                    close_s = hist['Close']
                    p_ref = p_actual if p_actual is not None else close_s.iloc[-1]
                    
                    ath = close_s.max()
                    dist_ath = ((p_ref / ath) - 1) * 100 if ath else None
                    
                    if len(hist) >= 200:
                        sma200 = close_s.rolling(window=200).mean().iloc[-1]
                        dist_sma = ((p_ref / sma200) - 1) * 100 if sma200 else None
                    
                    # Cálculo de RSI con suavizado exponencial (EWM)
                    delta = close_s.diff()
                    gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
                    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                    if loss.iloc[-1] != 0:
                        rsi_val = 100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1])))
                    else:
                        rsi_val = 100 if gain.iloc[-1] > 0 else 50

                    if rsi_val < 30: estado_rsi = "Oportunidad (Sobreventa)"
                    elif rsi_val > 70: estado_rsi = "Eufórico (Sobrecompra)"
            except Exception as e:
                print(f"Error en capa técnica {ticker}: {e}")

            fila_tec = {
                "Ticker": ticker,
                "Distancia a Máx Histórico": dist_ath,
                "RSI (14 días)": rsi_val,
                "Estado RSI": estado_rsi,
                "Distancia a Media 200d": dist_sma
            }
            datos_tecnicos.append(fila_tec)

            # --- CAPTURA CAPA OPERATIVA HISTÓRICA ---
            icon_r, icon_e = '●', '●'
            try:
                df_q = accion.quarterly_financials
                if df_q is not None and not df_q.empty:
                    if not fechas_headers:
                        fechas_raw = df_q.columns[:5][::-1]
                        for idx_f, d in enumerate(fechas_raw):
                            fechas_headers.append(f"{nombres_base[idx_f]}<br><small style='color:#888;'>{d.strftime('%d/%m/%Y')}</small>")

                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, v in enumerate(rev_s):
                            if i < len(fechas_headers): fila_rev[fechas_headers[i]] = v
                        
                        if len(rev_s) == 5:
                            r_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0]))
                            icon_r = '<span style="color:#81c784; font-size:1.4em;">▲</span>' if r_growth > 0.05 else '<span style="color:#e57373; font-size:1.4em;">▼</span>' if r_growth < -0.05 else '<span style="color:#ffd54f; font-size:1.4em;">●</span>'
                        else:
                            icon_r = '<span style="color:#ffd54f; font-size:1.4em;">●</span>'
                            
                        fila_rev["Tendencia"] = icon_r
                        datos_revenue.append(fila_rev)
                    
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, v in enumerate(eps_s):
                            if i < len(fechas_headers): fila_eps[fechas_headers[i]] = v
                        
                        if len(eps_s) == 5:
                            e_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0]))
                            icon_e = '<span style="color:#81c784; font-size:1.4em;">▲</span>' if e_growth > 0.05 else '<span style="color:#e57373; font-size:1.4em;">▼</span>' if e_growth < -0.05 else '<span style="color:#ffd54f; font-size:1.4em;">●</span>'
                        else:
                            icon_e = '<span style="color:#ffd54f; font-size:1.4em;">●</span>'
                            
                        fila_eps["Tendencia"] = icon_e
                        datos_eps.append(fila_eps)
            except Exception as e:
                print(f"Error en capa operativa {ticker}: {e}")

            analisis_completo[ticker] = {
                "nombre": info.get('longName', ticker) if info else ticker, "rev_t": icon_r, "eps_t": icon_e, 
                "net_margin": info.get('profitMargins', -1) if (info and info.get('profitMargins') is not None) else -1, 
                "upside_val": upside if upside is not None else None,
                "beta_val": beta if beta is not None else 99,
                "rsi_val": rsi_val,
                "dist_sma": dist_sma
            }

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

        # --- 1. VALUACIÓN ---
        st.write("### 1. Valuación y Datos de Empresa")
        df_val = df_total.loc[["Empresa", "Precio", "Fair Value (Target)", "Upside (%)", "Beta (Volatilidad)", "Volumen Promedio"]]
        
        h1 = '<div class="table-container"><table class="custom-table">'
        h1 += '<tr><th>Indicador</th>'
        for col in df_val.columns: h1 += f'<th>{col}</th>'
        h1 += '</tr>'
        for idx in df_val.index:
            h1 += f'<tr><td class="col-header">{idx}</td>'
            for col in df_val.columns:
                val = df_val.loc[idx, col]
                cls = ""
                if pd.isna(val) or val is None: val_show = "-"
                elif idx == "Beta (Volatilidad)":
                    v_b = float(val)
                    if v_b <= 1: val_show = f"<span style='color:#81c784; font-size:1.2em;'><strong>⇠</strong></span> {v_b:.2f}"
                    elif v_b <= 1.5: val_show = f"<span style='color:#ffd54f; font-size:1.2em;'><strong>⇡</strong></span> {v_b:.2f}"
                    else: val_show = f"<span style='color:#e57373; font-size:1.2em;'><strong>⇢</strong></span> {v_b:.2f}"
                elif idx == "Upside (%)":
                    v_n = float(val); val_show = f"{v_n*100:.2f}%"
                    if v_n > 0: cls = "highlight-green"
                elif idx == "Empresa": val_show = f"<b>{val}</b>"
                elif idx in ["Precio", "Fair Value (Target)"]: val_show = f"${float(val):,.2f}"
                elif idx == "Volumen Promedio": 
                    try: val_show = f"{float(val)/1e6:.2f}M"
                    except: val_show = "-"
                else: val_show = str(val)
                h1 += f'<td class="{cls}">{val_show}</td>'
            h1 += '</tr>'
        st.write(h1 + '</table></div>', unsafe_allow_html=True)

        # --- 2. COMPARATIVA FUNDAMENTAL AVANZADA ---
        st.write("### 2. Comparativa Fundamental Avanzada")
        df_fun = df_total.drop(["Precio", "Fair Value (Target)", "Upside (%)", "Beta (Volatilidad)", "Volumen Promedio"])
        f_ratios = df_fun.index.drop("Empresa")
        df_fun.loc[f_ratios, "PROMEDIO"] = df_fun.loc[f_ratios].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        h2 = '<div class="table-container"><table class="custom-table">'
        h2 += '<tr><th>Indicador</th>'
        for col in df_fun.columns: h2 += f'<th>{col}</th>'
        h2 += '</tr>'
        for idx in df_fun.index:
            t_text = TOOLTIPS.get(idx, "")
            t_attr = f'title="{t_text}"' if t_text else ""
            c_style = "cursor: help; border-bottom: 1px dotted #888;" if t_text else ""
            
            h2 += f'<tr><td class="col-header" {t_attr}><span style="{c_style}">{idx}</span></td>'
            
            for col in df_fun.columns:
                val = df_fun.loc[idx, col]
                cls = ""
                if pd.isna(val) or val is None: val_show = "-"
                elif idx == "Empresa": val_show = f"<b>{val}</b>" if col != "PROMEDIO" else "-"
                else:
                    try:
                        v_n = float(val)
                        if col != "PROMEDIO":
                            posibles_puntos[col] += 1
                            prom = float(df_fun.loc[idx, "PROMEDIO"])
                            
                            if idx == "PER":
                                es_mejor = 0 < v_n < prom
                            elif idx in ["Debt/Equity", "Cost of Revenue"]:
                                es_mejor = v_n < prom
                            else:
                                es_mejor = v_n > prom
                                
                            if es_mejor:
                                cls = "highlight-green"
                                ranking_puntos[col] += 1
                        
                        if "%" in idx: val_show = f"{v_n*100:.2f}%"
                        elif idx in ["Free Cash Flow", "Net Income", "Cost of Revenue"]: val_show = fmt_num(v_n, es_moneda=True)
                        else: val_show = f"{v_n:.2f}"
                    except: val_show = str(val)
                h2 += f'<td class="{cls}">{val_show}</td>'
            h2 += '</tr>'
        st.write(h2 + '</table></div>', unsafe_allow_html=True)

        # --- 3. EVOLUCIÓN DE INGRESOS ---
        st.divider()
        if datos_revenue:
            st.write("### 3. Evolución de Ingresos (Total Revenue)")
            df_r = pd.DataFrame(datos_revenue).set_index("Ticker")
            cols_r = [c for c in df_r.columns if c != "Tendencia"] + ["Tendencia"]
            h3 = '<div class="table-container"><table class="custom-table">'
            h3 += '<tr><th>Ticker</th>'
            for c in cols_r: h3 += f'<th>{c}</th>'
            h3 += '</tr>'
            for t_idx in df_r.index:
                h3 += f'<tr><td class="col-header">{t_idx}</td>'
                for c in cols_r:
                    val_c = df_r.loc[t_idx, c]
                    v_s = str(val_c) if c == "Tendencia" else fmt_num(val_c, es_moneda=True)
                    h3 += f'<td>{v_s}</td>'
                h3 += '</tr>'
            st.write(h3 + '</table></div>', unsafe_allow_html=True)
            
            df_p_r = df_r.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
            df_p_r['v_b'] = df_p_r['value'] / 1e9
            df_p_r['per_display'] = df_p_r['variable'].str.split('<').str[0]
            st.altair_chart(alt.Chart(df_p_r).mark_line(point=True).encode(
                x=alt.X('per_display', sort=None, title='Trimestre'), 
                y=alt.Y('v_b', title='Billions'), 
                color='Ticker'
            ).properties(height=300).configure_view(strokeOpacity=0).configure_axis(gridOpacity=0.1), use_container_width=True)

        # --- 4. EVOLUCIÓN DE EPS ---
        st.divider()
        if datos_eps:
            st.write("### 4. Evolución de Beneficio por Acción (Basic EPS)")
            df_e = pd.DataFrame(datos_eps).set_index("Ticker")
            cols_e = [c for c in df_e.columns if c != "Tendencia"] + ["Tendencia"]
            h4 = '<div class="table-container"><table class="custom-table">'
            h4 += '<tr><th>Ticker</th>'
            for c in cols_e: h4 += f'<th>{c}</th>'
            h4 += '</tr>'
            for t_idx in df_e.index:
                h4 += f'<tr><td class="col-header">{t_idx}</td>'
                for c in cols_e:
                    val_c = df_e.loc[t_idx, c]
                    v_s = str(val_c) if c == "Tendencia" else f"{val_c:.2f}" if val_c is not None else "-"
                    h4 += f'<td>{v_s}</td>'
                h4 += '</tr>'
            st.write(h4 + '</table></div>', unsafe_allow_html=True)
            
            df_p_e = df_e.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
            df_p_e['per_display'] = df_p_e['variable'].str.split('<').str[0]
            st.altair_chart(alt.Chart(df_p_e).mark_line(point=True).encode(
                x=alt.X('per_display', sort=None, title='Trimestre'), 
                y=alt.Y('value', title='EPS ($)'), 
                color='Ticker'
            ).properties(height=300).configure_view(strokeOpacity=0).configure_axis(gridOpacity=0.1), use_container_width=True)

        # --- 5. SELECCIÓN ELITE: TOP 10 ---
        st.divider()
        st.write(f"### 🏆 5. Selección Elite: TOP 10 ({modo_estrategia})")
        final_scores = []
        for t in lista_tickers:
            if t in analisis_completo:
                beta_val = analisis_completo[t]["beta_val"]
                upside_val = analisis_completo[t]["upside_val"]
                
                meets_beta = beta_val < 1.5
                meets_upside = (upside_val > 0) if upside_val is not None else True
                
                if meets_beta and meets_upside:
                    p_fun = ranking_puntos[t]
                    p_crec = (1 if "81c784" in analisis_completo[t]["rev_t"] else 0) + (1 if "81c784" in analisis_completo[t]["eps_t"] else 0)
                    score_total = (p_fun + p_crec + 1) if modo_estrategia == "Crecimiento (Agresivo)" else (p_fun + 1)
                    
                    final_scores.append({
                        "Ticker": t, "Nombre": analisis_completo[t]["nombre"], "Total": score_total,
                        "Bonus": p_crec, "Fund": p_fun, "Beta": beta_val,
                        "Upside": upside_val, "Margin": analisis_completo[t]["net_margin"],
                        "Eficacia": (p_fun/posibles_puntos[t]*100) if posibles_puntos[t]>0 else 0,
                        "Rsi": analisis_completo[t]["rsi_val"],
                        "DistSma": analisis_completo[t]["dist_sma"]
                    })

        top_10 = sorted(final_scores, key=lambda x: (x['Total'], x['Eficacia'], x['Bonus'], x['Margin']), reverse=True)[:10]
        if not top_10:
            st.warning("Ningún ticker cumple actualmente las condiciones exigidas: Beta < 1.5 y Upside > 0%.")
        else:
            for row_idx in range(0, len(top_10), 5):
                chunk = top_10[row_idx:row_idx+5]
                cols = st.columns(5)
                for col_idx, s in enumerate(chunk):
                    puesto = row_idx + col_idx + 1
                    with cols[col_idx]:
                        st.markdown(f"<p style='color: #888; font-size:0.9em; margin-bottom: 0;'>Puesto #{puesto}</p>", unsafe_allow_html=True)
                        st.markdown(f"<h2 style='text-align: left; margin-top: 0; color: #fff;'>{s['Ticker']}</h2>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size: 1.1em; color: #81c784;'><b>{s['Total']} Puntos</b></p>", unsafe_allow_html=True)
                        
                        with st.expander("Ver Racional"):
                            st.write("✅ **Filtros Sin-Equanon:**")
                            st.write(f"- Beta: **{s['Beta']:.2f}** (< 1.5)")
                            up_txt = f"{s['Upside']*100:.1f}% (> 0)" if s['Upside'] is not None else "N/A (Sin Target)"
                            st.write(f"- Potencial: **{up_txt}**")
                            st.divider()
                            
                            st.write(f"**🛡️ Fortaleza:** {s['Fund']} pts sobre la media.")
                            st.write("**📈 Momentum:** ▲▲" if s['Bonus']==2 else "▲" if s['Bonus']==1 else "Estable")
                            st.write(f"**💰 Eficiencia:** Margen {s['Margin']*100:.2f}%")
                            st.divider()
                            
                            rsi_v = s["Rsi"]
                            dsma_v = s["DistSma"]
                            
                            if rsi_v is None or dsma_v is None:
                                rec_tec = "⚪ Datos históricos insuficientes"
                            elif rsi_v < 30:
                                rec_tec = "🟢 COMPRA FUERTE (Sobreventa)"
                            elif 0 <= dsma_v <= 5:
                                rec_tec = "🟢 COMPRA IDEAL (Soporte M200)"
                            elif rsi_v > 70:
                                rec_tec = "🔴 NO ENTRAR (Sobrecompra)"
                            elif dsma_v < 0:
                                rec_tec = "🟡 PRECAUCIÓN (Tendencia Bajista)"
                            else:
                                rec_tec = "🟡 COMPRA MODERADA (Zona Neutral)"
                            
                            st.write(f"**🚦 Técnico:** {rec_tec}")

        # --- 6. ANÁLISIS DE MOMENTO TÉCNICO Y TENDENCIA ---
        st.divider()
        st.write("### 6. Análisis de Momento Técnico y Tendencia")
        if datos_tecnicos:
            df_tec = pd.DataFrame(datos_tecnicos).set_index("Ticker").T
            h6 = '<div class="table-container"><table class="custom-table">'
            h6 += '<tr><th>Indicador Técnico</th>'
            for col in df_tec.columns: h6 += f'<th>{col}</th>'
            h6 += '</tr>'
            for idx in df_tec.index:
                h6 += f'<tr><td class="col-header">{idx}</td>'
                for col in df_tec.columns:
                    val = df_tec.loc[idx, col]
                    cls = ""
                    if pd.isna(val) or val is None: val_show = "-"
                    elif idx in ["Distancia a Máx Histórico", "Distancia a Media 200d"]:
                        v_f = float(val)
                        h6_sign = "+" if v_f > 0 else ""
                        val_show = f"{h6_sign}{v_f:.2f}%"
                        if idx == "Distancia a Media 200d" and 0 <= v_f <= 5:
                            cls = "highlight-green"
                    elif idx == "RSI (14 días)":
                        val_show = f"{float(val):.2f}"
                    elif idx == "Estado RSI":
                        val_show = str(val)
                        if val == "Oportunidad (Sobreventa)": cls = "highlight-green"
                        elif val == "Eufórico (Sobrecompra)": cls = "highlight-red"
                    else: val_show = str(val)
                    h6 += f'<td class="{cls}">{val_show}</td>'
                h6 += '</tr>'
            st.write(h6 + '</table></div>', unsafe_allow_html=True)
else:
    st.info("Ingresa los tickers para iniciar el análisis.")
