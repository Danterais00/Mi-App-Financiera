import streamlit as st
import pandas as pd
import altair as alt

# Importar nuestros módulos
from ui.components import inyectar_css, TOOLTIPS, formatear_moneda
from data.extractor import descargar_datos_mercado
from models.calculators import calcular_puntajes

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Terminal Pro: Inteligencia Financiera", layout="wide", initial_sidebar_state="expanded")
inyectar_css()

# --- INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False

# --- BARRA LATERAL ---
st.sidebar.title("🚀 Terminal Pro")
modo_estrategia = st.sidebar.selectbox("Estrategia:", ["Crecimiento (Agresivo)", "Fortaleza (Defensivo)"])

st.sidebar.divider()
st.sidebar.subheader("📌 Navegación")
menu_seccion = st.sidebar.radio(
    "Ir a:",
    [
        "1. Datos Generales y Valuación", 
        "2. Comparativa Fundamental", 
        "3. Evolución Financiera (Rev & EPS)", 
        "4. Análisis Técnico",
        "🏆 5. Top 10 (Filtro Elite)"
    ]
)

st.title("Inteligencia Financiera Avanzada")
st.markdown(f"<p style='color: #888;'>Estrategia activa: <strong style='color: #fff;'>{modo_estrategia}</strong></p>", unsafe_allow_html=True)

# --- INPUT Y EXTRACCIÓN ---
col1, col2 = st.columns([4, 1])
with col1:
    tickers_raw = st.text_input("Tickers (separados por coma):", "BP, CVX, ET, PBR, TEN, VIST, XOM, AAPL.BA, MSFT.BA, NVDA.BA")
with col2:
    st.write("")
    st.write("")
    btn_analizar = st.button("Sincronizar Datos 🔄", use_container_width=True)

def corregir_ticker(t):
    return "BRK-B" if t == "BRKB" else "BRK-A" if t == "BRKA" else t

# --- LÓGICA PRINCIPAL (CON CACHÉ) ---
if btn_analizar and tickers_raw:
    lista_tickers = [corregir_ticker(t.strip().upper()) for t in tickers_raw.split(",") if t.strip()][:30]
    
    with st.spinner('Extrayendo datos de la bolsa (Buscando en caché primero)...'):
        # Convertimos la lista a tupla. Esto es OBLIGATORIO para que el caché de Streamlit funcione de manera segura.
        tupla_tickers = tuple(lista_tickers)
        
        # Llama a la función. Si la tupla ya se buscó hoy, esto tomará 0 segundos.
        df_fun, df_tec, df_rev, df_eps, analisis = descargar_datos_mercado(tupla_tickers)
        
        if df_fun:
            df_total, df_comp, puntos, posibles = calcular_puntajes(df_fun, lista_tickers)
            
            st.session_state.update({
                "datos_cargados": True, "df_total": df_total, "df_comp": df_comp,
                "df_rev": df_rev, "df_eps": df_eps, "df_tec": df_tec,
                "analisis": analisis, "puntos": puntos, "posibles": posibles, "tickers": lista_tickers
            })
            st.rerun()

# --- RENDERIZADO DE VISTAS ---
if st.session_state.datos_cargados:
    dft = st.session_state.df_total
    
    if menu_seccion == "1. Datos Generales y Valuación":
        st.header("1. Valuación y Perfil de Mercado")
        df_val = dft.loc[["Empresa", "Precio", "Fair Value (Target)", "Upside (%)", "Beta", "Volumen Promedio"]]
        h1 = '<div class="table-container"><table class="custom-table"><tr><th>Indicador</th>'
        for col in df_val.columns: h1 += f'<th>{col}</th>'
        h1 += '</tr>'
        for idx in df_val.index:
            h1 += f'<tr><td class="col-header">{idx}</td>'
            for col in df_val.columns:
                val = df_val.loc[idx, col]; cls = ""
                if pd.isna(val) or val is None: v_sh = "-"
                elif idx == "Beta":
                    v_b = float(val)
                    if v_b <= 1: v_sh = f"<span style='color:#81c784;'>⇠</span> {v_b:.2f}"
                    elif v_b <= 1.5: v_sh = f"<span style='color:#ffd54f;'>⇡</span> {v_b:.2f}"
                    else: v_sh = f"<span style='color:#e57373;'>⇢</span> {v_b:.2f}"
                elif idx == "Upside (%)":
                    v_sh = f"{float(val)*100:.2f}%"
                    if float(val) > 0: cls = "highlight-green"
                elif idx in ["Precio", "Fair Value (Target)"]: v_sh = f"${float(val):,.2f}"
                elif idx == "Empresa": v_sh = f"<b>{val}</b>"
                elif idx == "Volumen Promedio": v_sh = f"{float(val)/1e6:.2f}M"
                else: v_sh = str(val)
                h1 += f'<td class="{cls}">{v_sh}</td>'
            h1 += '</tr>'
        st.write(h1 + '</table></div>', unsafe_allow_html=True)

    elif menu_seccion == "2. Comparativa Fundamental":
        st.header("2. Ratios Fundamentales")
        df_comp = st.session_state.df_comp
        h2 = '<div class="table-container"><table class="custom-table"><tr><th>Indicador</th>'
        for col in df_comp.columns: h2 += f'<th>{col}</th>'
        h2 += '</tr>'
        for idx in df_comp.index:
            t_text = TOOLTIPS.get(idx, "")
            sty = "cursor: help; border-bottom: 1px dotted #888;" if t_text else ""
            h2 += f'<tr><td class="col-header" title="{t_text}"><span style="{sty}">{idx}</span></td>'
            for col in df_comp.columns:
                val = df_comp.loc[idx, col]; cls = ""
                if pd.isna(val) or val is None: v_sh = "-"
                elif idx == "Empresa": v_sh = f"<b>{val}</b>" if col != "PROMEDIO" else "-"
                else:
                    try:
                        v_n = float(val)
                        if col != "PROMEDIO":
                            prom = float(df_comp.loc[idx, "PROMEDIO"])
                            es_mejor = (0 < v_n < prom) if idx == "PER" else (v_n < prom) if idx in ["Debt/Equity", "Cost of Revenue"] else (v_n > prom)
                            if es_mejor: cls = "highlight-green"
                        
                        if "%" in idx: v_sh = f"{v_n*100:.2f}%"
                        elif idx in ["Free Cash Flow", "Net Income", "Cost of Revenue"]: v_sh = formatear_moneda(v_n)
                        else: v_sh = f"{v_n:.2f}"
                    except: v_sh = str(val)
                h2 += f'<td class="{cls}">{v_sh}</td>'
            h2 += '</tr>'
        st.write(h2 + '</table></div>', unsafe_allow_html=True)

    elif menu_seccion == "3. Evolución Financiera (Rev & EPS)":
        st.header("3. Evolución Financiera Histórica")
        df_r, df_e = st.session_state.df_rev, st.session_state.df_eps
        
        if df_r:
            st.subheader("Ingresos (Total Revenue)")
            df_rev_pd = pd.DataFrame(df_r).set_index("Ticker")
            h3 = '<div class="table-container"><table class="custom-table"><tr><th>Ticker</th>'
            for c in df_rev_pd.columns: h3 += f'<th>{c}</th>'
            h3 += '</tr>'
            for t_idx in df_rev_pd.index:
                h3 += f'<tr><td class="col-header">{t_idx}</td>'
                for c in df_rev_pd.columns:
                    val = df_rev_pd.loc[t_idx, c]
                    v_sh = str(val) if c == "Tendencia" else formatear_moneda(val)
                    h3 += f'<td>{v_sh}</td>'
                h3 += '</tr>'
            st.write(h3 + '</table></div>', unsafe_allow_html=True)
            
            df_p = df_rev_pd.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
            df_p['v_b'] = df_p['value'] / 1e9
            df_p['Trimestre'] = df_p['variable'].str.split('<').str[0]
            st.altair_chart(alt.Chart(df_p).mark_line(point=True).encode(
                x=alt.X('Trimestre', sort=None), y=alt.Y('v_b', title='Billions'), color='Ticker'
            ).properties(height=250).configure_view(strokeOpacity=0), use_container_width=True)

        if df_e:
            st.divider()
            st.subheader("Beneficio por Acción (EPS)")
            df_eps_pd = pd.DataFrame(df_e).set_index("Ticker")
            h4 = '<div class="table-container"><table class="custom-table"><tr><th>Ticker</th>'
            for c in df_eps_pd.columns: h4 += f'<th>{c}</th>'
            h4 += '</tr>'
            for t_idx in df_eps_pd.index:
                h4 += f'<tr><td class="col-header">{t_idx}</td>'
                for c in df_eps_pd.columns:
                    val = df_eps_pd.loc[t_idx, c]
                    v_sh = str(val) if c == "Tendencia" else f"{val:.2f}" if pd.notna(val) else "-"
                    h4 += f'<td>{v_sh}</td>'
                h4 += '</tr>'
            st.write(h4 + '</table></div>', unsafe_allow_html=True)

    elif menu_seccion == "4. Análisis Técnico":
        st.header("4. Osciladores y Tendencias")
        df_tec = pd.DataFrame(st.session_state.df_tec).set_index("Ticker").T
        if not df_tec.empty:
            h6 = '<div class="table-container"><table class="custom-table"><tr><th>Indicador Técnico</th>'
            for col in df_tec.columns: h6 += f'<th>{col}</th>'
            h6 += '</tr>'
            for idx in df_tec.index:
                h6 += f'<tr><td class="col-header">{idx}</td>'
                for col in df_tec.columns:
                    val = df_tec.loc[idx, col]; cls = ""
                    if pd.isna(val) or val is None: v_sh = "-"
                    elif "Dist." in idx:
                        v_f = float(val)
                        v_sh = f"{'+' if v_f > 0 else ''}{v_f:.2f}%"
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

    elif menu_seccion == "🏆 5. Top 10 (Filtro Elite)":
        st.header("🏆 Selección Elite: Top 10")
        ana = st.session_state.analisis
        puntos = st.session_state.puntos
        posibles = st.session_state.posibles
        
        scores = []
        for t in st.session_state.tickers:
            if t in ana:
                b_val, u_val = ana[t]["beta_val"], ana[t]["upside_val"]
                if b_val is not None and b_val < 1.5 and ((u_val is None) or (u_val > 0)):
                    p_f = puntos.get(t, 0)
                    p_c = (1 if "81c784" in ana[t]["rev_t"] else 0) + (1 if "81c784" in ana[t]["eps_t"] else 0)
                    total = (p_f + p_c + 1) if "Agresivo" in modo_estrategia else (p_f + 1)
                    
                    scores.append({
                        "t": t, "total": total, "pf": p_f, "pc": p_c, "b": b_val, "u": u_val,
                        "m": ana[t]["net_margin"], "rsi": ana[t]["rsi_val"], "dsma": ana[t]["dist_sma"],
                        "ef": (p_f/posibles[t]*100) if posibles.get(t,0)>0 else 0
                    })
        
        top10 = sorted(scores, key=lambda x: (x['total'], x['ef'], x['pc'], x['m'] if x['m'] else 0), reverse=True)[:10]
        
        if not top10:
            st.warning("Ninguna acción cumple los filtros de Beta < 1.5 y Upside > 0%.")
        else:
            for i in range(0, len(top10), 5):
                cols = st.columns(5)
                for j, s in enumerate(top10[i:i+5]):
                    with cols[j]:
                        st.markdown(f"<p style='color:#888; margin:0;'>Puesto #{i+j+1}</p><h2 style='margin:0; color:#fff;'>{s['t']}</h2><p style='color:#81c784;'><b>{s['total']} Puntos</b></p>", unsafe_allow_html=True)
                        with st.expander("Detalle"):
                            st.write(f"**Beta:** {s['b']:.2f}")
                            st.write(f"**Upside:** {s['u']*100:.1f}%" if s['u'] else "**Upside:** N/A")
                            st.divider()
                            st.write(f"🛡️ **Fortaleza:** {s['pf']} pts")
                            st.write(f"📈 **Momentum:** {'▲▲' if s['pc']==2 else '▲' if s['pc']==1 else 'Estable'}")
                            st.divider()
                            r, d = s['rsi'], s['dsma']
                            if not r or not d: st.write("⚪ Datos Incompletos")
                            elif r < 30: st.write("🟢 COMPRA FUERTE (RSI)")
                            elif 0 <= d <= 5: st.write("🟢 COMPRA IDEAL (Soporte M200)")
                            elif r > 70: st.write("🔴 NO ENTRAR (Euforia)")
                            elif d < 0: st.write("🟡 PRECAUCIÓN (Bajista)")
                            else: st.write("🟡 ZONA NEUTRAL")
else:
    st.info("👈 Ingresa los tickers y presiona 'Sincronizar Datos' para comenzar el análisis.")
