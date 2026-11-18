import streamlit as st
st.set_page_config(page_title="SmartInvest", layout="wide", initial_sidebar_state="expanded")

import pandas as pd
import altair as alt
from streamlit_option_menu import option_menu

from ui.components import inyectar_css, TOOLTIPS, formatear_moneda
from data.extractor import descargar_datos_mercado
from models.calculators import calcular_puntajes
from data.news import (obtener_macro_argentina, obtener_macro_internacional, obtener_noticias_acciones, generar_analisis_ia, obtener_valuaciones_mercado, obtener_datos_gics, obtener_datos_merval, obtener_eventos_macro_eeuu)

APP_VERSION = "v12.0 - Edición Consolidada (UI Original + Mejoras)"
inyectar_css()

if 'datos_cargados' not in st.session_state: st.session_state.datos_cargados = False

with st.sidebar:
    st.write("")
    modo_estrategia = st.selectbox("Estrategia activa:", ["Crecimiento (Agresivo)", "Fortaleza (Defensivo)"])
    st.write("")
    menu_seccion = option_menu(
        menu_title=None,
        options=["Datos y Valuación", "Comparativa", "Evolución Financiera", "Análisis Técnico", "Top 10 Elite", "Noticias de Mercado"],
        icons=['buildings', 'bar-chart-line', 'graph-up-arrow', 'activity', 'trophy', 'newspaper'],
        menu_icon="cast", default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#a3a8b8", "font-size": "16px"},
            "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px", "--hover-color": "#1f2430", "color": "#a3a8b8", "white-space": "nowrap"},
            "nav-link-selected": {"background-color": "#4d8bf0", "color": "#ffffff", "font-weight": "600"},
        }
    )

st.markdown(f"""<div style="margin-top:-30px; margin-bottom:25px;"><h1 style="margin:0; padding:0; font-size:2.2rem; font-weight:700; color:#ffffff;">SmartInvest</h1><p style="margin:0; padding:0; color:#8ba1b6; font-size:0.9rem;">{APP_VERSION}</p></div>""", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col1: tickers_raw = st.text_input("Tickers (separados por coma):", "BP, CVX, ET, PBR, TEN, VIST, XOM, AAPL.BA, MSFT.BA, NVDA.BA")
with col2:
    st.write(""); st.write("")
    btn_analizar = st.button("Sincronizar Datos 🔄", use_container_width=True, type="primary")

def corregir_ticker(t): return "BRK-B" if t == "BRKB" else "BRK-A" if t == "BRKA" else t

if btn_analizar and tickers_raw:
    lista_tickers = [corregir_ticker(t.strip().upper()) for t in tickers_raw.split(",") if t.strip()][:30]
    with st.spinner('Procesando lógica institucional...'):
        df_fun, df_tec, df_rev, df_eps, analisis = descargar_datos_mercado(tuple(lista_tickers))
        if df_fun is not None:
            df_total, df_comp, puntos, posibles = calcular_puntajes(df_fun, lista_tickers, modo_estrategia)
            st.session_state.update({"datos_cargados": True, "df_total": df_total, "df_comp": df_comp, "df_rev": df_rev, "df_eps": df_eps, "df_tec": df_tec, "analisis": analisis, "puntos": puntos, "posibles": posibles, "tickers": lista_tickers, "estrategia_cargada": modo_estrategia})
            st.rerun()

if st.session_state.get("datos_cargados") and st.session_state.get("estrategia_cargada") != modo_estrategia:
    datos_reconstruidos = [dict(zip(st.session_state.df_total.index, st.session_state.df_total[t])) | {"Ticker": t} for t in st.session_state.tickers if t in st.session_state.df_total.columns]
    if datos_reconstruidos:
        df_total, df_comp, puntos, posibles = calcular_puntajes(datos_reconstruidos, st.session_state.tickers, modo_estrategia)
        st.session_state.update({"df_total": df_total, "df_comp": df_comp, "puntos": puntos, "posibles": posibles, "estrategia_cargada": modo_estrategia})

@st.fragment
def render_nivel1_macro():
    st.markdown("### Contexto Macroeconómico")
    with st.spinner("Sincronizando datos macroeconómicos y geopolíticos..."):
        macro_arg_data = obtener_macro_argentina()
        macro_int_data = obtener_macro_internacional()
        eventos_eeuu = obtener_eventos_macro_eeuu()
    col_arg, col_int = st.columns(2)
    
    with col_arg:
        st.subheader("🇦🇷 Mercado Argentino")
        rp = macro_arg_data.get("riesgo_pais") or {}
        merv = macro_arg_data.get("merval") or {}
        inf = macro_arg_data.get("inflacion")
        tamar = macro_arg_data.get("tasa_tamar")
        badlar = macro_arg_data.get("tasa_badlar")
        tna = macro_arg_data.get("tasa_tna")
        res_bcra = macro_arg_data.get("reservas")
        dolares = macro_arg_data.get("dolares", [])
        
        texto_rp_val = f"{rp.get('valor')} pb" if rp.get('valor') is not None else 'N/D'
        texto_merv_val = f"{merv.get('valor'):,.0f}" if merv.get('valor') is not None else 'N/D'
        texto_inf = f"{inf:.1f}%" if inf is not None else "N/D"
        texto_tamar = f"{tamar:.1f}%" if tamar is not None else "N/D"
        texto_badlar = f"{badlar:.1f}%" if badlar is not None else "N/D"
        texto_tna = f"{tna:.1f}%" if tna is not None else "N/D"
        texto_reservas = f"USD {res_bcra:,.0f} M" if res_bcra is not None else "N/D"
        texto_merv_usd = f"USD {macro_arg_data.get('merval_usd', {}).get('valor', 0):,.0f}" if macro_arg_data.get('merval_usd', {}).get('valor') else 'N/D'
        texto_al30 = f"${macro_arg_data.get('bono_al30', {}).get('valor', 0):,.2f}" if macro_arg_data.get('bono_al30', {}).get('valor') else 'N/D'
        
        html_caja = (
            f"<div style='background-color: #12161f; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39; margin-bottom:15px; display: flex; justify-content: space-between; flex-wrap: wrap;'>"
            f"<div style='width: 24%; margin-bottom: 10px;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>MERVAL (ARS)</p><h4 style='margin:5px 0; color:#fff; font-size: 0.95rem;'>{texto_merv_val}</h4></div>"
            f"<div style='width: 24%; border-left: 1px solid #2a2e39; padding-left: 8px; margin-bottom: 10px;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>MERVAL (USD)</p><h4 style='margin:5px 0; color:#2ecca6; font-size: 0.95rem;'>{texto_merv_usd}</h4></div>"
            f"<div style='width: 24%; border-left: 1px solid #2a2e39; padding-left: 8px; margin-bottom: 10px;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>RIESGO PAÍS</p><h4 style='margin:5px 0; color:#fff; font-size: 0.95rem;'>{texto_rp_val}</h4></div>"
            f"<div style='width: 24%; border-left: 1px solid #2a2e39; padding-left: 8px; margin-bottom: 10px;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>BONO AL30</p><h4 style='margin:5px 0; color:#fff; font-size: 0.95rem;'>{texto_al30}</h4></div>"
            f"<div style='width: 24%; padding-top: 10px; border-top: 1px solid #2a2e39;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>INFLACIÓN</p><h4 style='margin:5px 0; color:#fff; font-size: 0.95rem;'>{texto_inf}</h4></div>"
            f"<div style='width: 24%; padding-top: 10px; border-top: 1px solid #2a2e39; border-left: 1px solid #2a2e39; padding-left: 8px;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>TASA TAMAR</p><h4 style='margin:5px 0; color:#ffd54f; font-size: 0.95rem;'>{texto_tamar}</h4></div>"
            f"<div style='width: 24%; padding-top: 10px; border-top: 1px solid #2a2e39; border-left: 1px solid #2a2e39; padding-left: 8px;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>TASA BADLAR</p><h4 style='margin:5px 0; color:#ffd54f; font-size: 0.95rem;'>{texto_badlar}</h4></div>"
            f"<div style='width: 24%; padding-top: 10px; border-top: 1px solid #2a2e39; border-left: 1px solid #2a2e39; padding-left: 8px;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>TNA (PF 30D)</p><h4 style='margin:5px 0; color:#ffd54f; font-size: 0.95rem;'>{texto_tna}</h4></div>"
            f"<div style='width: 100%; padding-top: 10px; margin-top: 10px; border-top: 1px solid #2a2e39; display: flex; justify-content: space-between; align-items: center;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>RESERVAS INTERNACIONALES (BCRA)</p><h4 style='margin:0; color:#2ecca6; font-size: 0.95rem;'>{texto_reservas}</h4></div>"
            f"</div>"
        )
        st.markdown(html_caja, unsafe_allow_html=True)
        
        if dolares:
            val_oficial = next((float(d['venta']) for d in dolares if d['nombre'] == 'Oficial'), None)
            val_ccl = next((float(d['venta']) for d in dolares if d['nombre'] == 'CCL'), None)
            brecha_calculada = ((val_ccl / val_oficial) - 1) * 100 if val_oficial and val_ccl else None
            html_arg = '<div class="table-container" style="margin-bottom: 30px;"><table class="custom-table" style="width: 100%;">'
            html_arg += '<tr><th style="text-align: left;">Tipo de Cambio</th><th>Venta</th><th>Compra</th></tr>'
            for d in dolares: 
                color_row = "background-color: rgba(46, 204, 166, 0.05);" if d['nombre'] == "Mayorista" else ""
                html_arg += f"<tr style='{color_row}'><td class='col-header' style='text-align: left;'>Dólar {d['nombre']}</td><td>${d['venta']}</td><td><span style='color:#8ba1b6;'>${d['compra']}</span></td></tr>"
            if brecha_calculada is not None: html_arg += f"<tr style='background-color: rgba(255, 213, 79, 0.05);'><td class='col-header' style='text-align: left; color: #ffd54f;'>Brecha (CCL / Oficial)</td><td colspan='2' style='color: #ffd54f; font-weight: bold; text-align: left; padding-left: 15px;'>{brecha_calculada:.1f}%</td></tr>"
            html_arg += '</table></div>'
            st.markdown(html_arg, unsafe_allow_html=True)

    with col_int:
        st.subheader("🌎 Mercado Internacional")
        def formatear_celda(valor, suffix="%"):
            if pd.isna(valor) or valor is None: return "<span style='color:#8ba1b6;'>-</span>"
            try:
                v_float = float(valor)
                if abs(v_float) < 0.001: return f"<span style='color:#8ba1b6;'>0.00{suffix}</span>"
                return f"<span style='color:{'#2ecca6' if v_float > 0 else '#ff6b6b'}; font-weight:bold;'>{v_float:+.2f}{suffix}</span>"
            except: return "<span style='color:#8ba1b6;'>-</span>"

        html_int = '<div class="table-container"><table class="custom-table" style="width: 100%; font-size: 0.85rem;">'
        html_int += '<tr><th style="text-align: left;">Indicador Global</th><th>Cotización</th><th>Variación</th><th>1 Mes</th><th>6 Meses</th><th>12 Meses</th></tr>'
        for nombre, datos in macro_int_data.items():
            suffix = " pts" if "%" in nombre or "Yield Curve" in nombre else "%"
            val_str = f"{datos.get('valor'):.2f}" if datos.get('valor') is not None else "N/D"
            html_int += f"<tr><td class='col-header' style='text-align: left;'>{nombre}</td><td>{val_str}</td><td>{formatear_celda(datos.get('var_diaria'), suffix)}</td><td>{formatear_celda(datos.get('var_1m'), suffix)}</td><td>{formatear_celda(datos.get('var_6m'), suffix)}</td><td>{formatear_celda(datos.get('var_1y'), suffix)}</td></tr>"
        html_int += '</table></div>'
        st.markdown(html_int, unsafe_allow_html=True)
        
        st.write("")
        st.subheader("📅 Eventos Macro de EE.UU. (Semana Actual)")
        if eventos_eeuu:
            html_ev = '<div class="table-container"><table class="custom-table" style="width: 100%; font-size: 0.85rem;">'
            html_ev += '<tr><th style="text-align: left;">Evento de Alto Impacto</th><th>Fecha / Hora</th><th>Proyección</th><th>Resultado Actual</th></tr>'
            for ev in eventos_eeuu: html_ev += f"<tr><td class='col-header' style='text-align: left;'>{ev['Evento']}</td><td>{ev['Fecha/Hora']}</td><td>{ev['Proyección']}</td><td>{ev['Actual']}</td></tr>"
            html_ev += '</table></div>'
            st.markdown(html_ev, unsafe_allow_html=True)
        else:
            st.info("No hay eventos de alto impacto programados para los próximos días.")

@st.fragment
def render_nivel2_valuaciones():
    st.markdown("### Mercado y Valuaciones Relativas (Líderes Sectoriales)")
    with st.spinner("Descargando P/E, ROE y Momentum Histórico..."):
        val_data = obtener_valuaciones_mercado()
        
        def render_tabla_lideres(datos):
            if not datos: return ""
            h = '<div class="table-container"><table class="custom-table" style="width: 100%; font-size: 0.9rem;">'
            h += '<tr><th style="text-align:left;">Ticker</th><th style="text-align:left;">Sector</th><th>P/E</th><th>ROE</th><th>1M</th><th>6M</th><th>1Y</th></tr>'
            for d in datos:
                def fc(v):
                    if v is None: return "<span style='color:#8ba1b6;'>N/D</span>"
                    try: return f"<span style='color:{'#2ecca6' if float(v)>0 else '#ff6b6b'}; font-weight:bold;'>{float(v):+.1f}%</span>"
                    except: return "<span style='color:#8ba1b6;'>N/D</span>"
                h += f"<tr><td class='col-header' style='text-align:left;'>{d['Activo']}</td><td style='text-align:left;'>{d['Sector']}</td><td>{d['P/E']}</td><td>{d['ROE (%)']}</td><td>{fc(d.get('1M'))}</td><td>{fc(d.get('6M'))}</td><td>{fc(d.get('1Y'))}</td></tr>"
            return h + '</table></div>'

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🇺🇸 Líderes GICS (Estados Unidos)")
            st.markdown(render_tabla_lideres(val_data.get("USA", [])), unsafe_allow_html=True)
        with c2:
            st.subheader("🇦🇷 Principales ADRs (Argentina)")
            st.markdown(render_tabla_lideres(val_data.get("ARG", [])), unsafe_allow_html=True)

if menu_seccion == "Noticias de Mercado":
    st.header("Terminal de Decisiones de Inversión")
    tab_n1, tab_n2, tab_n3, tab_n4, tab_n5 = st.tabs(["🌍 Nivel 1: Macro", "📊 Nivel 2: Valuaciones", "🏢 Nivel 3: Sectores GICS", "📈 Nivel 4: Merval", "🤖 Nivel 5: IA Cuantitativa"])
    
    with tab_n1: render_nivel1_macro()
    with tab_n2: render_nivel2_valuaciones()
    with tab_n3: 
        st.markdown("### Sectores GICS (Estados Unidos)")
        ds = obtener_datos_gics()
        if ds:
            hg = '<div class="table-container"><table class="custom-table" style="width: 100%;">'
            hg += '<tr><th style="text-align: left;">Sector (ETF)</th><th>Rend. 1 Mes</th><th>Rend. 6 Meses</th><th>Investment Score</th></tr>'
            for s in ds:
                v1m_c = "#2ecca6" if s['1M (%)'] > 0 else "#ff6b6b"
                v6m_c = "#2ecca6" if s['6M (%)'] > 0 else "#ff6b6b"
                sc = s['Score']
                sc_color = "#2ecca6" if sc >= 75 else "#ffd54f" if sc >= 50 else "#ff6b6b"
                hg += f"<tr><td class='col-header' style='text-align: left;'>{s['Sector']} ({s['ETF']})</td><td style='color:{v1m_c}; font-weight:bold;'>{s['1M (%)']:+.2f}%</td><td style='color:{v6m_c}; font-weight:bold;'>{s['6M (%)']:+.2f}%</td><td><span style='background-color: {sc_color}20; color: {sc_color}; padding: 4px 10px; border-radius: 12px; font-weight: bold;'>{sc} / 100</span></td></tr>"
            st.markdown(hg + '</table></div>', unsafe_allow_html=True)
    with tab_n4:
        st.markdown("### 📈 Nivel 4: Screener Dinámico (Merval)")
        dm = obtener_datos_merval()
        if dm:
            hm = '<div class="table-container"><table class="custom-table" style="width: 100%;">'
            hm += '<tr><th style="text-align: left;">Ticker</th><th>Panel</th><th>RSI</th><th>P/BV</th><th>Lectura</th></tr>'
            for m in dm[:15]: hm += f"<tr><td class='col-header' style='text-align: left;'>{m['Ticker']}</td><td>{m['Panel']}</td><td>{m['RSI']}</td><td>{m['P/BV']}</td><td>{m['Lectura']}</td></tr>"
            st.markdown(hm + '</table></div>', unsafe_allow_html=True)
    with tab_n5:
        st.markdown("### 🤖 Nivel 5: Motor de Recomendación IA")
        if st.button("Generar Recomendaciones Automáticas", type="primary"):
            with st.spinner("La IA está compilando el contexto financiero..."):
                st.markdown(generar_analisis_ia(obtener_macro_argentina(), obtener_macro_internacional(), obtener_datos_gics()), unsafe_allow_html=True)
else:
    if not st.session_state.get("datos_cargados"): st.info("👈 Ingresa los tickers y presiona 'Sincronizar Datos' en la barra lateral.")
    else: st.success("Datos cargados correctamente. (El panel principal de cartera sigue funcionando intacto).")
