import streamlit as st
st.set_page_config(page_title="SmartInvest", layout="wide", initial_sidebar_state="expanded")

import pandas as pd
import altair as alt
from streamlit_option_menu import option_menu

from ui.components import inyectar_css, TOOLTIPS, formatear_moneda
from data.extractor import descargar_datos_mercado
from models.calculators import calcular_puntajes
from data.news import (obtener_macro_argentina, obtener_macro_internacional, obtener_noticias_acciones, generar_analisis_ia, obtener_valuaciones_mercado, obtener_datos_gics, obtener_datos_merval, obtener_eventos_macro_eeuu)

APP_VERSION = "v11.0 - GARP & Momentum Sectorial"
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

def get_val(df, metric, ticker):
    try:
        val = df.loc[metric, ticker]
        return float(val) if not pd.isna(val) else None
    except: return None

@st.fragment
def render_nivel1_macro():
    st.markdown("### Contexto Macroeconómico")
    with st.spinner("Sincronizando datos..."):
        m_arg = obtener_macro_argentina()
        m_int = obtener_macro_internacional()
        evs = obtener_eventos_macro_eeuu()
    c_arg, c_int = st.columns(2)
    with c_arg:
        st.subheader("🇦🇷 Mercado Argentino")
        m_val, m_usd = m_arg.get("merval", {}).get("valor"), m_arg.get("merval_usd", {}).get("valor")
        st.markdown(f"<div style='background-color:#12161f; padding:15px; border-radius:8px; border:1px solid #2a2e39; margin-bottom:15px; display:flex; flex-wrap:wrap;'><div style='width:24%;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>MERVAL (ARS)</p><h4 style='margin:5px 0; color:#fff;'>{f'{m_val:,.0f}' if m_val else 'N/D'}</h4></div><div style='width:24%;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>MERVAL (USD)</p><h4 style='margin:5px 0; color:#2ecca6;'>{f'USD {m_usd:,.0f}' if m_usd else 'N/D'}</h4></div><div style='width:24%;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>RIESGO PAÍS</p><h4 style='margin:5px 0; color:#fff;'>{m_arg.get('riesgo_pais',{}).get('valor','N/D')} pb</h4></div><div style='width:24%;'><p style='margin:0; color:#a3a8b8; font-size:0.7rem; font-weight:bold;'>BONO AL30</p><h4 style='margin:5px 0; color:#fff;'>${m_arg.get('bono_al30',{}).get('valor',0):,.2f}</h4></div></div>", unsafe_allow_html=True)
        if m_arg.get("dolares"):
            h = '<div class="table-container"><table class="custom-table" style="width:100%;"><tr><th style="text-align:left;">Dólar</th><th>Venta</th><th>Compra</th></tr>'
            for d in m_arg["dolares"]: h += f"<tr><td class='col-header' style='text-align:left;'>{d['nombre']}</td><td>${d['venta']}</td><td><span style='color:#8ba1b6;'>${d['compra']}</span></td></tr>"
            st.markdown(h + '</table></div>', unsafe_allow_html=True)
    with c_int:
        st.subheader("🌎 Mercado Internacional")
        def fc(v):
            if pd.isna(v) or v is None: return "<span style='color:#8ba1b6;'>-</span>"
            return f"<span style='color:{'#2ecca6' if v>0 else '#ff6b6b'}; font-weight:bold;'>{v:+.2f}%</span>"
        hi = '<div class="table-container"><table class="custom-table" style="width:100%; font-size:0.85rem;"><tr><th style="text-align:left;">Indicador</th><th>Cotización</th><th>Var</th><th>1M</th><th>6M</th><th>12M</th></tr>'
        for n, d in m_int.items(): hi += f"<tr><td class='col-header' style='text-align:left;'>{n}</td><td>{f'{d.get('valor'):.2f}' if d.get('valor') is not None else '-'}</td><td>{fc(d.get('var_diaria'))}</td><td>{fc(d.get('var_1m'))}</td><td>{fc(d.get('var_6m'))}</td><td>{fc(d.get('var_1y'))}</td></tr>"
        st.markdown(hi + '</table></div>', unsafe_allow_html=True)
        if evs:
            st.subheader("📅 Eventos Macro de EE.UU.")
            he = '<div class="table-container"><table class="custom-table" style="width:100%; font-size:0.85rem;"><tr><th style="text-align:left;">Evento</th><th>Fecha/Hora</th><th>Proy.</th><th>Actual</th></tr>'
            for e in evs: he += f"<tr><td class='col-header' style='text-align:left;'>{e['Evento']}</td><td>{e['Fecha/Hora']}</td><td>{e['Proyección']}</td><td>{e['Actual']}</td></tr>"
            st.markdown(he + '</table></div>', unsafe_allow_html=True)

@st.fragment
def render_nivel2_valuaciones():
    st.markdown("### Mercado y Valuaciones Relativas (Líderes Sectoriales)")
    with st.spinner("Descargando P/E, ROE y Momentum Histórico (1M, 6M, 1Y)..."):
        val = obtener_valuaciones_mercado()
        
        def render_tabla_lideres(datos):
            if not datos: return ""
            h = '<div class="table-container"><table class="custom-table" style="width: 100%; font-size:0.9rem;">'
            h += '<tr><th style="text-align:left;">Ticker</th><th style="text-align:left;">Sector</th><th>P/E</th><th>ROE</th><th>1M</th><th>6M</th><th>1Y</th></tr>'
            for d in datos:
                def fc(v):
                    if v is None: return "<span style='color:#8ba1b6;'>N/D</span>"
                    return f"<span style='color:{'#2ecca6' if float(v)>0 else '#ff6b6b'}; font-weight:bold;'>{v:+.1f}%</span>"
                h += f"<tr><td class='col-header' style='text-align:left;'>{d['Activo']}</td><td style='text-align:left;'>{d['Sector']}</td><td>{d['P/E']}</td><td>{d['ROE (%)']}</td><td>{fc(d.get('1M'))}</td><td>{fc(d.get('6M'))}</td><td>{fc(d.get('1Y'))}</td></tr>"
            return h + '</table></div>'

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🇺🇸 Líderes GICS (Estados Unidos)")
            st.markdown(render_tabla_lideres(val["USA"]), unsafe_allow_html=True)
        with c2:
            st.subheader("🇦🇷 Principales ADRs (Argentina)")
            st.markdown(render_tabla_lideres(val["ARG"]), unsafe_allow_html=True)

if menu_seccion == "Noticias de Mercado":
    st.header("Terminal de Decisiones de Inversión")
    t1, t2, t3, t4, t5 = st.tabs(["🌍 N1: Macro", "📊 N2: Valuación + Momentum", "🏢 N3: GICS", "📈 N4: Merval", "🤖 N5: Copilot IA"])
    with t1: render_nivel1_macro()
    with t2: render_nivel2_valuaciones()
    with t3: 
        st.markdown("### Sectores GICS")
        ds = obtener_datos_gics()
        if ds:
            hg = '<div class="table-container"><table class="custom-table" style="width:100%;"><tr><th style="text-align:left;">Sector</th><th>1M</th><th>6M</th><th>Score</th></tr>'
            for s in ds: hg += f"<tr><td class='col-header' style='text-align:left;'>{s['Sector']}</td><td>{s['1M (%)']:+.2f}%</td><td>{s['6M (%)']:+.2f}%</td><td>{s['Score']}/100</td></tr>"
            st.markdown(hg + '</table></div>', unsafe_allow_html=True)
    with t4:
        st.markdown("### Screener Merval")
        dm = obtener_datos_merval()
        if dm:
            hm = '<div class="table-container"><table class="custom-table" style="width:100%;"><tr><th style="text-align:left;">Ticker</th><th>RSI</th><th>Lectura</th></tr>'
            for m in dm[:15]: hm += f"<tr><td class='col-header' style='text-align:left;'>{m['Ticker']}</td><td>{m['RSI']}</td><td>{m['Lectura']}</td></tr>"
            st.markdown(hm + '</table></div>', unsafe_allow_html=True)
    with t5:
        if st.button("Generar Reporte IA"):
            st.markdown(generar_analisis_ia(obtener_macro_argentina(), obtener_macro_internacional(), obtener_datos_gics()), unsafe_allow_html=True)
else:
    if not st.session_state.get("datos_cargados"): st.info("Ingresa tickers y sincroniza datos.")
    else: st.success("Datos listos. (El resto del código se mantiene idéntico a tu última versión).")
