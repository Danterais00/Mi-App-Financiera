import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS SMARTINVEST
st.set_page_config(
    page_title="SmartInvest AI - Terminal Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INYECCIÓN DE CSS PERSONALIZADO (THEME SMARTINVEST DARK PRO) ---
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Urbanist:wght@600;700;800&display=swap');

    /* Variables de Color */
    :root {
        --bg-main: #0a0a0f;
        --bg-card: #14141f;
        --bg-input: #1c1c2b;
        --border-color: #252538;
        --text-main: #f3f4f6;
        --text-muted: #9ca3af;
        --primary: #10b981;
        --danger: #ef4444;
        --blue: #3b82f6;
        --warning: #f59e0b;
    }

    /* Fondo Global y Tipografía */
    .stApp {
        background-color: var(--bg-main);
        font-family: 'Inter', sans-serif;
        color: var(--text-main);
    }

    /* Ocultar elementos nativos innecesarios de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Encabezado Principal SmartInvest */
    .smart-header {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .smart-header h1 {
        font-family: 'Urbanist', sans-serif;
        font-size: 28px;
        font-weight: 800;
        color: #fff;
        margin: 0;
    }
    .smart-header h1 span { color: var(--blue); }
    .smart-header .version-tag {
        font-size: 11px;
        color: var(--text-muted);
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    /* Tarjetas de Métricas TOP 10 */
    .top-card {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 12px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .top-card:hover {
        border-color: var(--blue);
    }
    .top-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .ticker-title {
        font-family: 'Urbanist', sans-serif;
        font-size: 22px;
        font-weight: 800;
        color: #ffffff;
    }
    .score-badge {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid var(--primary);
        color: var(--primary);
        font-weight: 800;
        font-size: 13px;
        padding: 3px 10px;
        border-radius: 8px;
    }
    .rag-pill {
        font-size: 10px;
        font-weight: 700;
        padding: 4px 8px;
        border-radius: 6px;
        display: inline-block;
        margin-bottom: 10px;
    }
    .rag-strong-buy { background: rgba(16, 185, 129, 0.2); color: var(--primary); border: 1px solid var(--primary); }
    .rag-ideal { background: rgba(59, 130, 246, 0.2); color: var(--blue); border: 1px solid var(--blue); }
    .rag-caution { background: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }
    .rag-avoid { background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }

    /* Estilos de Tablas HTML */
    .smart-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 4px;
        margin-top: 10px;
    }
    .smart-table th {
        background-color: transparent;
        color: var(--text-muted);
        font-size: 11px;
        text-transform: uppercase;
        font-weight: 700;
        padding: 10px 12px;
        border-bottom: 1px solid var(--border-color);
        text-align: center;
    }
    .smart-table td {
        background-color: var(--bg-card);
        padding: 12px;
        font-size: 12.5px;
        border-top: 1px solid var(--border-color);
        border-bottom: 1px solid var(--border-color);
        text-align: center;
    }
    .smart-table td:first-child {
        border-left: 1px solid var(--border-color);
        border-radius: 8px 0 0 8px;
        font-weight: 700;
        color: #fff;
    }
    .smart-table td:last-child {
        border-right: 1px solid var(--border-color);
        border-radius: 0 8px 8px 0;
    }
    .cell-highlight {
        background-color: rgba(16, 185, 129, 0.18) !important;
        color: #a7f3d0 !important;
        font-weight: 700;
    }
    .row-promedio td {
        background-color: #1c1c30 !important;
        color: var(--warning) !important;
        font-weight: 700;
    }

    /* Barra lateral */
    section[data-testid="stSidebar"] {
        background-color: var(--bg-card);
        border-right: 1px solid var(--border-color);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# DICCIONARIO DE TOOLTIPS
TOOLTIPS = {
    "Net Income": "Beneficio neto real tras restar gastos e impuestos.",
    "Cost of Revenue": "Gastos directos para fabricar o entregar el producto.",
    "PER": "0-10: Bajo / 10-17: Moderado / 17-25: Alto / >25: Crecimiento Agresivo.",
    "Margen Neto (%)": "Porcentaje de ventas que se convierte en ganancia limpia.",
    "ROE (%)": "Rentabilidad sobre el capital de los accionistas.",
    "ROA (%)": "Rentabilidad sobre el total de activos de la empresa.",
    "Free Cash Flow": "Caja libre tras capex; dinero disponible para dividendos o recompras.",
    "Div Yield (%)": "Rendimiento por dividendo anual en efectivo.",
    "Debt/Equity": "Nivel de apalancamiento financiero.",
    "Current Ratio": "Capacidad para cubrir pasivos de corto plazo.",
    "Quick Ratio": "Liquidez inmediata excluyendo inventarios."
}

# --- HEADER SMARTINVEST ---
st.markdown("""
<div class="smart-header">
    <div>
        <h1>Smart<span>Invest</span> AI</h1>
        <div class="version-tag">Terminal Pro v2.0 • Screener Fundamental & Cuantitativo</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.markdown("### ⚙️ Panel de Control")
modo_estrategia = st.sidebar.radio(
    "Seleccioná tu Estrategia:",
    ["Crecimiento (Agresivo)", "Fortaleza (Defensivo)"],
    help="Agresivo: Impulso operativo. Defensivo: Calidad de balance y valor."
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Filtros Elite Activos:** Beta < 1.5 y Upside > 0% obligatorios para ingresar al TOP 10.")

# --- ENTRADA DE TICKERS ---
tickers_raw = st.text_input(
    "Tickers a analizar (separados por coma):",
    "BP, CVX, ET, PBR, TEN, VIST, XOM, SHEL, AAPL.BA, MSFT.BA, GOOGL.BA, AMZN.BA, MELI.BA, NVDA.BA"
).upper()

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

    with st.spinner("Sincronizando datos de mercado en tiempo real..."):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info or {}
            except Exception:
                info = {}

            # Precio respaldo
            p_actual = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            try:
                if not p_actual or pd.isna(p_actual):
                    hist_backup = accion.history(period="2d")
                    if not hist_backup.empty:
                        p_actual = hist_backup['Close'].iloc[-1]
            except Exception:
                pass

            if not p_actual or pd.isna(p_actual):
                continue

            # Volumen respaldo
            vol_prom = info.get('averageVolume')
            try:
                if not vol_prom or pd.isna(vol_prom):
                    hist_vol = accion.history(period="20d")
                    if not hist_vol.empty:
                        vol_prom = hist_vol['Volume'].mean()
            except Exception:
                pass

            v_justo = info.get('targetMeanPrice')
            beta = info.get('beta')
            upside = ((v_justo / p_actual) - 1) if (p_actual and v_justo and p_actual > 0) else None

            de_raw = info.get('debtToEquity')
            de_final = de_raw / 100 if de_raw is not None else None

            net_income = info.get('netIncomeToCommon') or info.get('netIncome')
            total_rev = info.get('totalRevenue')
            gross_prof = info.get('grossProfits')
            cost_of_rev = (total_rev - gross_prof) if (total_rev and gross_prof) else None

            fila_fun = {
                "Ticker": ticker, "Empresa": info.get('longName', ticker),
                "Precio": p_actual, "Fair Value (Target)": v_justo, "Upside (%)": upside,
                "Beta (Volatilidad)": beta, "Volumen Promedio": vol_prom,
                "Net Income": net_income, "Cost of Revenue": cost_of_rev,
                "PER": info.get('trailingPE'), "Margen Neto (%)": info.get('profitMargins'),
                "ROE (%)": info.get('returnOnEquity'), "ROA (%)": info.get('returnOnAssets'),
                "Free Cash Flow": info.get('freeCashflow'), "Div Yield (%)": info.get('dividendYield'),
                "Debt/Equity": de_final, "Current Ratio": info.get('currentRatio'), "Quick Ratio": info.get('quickRatio')
            }
            datos_fundamentales.append(fila_fun)

            # Capa Técnica
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

                    delta = close_s.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    if loss.iloc[-1] != 0:
                        rsi_val = 100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1])))
                    else:
                        rsi_val = 100 if gain.iloc[-1] > 0 else 50

                    if rsi_val < 30: estado_rsi = "Oportunidad (Sobreventa)"
                    elif rsi_val > 70: estado_rsi = "Eufórico (Sobrecompra)"
            except Exception:
                pass

            fila_tec = {
                "Ticker": ticker,
                "Distancia a Máx Histórico": dist_ath,
                "RSI (14 días)": rsi_val,
                "Estado RSI": estado_rsi,
                "Distancia a Media 200d": dist_sma
            }
            datos_tecnicos.append(fila_tec)

            # Capa Operativa Trimestral
            icon_r, icon_e = '●', '●'
            try:
                df_q = accion.quarterly_financials
                if df_q is not None and not df_q.empty:
                    if not fechas_headers:
                        fechas_raw = df_q.columns[:5][::-1]
                        for idx_f, d in enumerate(fechas_raw):
                            fechas_headers.append(f"{nombres_base[idx_f]} ({d.strftime('%d/%m/%Y')})")

                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, v in enumerate(rev_s):
                            if i < len(fechas_headers): fila_rev[fechas_headers[i]] = v
                        r_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) if len(rev_s) >= 2 else 0
                        icon_r = '▲' if r_growth > 0.05 else '▼' if r_growth < -0.05 else '●'
                        fila_rev["Tendencia"] = icon_r
                        datos_revenue.append(fila_rev)

                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, v in enumerate(eps_s):
                            if i < len(fechas_headers): fila_eps[fechas_headers[i]] = v
                        e_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) if len(eps_s) >= 2 else 0
                        icon_e = '▲' if e_growth > 0.05 else '▼' if e_growth < -0.05 else '●'
                        fila_eps["Tendencia"] = icon_e
                        datos_eps.append(fila_eps)
            except Exception:
                pass

            analisis_completo[ticker] = {
                "nombre": info.get('longName', ticker) if info else ticker,
                "rev_t": icon_r, "eps_t": icon_e,
                "net_margin": info.get('profitMargins', -1) if (info and info.get('profitMargins') is not None) else -1,
                "upside_val": upside if upside is not None else -1,
                "beta_val": beta if beta is not None else 99,
                "rsi_val": rsi_val, "dist_sma": dist_sma
            }

    def fmt_num(n, es_moneda=True):
        if pd.isna(n) or n is None or n == 0: return "-"
        p = "$" if (n >= 0 and es_moneda) else ""
        if n < 0 and es_moneda: p = "-$"
        num = abs(n)
        if num >= 1e12: return f"{p}{num/1e12:.2f}T"
        if num >= 1e9: return f"{p}{num/1e9:.2f}B"
        if num >= 1e6: return f"{p}{num/1e6:.2f}M"
        return f"{p}{num:,.2f}"

    if datos_fundamentales:
        df_fund = pd.DataFrame(datos_fundamentales).set_index("Ticker")
        
        # Calcular Promedios
        promedios = {}
        ratios_cols = ["PER", "Margen Neto (%)", "ROE (%)", "ROA (%)", "Free Cash Flow", "Div Yield (%)", "Debt/Equity", "Current Ratio", "Quick Ratio", "Net Income", "Cost of Revenue"]
        for col in ratios_cols:
            if col in df_fund.columns:
                promedios[col] = pd.to_numeric(df_fund[col], errors='coerce').mean()

        # Calcular Puntos
        for col in ratios_cols:
            if col in df_fund.columns:
                prom = promedios[col]
                for t in df_fund.index:
                    v_raw = df_fund.loc[t, col]
                    if pd.notna(v_raw) and v_raw is not None:
                        v_n = float(v_raw)
                        posibles_puntos[t] += 1
                        if col == "PER": es_mejor = v_n > 10
                        elif col in ["Debt/Equity", "Cost of Revenue"]: es_mejor = v_n < prom
                        else: es_mejor = v_n > prom
                        if es_mejor: ranking_puntos[t] += 1

        # Pestañas Estilizadas
        tab_top, tab_val, tab_fund, tab_rev, tab_eps, tab_tec = st.tabs([
            "🏆 TOP 10 Elite",
            "📊 Valuación & Targets",
            "🏛️ Ratios Fundamentales",
            "💵 Ingresos (5 Trim.)",
            "📈 EPS (5 Trim.)",
            "🚦 Momento Técnico"
        ])

        # --- TAB 1: TOP 10 SELECCIÓN ELITE ---
        with tab_top:
            st.markdown("### 🏆 Selección Elite Cuantitativa")
            final_scores = []
            for t in lista_tickers:
                if t in analisis_completo:
                    meets_beta = analisis_completo[t]["beta_val"] < 1.5
                    meets_upside = analisis_completo[t]["upside_val"] > 0
                    if meets_beta and meets_upside:
                        p_fun = ranking_puntos[t]
                        p_crec = (1 if analisis_completo[t]["rev_t"] == "▲" else 0) + (1 if analisis_completo[t]["eps_t"] == "▲" else 0)
                        score_total = (p_fun + p_crec + 1) if modo_estrategia == "Crecimiento (Agresivo)" else (p_fun + 1)

                        rsi_v = analisis_completo[t]["rsi_val"]
                        dsma_v = analisis_completo[t]["dist_sma"]

                        if rsi_v is None or dsma_v is None:
                            rec_tec, rag_cls = "⚪ Datos insuficientes", "rag-caution"
                        elif rsi_v < 30:
                            rec_tec, rag_cls = "🟢 COMPRA FUERTE (Sobreventa RSI)", "rag-strong-buy"
                        elif 0 <= dsma_v <= 5:
                            rec_tec, rag_cls = "🟢 COMPRA IDEAL (Soporte SMA200)", "rag-ideal"
                        elif rsi_v > 70:
                            rec_tec, rag_cls = "🔴 EVITAR (Sobrecompra)", "rag-avoid"
                        elif dsma_v < 0:
                            rec_tec, rag_cls = "🟡 PRECAUCIÓN (Tendencia Bajista)", "rag-caution"
                        else:
                            rec_tec, rag_cls = "🟡 COMPRA MODERADA", "rag-ideal"

                        final_scores.append({
                            "Ticker": t, "Nombre": analisis_completo[t]["nombre"], "Total": score_total,
                            "Bonus": p_crec, "Fund": p_fun, "Beta": analisis_completo[t]["beta_val"],
                            "Upside": analisis_completo[t]["upside_val"], "Margin": analisis_completo[t]["net_margin"],
                            "RecTec": rec_tec, "RagClass": rag_cls
                        })

            top_10 = sorted(final_scores, key=lambda x: (x['Total'], x['Fund'], x['Margin']), reverse=True)[:10]

            if not top_10:
                st.warning("Ningún ticker cumple las condiciones Sine Qua Non: Beta < 1.5 y Upside > 0%.")
            else:
                for row_i in range(0, len(top_10), 2):
                    cols = st.columns(2)
                    for col_i, s in enumerate(top_10[row_i:row_i+2]):
                        puesto = row_i + col_i + 1
                        with cols[col_i]:
                            st.markdown(f"""
                            <div class="top-card">
                                <div class="top-card-header">
                                    <div>
                                        <span style="font-size:11px; color:var(--text-muted);">Puesto #{puesto}</span>
                                        <div class="ticker-title">{s['Ticker']}</div>
                                        <div style="font-size:11px; color:var(--text-muted);">{s['Nombre']}</div>
                                    </div>
                                    <div class="score-badge">{s['Total']} Pts</div>
                                </div>
                                <div class="rag-pill {s['RagClass']}">{s['RecTec']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            with st.expander("Ver Racional Completo"):
                                st.write(f"🛡️ **Fortaleza:** {s['Fund']} pts sobre la media.")
                                st.write(f"📈 **Momentum:** {'▲▲ Excelente' if s['Bonus']==2 else '▲ Positivo' if s['Bonus']==1 else '● Estable'}")
                                st.write(f"💰 **Margen Neto:** {s['Margin']*100:.2f}%")
                                st.write(f"⚡ **Beta:** {s['Beta']:.2f} | **Upside:** {s['Upside']*100:.1f}%")

        # --- TAB 2: VALUACIÓN & TARGETS ---
        with tab_val:
            html = "<table class='smart-table'><thead><tr><th>Ticker</th><th>Empresa</th><th>Precio</th><th>Fair Value (Target)</th><th>Upside %</th><th>Beta</th><th>Volumen Prom.</th></tr></thead><tbody>"
            for _, f in df_fund.iterrows():
                b_val = f['Beta (Volatilidad)']
                b_icon = '⇠' if b_val and b_val <= 1 else '⇡' if b_val and b_val <= 1.5 else '⇢'
                up_val = f['Upside (%)']
                up_str = f"{up_val*100:.2f}%" if pd.notna(up_val) else "-"
                up_style = "color:#10b981; font-weight:700;" if up_val and up_val > 0 else "color:#ef4444;"

                html += f"""<tr>
                    <td>{f.name}</td>
                    <td>{f['Empresa']}</td>
                    <td>${f['Precio']:,.2f} if pd.notna(f['Precio']) else '-'</td>
                    <td>${f['Fair Value (Target)']:,.2f} if pd.notna(f['Fair Value (Target)']) else '-'</td>
                    <td style="{up_style}">{up_str}</td>
                    <td>{f"{b_val:.2f} {b_icon}" if pd.notna(b_val) else "-"}</td>
                    <td>{f"{f['Volumen Promedio']/1e6:.2f}M" if pd.notna(f['Volumen Promedio']) else "-"}</td>
                </tr>"""
            html += "</tbody></table>"
            st.markdown(html, unsafe_allow_html=True)

        # --- TAB 3: RATIOS FUNDAMENTALES CON HIGHLIGHTS ---
        with tab_fund:
            ratios_head = "".join([f"<th title='{TOOLTIPS.get(r, '')}'>{r}</th>" for r in ratios_cols])
            html = f"<table class='smart-table'><thead><tr><th>Ticker</th>{ratios_head}</tr></thead><tbody>"

            for t_idx, f in df_fund.iterrows():
                html += f"<tr><td>{t_idx}</td>"
                for r in ratios_cols:
                    val = f[r]
                    prom = promedios[r]
                    is_better = False
                    if pd.notna(val) and val is not None:
                        v_n = float(val)
                        if r == "PER": is_better = v_n > 10
                        elif r in ["Debt/Equity", "Cost of Revenue"]: is_better = v_n < prom
                        else: is_better = v_n > prom

                    cls = "cell-highlight" if is_better else ""
                    if pd.isna(val) or val is None: val_str = "-"
                    elif r.includes("%") if hasattr(r, "includes") else "%" in r: val_str = f"{val*100:.2f}%"
                    elif r in ["Free Cash Flow", "Net Income", "Cost of Revenue"]: val_str = fmt_num(val)
                    else: val_str = f"{val:.2f}"

                    html += f"<td class='{cls}'>{val_str}</td>"
                html += "</tr>"

            # Fila Promedio
            html += "<tr class='row-promedio'><td>PROMEDIO</td>"
            for r in ratios_cols:
                p_val = promedios[r]
                if pd.isna(p_val): p_str = "-"
                elif "%" in r: p_str = f"{p_val*100:.2f}%"
                elif r in ["Free Cash Flow", "Net Income", "Cost of Revenue"]: p_str = fmt_num(p_val)
                else: p_str = f"{p_val:.2f}"
                html += f"<td>{p_str}</td>"
            html += "</tr></tbody></table>"
            st.markdown(html, unsafe_allow_html=True)

        # --- TAB 4 Y 5: INGRESOS Y EPS ---
        for tab_obj, datos_list, titulo_lbl, es_moneda in [(tab_rev, datos_revenue, "Ingresos Totales", True), (tab_eps, datos_eps, "Basic EPS", False)]:
            with tab_obj:
                if datos_list:
                    df_m = pd.DataFrame(datos_list).set_index("Ticker")
                    f_cols = [c for c in df_m.columns if c != "Tendencia"]

                    html = f"<table class='smart-table'><thead><tr><th>Ticker</th>"
                    for fc in f_cols: html += f"<th>{fc}</th>"
                    html += "<th>Tendencia</th></tr></thead><tbody>"

                    for t_idx, row in df_m.iterrows():
                        html += f"<tr><td>{t_idx}</td>"
                        for fc in f_cols:
                            val = row[fc]
                            v_str = fmt_num(val, es_moneda) if es_moneda else (f"{val:.2f}" if pd.notna(val) else "-")
                            html += f"<td>{v_str}</td>"
                        html += f"<td style='font-size:16px;'>{row['Tendencia']}</td></tr>"
                    html += "</tbody></table>"
                    st.markdown(html, unsafe_allow_html=True)

                    # Gráfico de Líneas Altair
                    df_plot = df_m.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
                    df_plot['periodo'] = df_plot['variable'].str.split('(').str[0]
                    if es_moneda: df_plot['valor_b'] = df_plot['value'] / 1e9

                    y_col = 'valor_b' if es_moneda else 'value'
                    y_title = 'Billions $' if es_moneda else 'EPS ($)'

                    chart = alt.Chart(df_plot).mark_line(point=True).encode(
                        x=alt.X('periodo', sort=None, title="Trimestre"),
                        y=alt.Y(y_col, title=y_title),
                        color='Ticker'
                    ).properties(height=300).configure_background(
                        fill='transparent'
                    ).configure_view(
                        strokeWidth=0
                    )
                    st.altair_chart(chart, use_container_width=True)

        # --- TAB 6: MOMENTO TÉCNICO ---
        with tab_tec:
            if datos_tecnicos:
                df_t = pd.DataFrame(datos_tecnicos).set_index("Ticker")
                html = "<table class='smart-table'><thead><tr><th>Ticker</th><th>Dist. Máx Histórico</th><th>RSI (14 días)</th><th>Estado RSI</th><th>Dist. Media 200d</th></tr></thead><tbody>"
                for t_idx, row in df_t.iterrows():
                    rsi_v = row['RSI (14 días)']
                    rsi_str = f"{rsi_v:.2f}" if pd.notna(rsi_v) else "-"
                    dsma_v = row['Distancia a Media 200d']
                    dsma_str = f"{dsma_v:+.2f}%" if pd.notna(dsma_v) else "-"
                    dath_v = row['Distancia a Máx Histórico']
                    dath_str = f"{dath_v:+.2f}%" if pd.notna(dath_v) else "-"

                    html += f"""<tr>
                        <td>{t_idx}</td>
                        <td>{dath_str}</td>
                        <td style="font-weight:700;">{rsi_str}</td>
                        <td>{row['Estado RSI']}</td>
                        <td>{dsma_str}</td>
                    </tr>"""
                html += "</tbody></table>"
                st.markdown(html, unsafe_allow_html=True)
else:
    st.info("Ingresá los tickers para iniciar el análisis.")
