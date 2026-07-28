import streamlit as st
import pandas as pd
import yfinance as yf
from data.news import (
    obtener_macro_argentina, 
    obtener_macro_internacional, 
    obtener_noticias_acciones, 
    generar_analisis_ia
)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="SmartInvest - Tablero Estratégico",
    page_icon="📈",
    layout="wide"
)

# --- BARRA LATERAL (MENU DE NAVEGACIÓN) ---
st.sidebar.title("🧭 Navegación")
st.sidebar.markdown("Selecciona una sección:")

seccion = st.sidebar.radio(
    "",
    [
        "Tablero Macro", 
        "Top 10 Acciones", 
        "Análisis de Acciones", 
        "Noticias del Mercado", 
        "Visión Estratégica (IA)"
    ]
)

st.sidebar.divider()
st.sidebar.info("SmartInvest v2.0\nMotor IA: Gemini 3.5 Flash")

# --- CARGA DE DATOS MACRO CENTRALIZADA ---
if seccion in ["Tablero Macro", "Visión Estratégica (IA)"]:
    with st.spinner("Obteniendo datos del mercado..."):
        macro_arg = obtener_macro_argentina()
        macro_int = obtener_macro_internacional()

    brecha = None
    try:
        dolares = macro_arg.get("dolares", [])
        oficial = next((d for d in dolares if d["nombre"].lower() == "oficial"), None)
        ccl = next((d for d in dolares if d["nombre"].lower() == "ccl"), None)
        
        if oficial and ccl and oficial.get("venta") and ccl.get("venta"):
            brecha = ((ccl["venta"] / oficial["venta"]) - 1) * 100
    except Exception:
        pass

# =====================================================================
# RENDERIZADO CONDICIONAL (Muestra la pantalla según la opción elegida)
# =====================================================================

if seccion == "Tablero Macro":
    st.title("📈 Tablero Macroeconómico")
    st.markdown("Monitor de variables clave de Argentina y el mundo.")
    st.divider()
    
    # --- MERCADO ARGENTINO ---
    st.header("🇦🇷 Mercado Argentino")
    col_arg1, col_arg2, col_arg3 = st.columns(3)

    with col_arg1:
        st.subheader("Tipos de Cambio")
        for d in macro_arg.get("dolares", []):
            st.metric(label=f"Dólar {d['nombre']}", value=f"${d['venta']}")

    with col_arg2:
        st.subheader("Mercado de Valores")
        merv = macro_arg.get("merval", {})
        if merv.get("valor"):
            var_merv = merv.get("var_diaria", 0)
            st.metric(label="Merval", value=f"{merv['valor']:,.0f}", delta=f"{var_merv:.2f}%")
            
            var_1m = merv.get("var_1m")
            var_6m = merv.get("var_6m")
            var_1y = merv.get("var_1y")
            tendencias_merv = []
            if var_1m is not None: tendencias_merv.append(f"1M: {var_1m:.2f}%")
            if var_6m is not None: tendencias_merv.append(f"6M: {var_6m:.2f}%")
            if var_1y is not None: tendencias_merv.append(f"1Y: {var_1y:.2f}%")
            if tendencias_merv:
                st.caption(" | ".join(tendencias_merv))

    with col_arg3:
        st.subheader("Riesgo País")
        rp = macro_arg.get("riesgo_pais")
        if rp and rp.get("valor"):
            st.metric(label="Riesgo País (puntos)", value=rp["valor"], delta=rp.get("variacion"), delta_color="inverse")
            if brecha is not None:
                st.caption(f"Brecha Cambiaria (CCL vs Oficial): {brecha:.2f}%")

    st.divider()

    # --- MERCADO INTERNACIONAL Y TENDENCIAS ---
    st.header("🌎 Mercado Internacional y Tendencias")
    st.markdown("Visualización de variables clave y su evolución histórica.")

    for nombre, datos in macro_int.items():
        st.markdown(f"**{nombre}**")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        valor = datos.get('valor')
        var_diaria = datos.get('var_diaria')
        var_1m = datos.get('var_1m')
        var_6m = datos.get('var_6m')
        var_1y = datos.get('var_1y')
        
        if valor is not None:
            col1.metric("Valor Actual", f"{valor:.2f}")
        if var_diaria is not None:
            col2.metric("Variación Hoy", f"{var_diaria:.2f}%", delta=f"{var_diaria:.2f}%")
        if var_1m is not None:
            col3.metric("Tendencia 1 Mes", f"{var_1m:.2f}%", delta=f"{var_1m:.2f}%")
        if var_6m is not None:
            col4.metric("Tendencia 6 Meses", f"{var_6m:.2f}%", delta=f"{var_6m:.2f}%")
        if var_1y is not None:
            col5.metric("Tendencia 1 Año", f"{var_1y:.2f}%", delta=f"{var_1y:.2f}%")
            
        st.markdown("---") 

elif seccion == "Top 10 Acciones":
    st.title("🏆 Top 10 Acciones Destacadas")
    st.markdown("Monitoreo en tiempo real de las acciones de mayor capitalización y relevancia en el mercado (Blue Chips).")
    st.divider()
    
    # Lista predefinida de las 10 empresas más seguidas por fondos institucionales
    top_10_tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "BRK-B", "LLY", "TSLA", "V"]
    
    with st.spinner("Descargando cotizaciones del Top 10..."):
        resultados = []
        for t in top_10_tickers:
            try:
                hist = yf.Ticker(t).history(period="5d")
                if len(hist) >= 2:
                    precio = hist['Close'].iloc[-1]
                    var = ((precio / hist['Close'].iloc[-2]) - 1) * 100
                    resultados.append({
                        "Ticker": t, 
                        "Precio Actual (USD)": f"${precio:.2f}", 
                        "Variación Diaria (%)": round(var, 2)
                    })
            except:
                pass
                
        if resultados:
            df_top10 = pd.DataFrame(resultados)
            df_top10.index += 1 # Que el ranking empiece en 1
            
            # Formateo visual de la tabla (verde para positivo, rojo para negativo)
            def color_variacion(val):
                color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                return f'color: {color}; font-weight: bold'
            
            st.dataframe(
                df_top10.style.applymap(color_variacion, subset=["Variación Diaria (%)"]),
                use_container_width=True
            )
        else:
            st.warning("No se pudieron descargar los datos en este momento. Intenta de nuevo más tarde.")

elif seccion == "Análisis de Acciones":
    st.title("📊 Análisis Fundamental de Acciones")
    st.markdown("Ingresa el ticker de una empresa para ver su rendimiento y ratios clave.")
    st.divider()
    
    ticker_input = st.text_input("Ticker (ej: AAPL, MSFT, GGAL.BA):", "AAPL").upper().strip()
    
    if ticker_input:
        with st.spinner(f"Descargando datos financieros para {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                hist = stock.history(period="1y")
                info = stock.info
                
                if not hist.empty:
                    nombre_empresa = info.get('shortName', ticker_input)
                    st.header(f"{nombre_empresa} ({ticker_input})")
                    
                    st.subheader("Evolución del Precio (Último Año)")
                    st.line_chart(hist['Close'])
                    
                    st.divider()
                    
                    st.subheader("Métricas y Ratios Fundamentales")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    precio_actual = info.get('currentPrice', info.get('regularMarketPrice'))
                    target = info.get('targetMeanPrice')
                    
                    upside = None
                    if precio_actual and target:
                        upside = ((target / precio_actual) - 1) * 100
                        
                    roa = info.get('returnOnAssets')
                    roe = info.get('returnOnEquity')
                    
                    col1.metric("Precio Actual", f"${precio_actual:,.2f}" if precio_actual else "N/D")
                    col2.metric("Precio Objetivo", f"${target:,.2f}" if target else "N/D", delta=f"{upside:.2f}% (Upside)" if upside else None)
                    col3.metric("ROA (Retorno s/ Activos)", f"{roa * 100:.2f}%" if roa else "N/D")
                    col4.metric("ROE (Retorno s/ Equity)", f"{roe * 100:.2f}%" if roe else "N/D")
                    
                    with st.expander("Ver descripción de la empresa"):
                        st.write(info.get('longBusinessSummary', 'Descripción no disponible.'))
                        
                else:
                    st.warning("No se encontraron datos para este Ticker. Verifica que esté bien escrito.")
            except Exception as e:
                st.error(f"Error al procesar el ticker: {e}")

elif seccion == "Noticias del Mercado":
    st.title("📰 Noticias del Mercado")
    st.markdown("Consulta los últimos titulares de tus activos favoritos.")
    st.divider()
    
    tickers_input = st.text_input("Ingresa los Tickers separados por coma (ej: AAPL, MSFT, GGAL, SPY):", "SPY, QQQ, AAPL")
    lista_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    if lista_tickers:
        with st.spinner("Buscando titulares en Yahoo Finance..."):
            noticias = obtener_noticias_acciones(lista_tickers)
            cols_news = st.columns(min(len(lista_tickers), 3))
            
            for idx, (ticker, entradas) in enumerate(noticias.items()):
                col = cols_news[idx % 3]
                with col:
                    with st.expander(f"Titulares: {ticker}", expanded=True):
                        if entradas:
                            for noticia in entradas:
                                st.markdown(f"- [{noticia['titulo']}]({noticia['link']})")
                        else:
                            st.write("No se encontraron noticias recientes.")

elif seccion == "Visión Estratégica (IA)":
    st.title("💡 Visión Estratégica de Mercado (IA)")
    st.info("El siguiente análisis es generado en tiempo real por el motor Gemini 3.5 Flash, cruzando la macroeconomía local con las tendencias globales (1M, 6M y 1Y).")
    st.divider()
    
    if st.button("Generar / Actualizar Análisis IA", type="primary"):
        with st.spinner("Analizando ciclo económico y evaluando los 11 sectores GICS. Esto puede tardar hasta 30 segundos..."):
            reporte_ia = generar_analisis_ia(macro_arg, macro_int, brecha)
            st.markdown(reporte_ia)
