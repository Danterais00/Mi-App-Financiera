import streamlit as st
import pandas as pd
import altair as alt
from streamlit_option_menu import option_menu

# Importar nuestros módulos
from ui.components import inyectar_css, TOOLTIPS, formatear_moneda
from data.extractor import descargar_datos_mercado
from models.calculators import calcular_puntajes
from data.news import obtener_macro_argentina, obtener_macro_internacional, obtener_noticias_acciones

# --- CONSTANTES DE LA APP ---
APP_VERSION = "v4.6"  # Terminal Híbrida: Nivel 1 Macro Integrado

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="SmartInvest", layout="wide", initial_sidebar_state="expanded")
inyectar_css()

# --- INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False

# --- BARRA LATERAL ---
with st.sidebar:
    st.write("")
    modo_estrategia = st.selectbox("Estrategia activa:", ["Crecimiento (Agresivo)", "Fortaleza (Defensivo)"])
    
    st.write("")
    menu_seccion = option_menu(
        menu_title=None,
        options=["Datos y Valuación", "Comparativa", "Evolución Financiera", "Análisis Técnico", "Top 10 Elite", "Noticias de Mercado"],
        icons=['buildings', 'bar-chart-line', 'graph-up-arrow', 'activity', 'trophy', 'newspaper'],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#a3a8b8", "font-size": "16px"},
            "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px", "--hover-color": "#1f2430", "color": "#a3a8b8", "white-space": "nowrap"},
            "nav-link-selected": {"background-color": "#4d8bf0", "color": "#ffffff", "font-weight": "600"},
        }
    )

# --- HEADER PRINCIPAL ---
st.markdown(f"""
    <div style="margin-top: -30px; margin-bottom: 25px;">
        <h1 style="margin: 0; padding: 0; font-size: 2.2rem; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">SmartInvest</h1>
        <p style="margin: 0; padding: 0; color: #8ba1b6; font-size: 0.9rem; font-weight: 500;">{APP_VERSION}</p>
    </div>
""", unsafe_allow_html=True)

# --- INPUT Y EXTRACCIÓN ---
col1, col2 = st.columns([4, 1])
with col1:
    tickers_raw = st.text_input("Tickers (separados por coma):", "BP, CVX, ET, PBR, TEN, VIST, XOM, AAPL.BA, MSFT.BA, NVDA.BA")
with col2:
    st.write("")
    st.write("")
    btn_analizar = st.button("Sincronizar Datos 🔄", use_container_width=True, type="primary")

def corregir_ticker(t):
    return "BRK-B" if t == "BRKB" else "BRK-A" if t == "BRKA" else t

# --- LÓGICA PRINCIPAL ---
if btn_analizar and tickers_raw:
    lista_tickers = [corregir_ticker(t.strip().upper()) for t in tickers_raw.split(",") if t.strip()][:30]
    
    with st.spinner('Procesando lógica institucional...'):
        tupla_tickers = tuple(lista_tickers)
        df_fun, df_tec, df_rev, df_eps, analisis = descargar_datos_mercado(tupla_tickers)
        
        if df_fun:
            df_total, df_comp, puntos, posibles = calcular_puntajes(df_fun, lista_tickers, modo_estrategia)
            
            st.session_state.update({
                "datos_cargados": True, "df_total": df_total, "df_comp": df_comp,
                "df_rev": df_rev, "df_eps": df_eps, "df_tec": df_tec,
                "analisis": analisis, "puntos": puntos, "posibles": posibles, 
                "tickers": lista_tickers, "estrategia_cargada": modo_estrategia
            })
            st.rerun()

# --- RE-CÁLCULO SIN DESCARGA ---
if st.session_state.datos_cargados and st.session_state.estrategia_cargada != modo_estrategia:
    datos_reconstruidos = []
    for t in st.session_state.tickers:
        if t in st.session_state.df_total.columns:
            fila = dict(zip(st.session_state.df_total.index, st.session_state.df_total[t]))
            fila["Ticker"] = t
            datos_reconstruidos.append(fila)
            
    df_total, df_comp, puntos, posibles = calcular_puntajes(datos_reconstruidos, st.session_state.tickers, modo_estrategia)
    st.session_state.update({"df_total": df_total, "df_comp": df_comp, "puntos": puntos, "posibles": posibles, "estrategia_cargada": modo_estrategia})

def get_val(df, metric, ticker):
    try:
        val = df.loc[metric, ticker]
        return float(val) if not pd.isna(val) else None
    except:
        return None

# --- RENDERIZADO DE VISTAS ---

# 1. VISTA INDEPENDIENTE: NOTICIAS
if menu_seccion == "Noticias de Mercado":
    st.header("Noticias de Mercado")
    tab_gen, tab_acc = st.tabs(["🌐 Información General de Mercado", "📰 Noticias de Acciones"])
    
    with tab_gen:
        col_arg, col_int = st.columns(2)
        
        with col_arg:
            # --- MERCADO ARGENTINO ---
            st.subheader("🇦🇷 Mercado Argentino")
            with st.spinner("Sincronizando datos locales..."):
                macro_arg = obtener_macro_argentina()
                rp = macro_arg.get("riesgo_pais")
                merv = macro_arg.get("merval")
                dolares = macro_arg.get("dolares", [])
                
                # 1. CAJA DESTACADA (Para Merval y Riesgo País)
                html_caja = f"""<div style="background-color: #12161f; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39; margin-bottom:15px; display: flex; justify-content: space-between;">
                    <div style="width: 48%;">
                        <p style="margin:0; color:#a3a8b8; font-size:0.85rem; font-weight:bold;">RIESGO PAÍS</p>
                        <h3 style="margin:5px 0; color:#fff;">{rp['valor'] if rp else 'N/D'} <span style="font-size:1rem; color:{'#ff6b6b' if rp and rp.get('variacion', '').startswith('+') else '#2ecca6'};">({rp['variacion'] if rp else '-'})</span></h3>
                    </div>
                    <div style="width: 48%; border-left: 1px solid #2a2e39; padding-left: 15px;">
                        <p style="margin:0; color:#a3a8b8; font-size:0.85rem; font-weight:bold;">S&P MERVAL</p>
                        <h3 style="margin:5px 0; color:#fff;">{f"{merv['valor']:,.0f}" if merv else 'N/D'} <span style="font-size:1rem; color:{'#2ecca6' if merv and merv['var'] > 0 else '#ff6b6b'};">({f"{merv['var']:.2f}%" if merv else "-"})</span></h3>
                    </div>
                </div>"""
                st.markdown(html_caja, unsafe_allow_html=True)
                
                # 2. CÁLCULO DE LA BRECHA Y TABLA MINIMALISTA
                if dolares:
                    # Extraer Oficial y CCL para calcular la brecha
                    val_oficial = next((float(d['venta']) for d in dolares if d['nombre'] == 'Oficial'), None)
                    val_ccl = next((float(d['venta']) for d in dolares if d['nombre'] == 'CCL'), None)
                    brecha = ((val_ccl / val_oficial) - 1) * 100 if val_oficial and val_ccl else None

                    html_arg = '<div class="table-container" style="margin-bottom: 30px;"><table class="custom-table" style="width: 100%;">'
                    html_arg += '<tr><th style="text-align: left;">Tipo de Cambio</th><th>Venta</th><th>Compra</th></tr>'
                    
                    for d in dolares:
                        html_arg += f"<tr><td class='col-header' style='text-align: left;'>Dólar {d['nombre']}</td><td>${d['venta']}</td><td><span style='color:#8ba1b6;'>${d['compra']}</span></td></tr>"
                    
                    # Fila de Brecha Cambiaria
                    if brecha is not None:
                        html_arg += f"<tr style='background-color: rgba(255, 213, 79, 0.05);'><td class='col-header' style='text-align: left; color: #ffd54f;'>Brecha (CCL / Oficial)</td><td colspan='2' style='color: #ffd54f; font-weight: bold; text-align: left; padding-left: 15px;'>{brecha:.1f}%</td></tr>"
                    
                    html_arg += '</table></div>'
                    st.write(html_arg, unsafe_allow_html=True)
                else:
                    st.info("Cotizaciones cambiarias no disponibles en este momento.")

        with col_int:
            # --- MERCADO INTERNACIONAL ---
            st.subheader("🌎 Mercado Internacional")
            with st.spinner("Sincronizando contexto global..."):
                macro_int = obtener_macro_internacional()
                
                html_int = '<div class="table-container"><table class="custom-table" style="width: 100%;">'
                html_int += '<tr><th style="text-align: left;">Indicador Global</th><th>Cotización</th><th>Variación Diaria</th></tr>'
                
                for nombre, datos in macro_int.items():
                    color = "#2ecca6" if datos['var'] > 0 else "#ff6b6b"
                    simbolo = "▲" if datos['var'] > 0 else "▼"
                    html_int += f"<tr><td class='col-header' style='text-align: left;'>{nombre}</td><td>{datos['valor']:.2f}</td><td><span style='color:{color}; font-weight:bold;'>{simbolo} {abs(datos['var']):.2f}%</span></td></tr>"
                
                html_int += '</table></div>'
                st.write(html_int, unsafe_allow_html=True)

    with tab_acc:
        st.subheader("📰 Titulares Recientes de tu Cartera")
        if st.session_state.datos_cargados:
            with st.spinner("Rastreando agencias de noticias..."):
                noticias = obtener_noticias_acciones(st.session_state.tickers)
                for ticker, headlines in noticias.items():
                    if headlines:
                        st.markdown(f"#### 🔵 {ticker}")
                        for h in headlines:
                            st.markdown(f"""
                            <div style="background-color: #171b26; padding: 12px; border-radius: 6px; border-left: 4px solid #4d8bf0; margin-bottom:10px;">
                                <a href="{h['link']}" target="_blank" style="color: #e2e8f0; text-decoration: none; font-weight: 600; font-size: 0.95rem;">{h['titulo']}</a>
                                <p style="margin: 5px 0 0 0; color: #8ba1b6; font-size: 0.75rem;">{h['fecha']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        st.write("")
        else:
            st.info("👈 Ingresa los tickers y presiona 'Sincronizar Datos' para ver las noticias específicas de tus acciones.")

# 2. VISTAS DEPENDIENTES: (Requieren que existan datos de las acciones)
else:
    if st.session_state.datos_cargados:
        dft = st.session_state.df_total
        
        if menu_seccion == "Datos y Valuación":
            st.header("Valuación Futura y Perfil de Mercado")
            filas_mostrar = ["Empresa", "Precio", "Fair Value (Target)", "Upside (%)", "Beta", "Volumen Promedio", "Forward P/E", "PEG Ratio", "EV/EBITDA", "Consenso (1-5)"]
            filas_reales = [f for f in filas_mostrar if f in dft.index]
            df_val = dft.loc[filas_reales]
            h1 = '<div class="table-container"><table class="custom-table"><tr><th>Indicador</th>'
            for col in df_val.columns:
                logo_html = f'<img src="{st.session_state.analisis[col]["logo_url"]}" class="company-logo" onerror="this.style.display=\'none\'">' if col in st.session_state.analisis and st.session_state.analisis[col].get("logo_url") else ''
                h1 += f'<th>{logo_html}{col}</th>'
            h1 += '</tr>'
            for idx in df_val.index:
                t_text = TOOLTIPS.get(idx, "")
                sty = "cursor: help; border-bottom: 1px dotted #888;" if t_text else ""
                h1 += f'<tr><td class="col-header" title="{t_text}"><span style="{sty}">{idx}</span></td>'
                for col in df_val.columns:
                    val = df_val.loc[idx, col]; cls = ""
                    if pd.isna(val) or val is None: v_sh = "-"
                    elif idx == "Beta":
                        v_b = float(val)
                        v_sh = f"<span style='color:#2ecca6;'>⇠</span> {v_b:.2f}" if v_b <= 1 else f"<span style='color:#ffd54f;'>⇡</span> {v_b:.2f}" if v_b <= 1.5 else f"<span style='color:#ff6b6b;'>⇢</span> {v_b:.2f}"
                    elif idx == "Upside (%)":
                        v_sh = f"{float(val)*100:.2f}%"
                        if float(val) > 0: cls = "highlight-green"
                    elif idx in ["Precio", "Fair Value (Target)"]: v_sh = f"${float(val):,.2f}"
                    elif idx == "Consenso (1-5)":
                        v_c = float(val); v_sh = f"{v_c:.1f}"
                        if v_c <= 2.5: cls = "highlight-green"
                    elif idx == "Empresa": v_sh = f"<b>{val}</b>"
                    elif idx == "Volumen Promedio": v_sh = f"{float(val)/1e6:.2f}M"
                    else: 
                        v_sh = f"{float(val):.2f}"
                        if idx == "PEG Ratio" and float(val) < 1.5: cls = "highlight-green"
                        elif idx == "EV/EBITDA" and float(val) < 12: cls = "highlight-green"
                    h1 += f'<td class="{cls}">{v_sh}</td>'
                h1 += '</tr>'
            st.write(h1 + '</table></div>', unsafe_allow_html=True)

        elif menu_seccion == "Comparativa":
            st.header(f"Ratios Contables (Evaluados como: {modo_estrategia})")
            df_comp = st.session_state.df_comp
            h2 = '<div class="table-container"><table class="custom-table"><tr><th>Indicador</th>'
            for col in df_comp.columns:
                if col == "REFERENCIA": h2 += f'<th>{col}</th>'
                else:
                    logo_html = f'<img src="{st.session_state.analisis[col]["logo_url"]}" class="company-logo" onerror="this.style.display=\'none\'">' if col in st.session_state.analisis and st.session_state.analisis[col].get("logo_url") else ''
                    h2 += f'<th>{logo_html}{col}</th>'
            h2 += '</tr>'
            for idx in df_comp.index:
                t_text = TOOLTIPS.get(idx, "")
                sty = "cursor: help; border-bottom: 1px dotted #888;" if t_text else ""
                h2 += f'<tr><td class="col-header" title="{t_text}"><span style="{sty}">{idx}</span></td>'
                for col in df_comp.columns:
                    val = df_comp.loc[idx, col]; cls = ""
                    if col == "REFERENCIA":
                        h2 += f'<td class="col-ref">{val}</td>'; continue
                    elif pd.isna(val) or val is None: v_sh = "-"
                    elif idx == "Empresa": v_sh = f"<b>{val}</b>"
                    else:
                        try:
                            v_n = float(val)
                            if "%" in idx: v_sh = f"{v_n*100:.2f}%"
                            elif idx in ["Current Ratio", "Quick Ratio", "Debt/Equity", "PER"]: v_sh = f"{v_n:.2f}"
                            else: v_sh = str(v_n)
                        except: v_sh = str(val)
                    h2 += f'<td class="{cls}">{v_sh}</td>'
                h2 += '</tr>'
            st.write(h2 + '</table></div>', unsafe_allow_html=True)

        elif menu_seccion == "Evolución Financiera":
            st.header("Evolución Financiera Histórica")
            df_r, df_e = st.session_state.df_rev, st.session_state.df_eps
            if df_r:
                st.subheader("Ingresos (Total Revenue)")
                df_rev_pd = pd.DataFrame(df_r).set_index("Ticker")
                h3 = '<div class="table-container"><table class="custom-table"><tr><th>Ticker</th>'
                for c in df_rev_pd.columns: h3 += f'<th>{c}</th>'
                h3 += '</tr>'
                for t_idx in df_rev_pd.index:
                    logo_html = f'<img src="{st.session_state.analisis[t_idx]["logo_url"]}" class="company-logo" onerror="this.style.display=\'none\'">' if t_idx in st.session_state.analisis and st.session_state.analisis[t_idx].get("logo_url") else ''
                    h3 += f'<tr><td class="col-header">{logo_html}{t_idx}</td>'
                    for c in df_rev_pd.columns:
                        val = df_rev_pd.loc[t_idx, c]
                        v_sh = str(val) if c == "Tendencia" else formatear_moneda(val)
                        h3 += f'<td>{v_sh}</td>'
                    h3 += '</tr>'
                st.write(h3 + '</table></div>', unsafe_allow_html=True)
                
                df_p = df_rev_pd.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
                df_p['v_b'] = pd.to_numeric(df_p['value'], errors='coerce') / 1e9
                df_p['Trimestre'] = df_p['variable'].str.split('<').str[0]
                st.altair_chart(alt.Chart(df_p).mark_line(point=True).encode(
                    x=alt.X('Trimestre', sort=None), y=alt.Y('v_b', title='Billions (USD)'), color='Ticker',
                    tooltip=['Ticker', 'Trimestre', 'v_b']
                ).properties(height=250).configure_view(strokeOpacity=0), use_container_width=True)

            if df_e:
                st.divider()
                st.subheader("Beneficio por Acción (EPS)")
                df_eps_pd = pd.DataFrame(df_e).set_index("Ticker")
                h4 = '<div class="table-container"><table class="custom-table"><tr><th>Ticker</th>'
                for c in df_eps_pd.columns: h4 += f'<th>{c}</th>'
                h4 += '</tr>'
                for t_idx in df_eps_pd.index:
                    logo_html = f'<img src="{st.session_state.analisis[t_idx]["logo_url"]}" class="company-logo" onerror="this.style.display=\'none\'">' if t_idx in st.session_state.analisis and st.session_state.analisis[t_idx].get("logo_url") else ''
                    h4 += f'<tr><td class="col-header">{logo_html}{t_idx}</td>'
                    for c in df_eps_pd.columns:
                        val = df_eps_pd.loc[t_idx, c]
                        v_sh = str(val) if c == "Tendencia" else f"{val:.2f}" if pd.notna(val) else "-"
                        h4 += f'<td>{v_sh}</td>'
                    h4 += '</tr>'
                st.write(h4 + '</table></div>', unsafe_allow_html=True)
                
                df_p_eps = df_eps_pd.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
                df_p_eps['value'] = pd.to_numeric(df_p_eps['value'], errors='coerce')
                df_p_eps['Trimestre'] = df_p_eps['variable'].str.split('<').str[0]
                
                st.altair_chart(alt.Chart(df_p_eps).mark_line(point=True).encode(
                    x=alt.X('Trimestre', sort=None), 
                    y=alt.Y('value', title='EPS (USD)'), 
                    color='Ticker',
                    tooltip=['Ticker', 'Trimestre', 'value']
                ).properties(height=250).configure_view(strokeOpacity=0), use_container_width=True)

        elif menu_seccion == "Análisis Técnico":
            st.header("Osciladores y Tendencias")
            df_tec = pd.DataFrame(st.session_state.df_tec).set_index("Ticker").T
            if not df_tec.empty:
                h6 = '<div class="table-container"><table class="custom-table"><tr><th>Indicador Técnico</th>'
                for col in df_tec.columns:
                    logo_html = f'<img src="{st.session_state.analisis[col]["logo_url"]}" class="company-logo" onerror="this.style.display=\'none\'">' if col in st.session_state.analisis and st.session_state.analisis[col].get("logo_url") else ''
                    h6 += f'<th>{logo_html}{col}</th>'
                h6 += '</tr>'
                for idx in df_tec.index:
                    h6 += f'<tr><td class="col-header">{idx}</td>'
                    for col in df_tec.columns:
                        val = df_tec.loc[idx, col]; cls = ""
                        if pd.isna(val) or val is None: v_sh = "-"
                        elif "Dist." in idx:
                            v_f = float(val); v_sh = f"{'+' if v_f > 0 else ''}{v_f:.2f}%"
                            if "200d" in idx and 0 <= v_f <= 5: cls = "highlight-green"
                        elif "RSI" in idx and "Estado" not in idx: v_sh = f"{float(val):.2f}"
                        elif "Estado" in idx:
                            v_sh = str(val)
                            if "Oportunidad" in val: cls = "highlight-green"
                            elif "Eufórico" in val: cls = "highlight-red"
                        else: v_sh = str(val)
                        h6 += f'<td class="{cls}">{v_sh}</td>'
                    h6 += '</tr>'
                st.write(h6 + '</table></div>', unsafe_allow_html=True)

        elif menu_seccion == "Top 10 Elite":
            es_agresivo = "Agresivo" in modo_estrategia
            st.header(f"🏆 Selección Elite: {'Growth (Agresivo)' if es_agresivo else 'Value (Defensivo)'}")
            ana = st.session_state.analisis
            puntos = st.session_state.puntos
            posibles = st.session_state.posibles
            
            scores = []
            for t in st.session_state.tickers:
                if t in ana:
                    b_val, u_val = ana[t]["beta_val"], ana[t]["upside_val"]
                    limite_beta = 1.5 if es_agresivo else 1.0
                    if b_val is not None and b_val <= limite_beta:
                        p_f = puntos.get(t, 0)
                        p_c = (1 if "2ecca6" in ana[t]["rev_t"] else 0) + (1 if "2ecca6" in ana[t]["eps_t"] else 0)
                        p_u = 1 if (u_val is not None and u_val > 0) else 0
                        total = (p_f + p_c + p_u)
                        scores.append({
                            "t": t, "total": total, "pf": p_f, "pc": p_c, "b": b_val, "u": u_val,
                            "m": ana[t]["net_margin"], "rsi": ana[t]["rsi_val"], "dsma": ana[t]["dist_sma"],
                            "ef": (p_f/posibles[t]*100) if posibles.get(t,0)>0 else 0
                        })
            
            top10 = sorted(scores, key=lambda x: (x['total'], x['ef'], x['pc'], x['m'] if x['m'] else 0), reverse=True)[:10]
            
            if not top10: st.warning(f"Ninguna acción cumple el filtro estricto de riesgo de esta estrategia (Beta < {1.5 if es_agresivo else 1.0}).")
            else:
                st.write("---")
                for i, s in enumerate(top10):
                    col_box, col_text = st.columns([1, 4])
                    ticker = s['t']
                    with col_box:
                        logo_html = f'<img src="{st.session_state.analisis[ticker]["logo_url"]}" class="top10-logo" onerror="this.style.display=\'none\'">' if ticker in st.session_state.analisis and st.session_state.analisis[ticker].get("logo_url") else ''
                        st.markdown(f"""
                        <div style="background-color: #12161f; padding: 12px 5px; border-radius: 12px; border: 1px solid #2a2e39; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                            <p style='color:#a3a8b8; margin:0 0 5px 0; font-size: 0.75rem;'>Puesto #{i+1}</p>
                            {logo_html}
                            <h2 style='margin: 4px 0; color:#ffffff; font-size: 1.6rem;'>{ticker}</h2>
                            <p style='color:#2ecca6; margin:0; font-size: 0.95rem;'><b>{s['total']} Puntos</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_text:
                        roe = get_val(dft, "ROE (%)", ticker); net_margin = get_val(dft, "Margen Neto (%)", ticker)
                        fwd_pe = get_val(dft, "Forward P/E", ticker); peg = get_val(dft, "PEG Ratio", ticker)
                        evebitda = get_val(dft, "EV/EBITDA", ticker); div_yield = get_val(dft, "Div Yield (%)", ticker)
                        payout = get_val(dft, "Payout Ratio (%)", ticker); consenso = get_val(dft, "Consenso (1-5)", ticker)
                        short_int = get_val(dft, "Short Interest (%)", ticker); deuda = get_val(dft, "Debt/Equity", ticker)
                        
                        if es_agresivo:
                            fun_parts = []
                            if roe and roe > 0.15: fun_parts.append(f"ROE sobresaliente del <strong>{roe*100:.1f}%</strong>")
                            if net_margin and net_margin > 0.10: fun_parts.append(f"márgenes netos del <strong>{net_margin*100:.1f}%</strong>")
                            if deuda is not None and deuda < 1.0: fun_parts.append(f"deuda controlada (Debt/Equity: <strong>{deuda:.2f}</strong>)")
                            fun_str = "Excelente eficiencia de capital, con " + " y ".join(fun_parts) + "." if fun_parts else f"Cumple con {s['pf']} métricas institucionales de rentabilidad."
                        else:
                            fun_parts = []
                            if div_yield and div_yield > 0.02:
                                dy_str = f"rendimiento por dividendo del <strong>{div_yield*100:.1f}%</strong>"
                                if payout and payout < 0.6: dy_str += f" (seguro, Payout del <strong>{payout*100:.1f}%</strong>)"
                                fun_parts.append(dy_str)
                            if roe and roe > 0.10: fun_parts.append(f"sólida rentabilidad (ROE <strong>{roe*100:.1f}%</strong>)")
                            fun_str = "Destaca por su perfil de valor, ofreciendo " + " y ".join(fun_parts) + "." if fun_parts else f"Cumple con {s['pf']} métricas de solvencia defensiva."

                        mom_text = "Fuerte impulso alcista tanto en ingresos como en ganancias recientes." if s['pc'] == 2 else "Señales positivas en el crecimiento operativo reciente." if s['pc'] == 1 else "Estabilidad operativa sin un crecimiento expansivo en el corto plazo."
                        
                        val_parts = [f"Beta: <strong>{s['b']:.2f}</strong>"]
                        if es_agresivo:
                            if fwd_pe: val_parts.append(f"Forward P/E: <strong>{fwd_pe:.1f}</strong>")
                            if peg and peg < 1.5: val_parts.append(f"PEG Ratio excepcional de <strong>{peg:.1f}</strong>")
                        else:
                            if evebitda and evebitda < 12: val_parts.append(f"Atractivo EV/EBITDA de <strong>{evebitda:.1f}</strong>")
                            elif fwd_pe and fwd_pe < 20: val_parts.append(f"Valoración razonable (Forward P/E: <strong>{fwd_pe:.1f}</strong>)")
                        if s['u'] and s['u'] > 0: val_parts.append(f"Upside analistas: <strong>{s['u']*100:.1f}%</strong>")
                        if consenso and consenso <= 2.5: val_parts.append(f"Consenso: <strong>Compra ({consenso:.1f}/5)</strong>")
                        
                        riesgo_str = " | ".join(val_parts) + "."
                        r, d = s['rsi'], s['dsma']
                        tec_str = "Faltan datos históricos para emitir juicio técnico."
                        if r and d:
                            if r < 30: tec_str = f"🟢 <strong>COMPRA FUERTE:</strong> RSI en <strong>{r:.1f}</strong> indica sobreventa."
                            elif 0 <= d <= 5: tec_str = f"🟢 <strong>ENTRADA IDEAL:</strong> Rebote inminente sobre media de 200 días."
                            elif r > 70: tec_str = f"🔴 <strong>PRECAUCIÓN:</strong> RSI en <strong>{r:.1f}</strong> (euforia); alto riesgo de recorte."
                            elif d < 0: tec_str = f"🟡 <strong>ALERTA BAJISTA:</strong> Cotizando un <strong>{abs(d):.1f}%</strong> por debajo de media móvil de 200."
                            else: tec_str = f"⚪ <strong>ZONA NEUTRAL:</strong> RSI en <strong>{r:.1f}</strong>, tendencia estable."
                        
                        html_text = f"""
                        <div style="font-size: 0.88rem; line-height: 1.4; color: #cbd5e1; padding: 4px 0;">
                            <p style="margin: 0 0 6px 0; color:#ffffff; font-weight: 600; font-size: 0.95rem;">💡 Racional de Inversión:</p>
                            <p style="margin: 0 0 4px 0;"><strong>• Fundamental:</strong> {fun_str}</p>
                            <p style="margin: 0 0 4px 0;"><strong>• Momentum:</strong> {mom_text}</p>
                            <p style="margin: 0 0 4px 0;"><strong>• Perfil / Valoración:</strong> {riesgo_str}</p>
                            <p style="margin: 0 0 0 0;"><strong>• Timing Técnico:</strong> {tec_str}</p>
                        </div>
                        """
                        st.markdown(html_text, unsafe_allow_html=True)
                    st.write("---")

    else:
        st.info("👈 Ingresa los tickers y presiona 'Sincronizar Datos' para comenzar el análisis.")
