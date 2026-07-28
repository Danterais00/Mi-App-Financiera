import streamlit as st
import pandas as pd
from data.news import (
    obtener_macro_argentina, 
    obtener_macro_internacional, 
    obtener_noticias_acciones, 
    generar_analisis_ia
)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="SmartInvest - Visión Estratégica",
    page_icon="📈",
    layout="wide"
)

st.title("📈 SmartInvest - Tablero Estratégico")
st.markdown("Monitor de variables macroeconómicas, noticias en tiempo real y análisis sectorial impulsado por Inteligencia Artificial.")
st.divider()

# --- CARGA DE DATOS MACRO ---
with st.spinner("Obteniendo datos del mercado..."):
    macro_arg = obtener_macro_argentina()
    macro_int = obtener_macro_internacional()

# Cálculo de la Brecha Cambiaria (necesario para el prompt de la IA)
brecha = None
try:
    dolares = macro_arg.get("dolares", [])
    oficial = next((d for d in dolares if d["nombre"].lower() == "oficial"), None)
    ccl = next((d for d in dolares if d["nombre"].lower() == "ccl"), None)
    
    if oficial and ccl and oficial.get("venta") and ccl.get("venta"):
        brecha = ((ccl["venta"] / oficial["venta"]) - 1) * 100
except Exception:
    pass

# --- SECCIÓN 1: MERCADO ARGENTINO ---
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

with col_arg3:
    st.subheader("Riesgo País")
    rp = macro_arg.get("riesgo_pais")
    if rp and rp.get("valor"):
        st.metric(label="Riesgo País (puntos)", value=rp["valor"], delta=rp.get("variacion"), delta_color="inverse")

st.divider()

# --- SECCIÓN 2: MERCADO INTERNACIONAL Y TENDENCIAS ---
st.header("🌎 Mercado Internacional y Tendencias")
st.markdown("Visualización de variables clave y su evolución histórica.")

# Iteramos sobre los datos internacionales para armar el "mini tablero"
for nombre, datos in macro_int.items():
    st.markdown(f"**{nombre}**")
    
    # Creamos 4 columnas para distribuir la información histórica
    col1, col2, col3, col4 = st.columns(4)
    
    valor = datos.get('valor')
    var_diaria = datos.get('var_diaria')
    var_1m = datos.get('var_1m')
    var_6m = datos.get('var_6m')
    
    if valor is not None:
        col1.metric("Valor Actual", f"{valor:.2f}")
    if var_diaria is not None:
        col2.metric("Variación Hoy", f"{var_diaria:.2f}%", delta=f"{var_diaria:.2f}%")
    if var_1m is not None:
        col3.metric("Tendencia 1 Mes", f"{var_1m:.2f}%", delta=f"{var_1m:.2f}%")
    if var_6m is not None:
        col4.metric("Tendencia 6 Meses", f"{var_6m:.2f}%", delta=f"{var_6m:.2f}%")
        
    st.markdown("---") 

# --- SECCIÓN 3: NOTICIAS FINANCIERAS (RECUPERADA) ---
st.header("📰 Noticias del Mercado")
st.markdown("Consulta los últimos titulares de tus activos favoritos.")

# Input interactivo para que el usuario elija los Tickers
tickers_input = st.text_input("Ingresa los Tickers separados por coma (ej: AAPL, MSFT, GGAL, SPY):", "SPY, QQQ, AAPL")
lista_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if lista_tickers:
    with st.spinner("Buscando titulares en Yahoo Finance..."):
        noticias = obtener_noticias_acciones(lista_tickers)
        
        # Mostramos las noticias en columnas dinámicas (hasta 3 columnas para organizar el espacio)
        cols_news = st.columns(min(len(lista_tickers), 3))
        
        for idx, (ticker, entradas) in enumerate(noticias.items()):
            col = cols_news[idx % 3] # Distribuye los tickers uniformemente en las columnas
            with col:
                with st.expander(f"Titulares: {ticker}", expanded=True):
                    if entradas:
                        for noticia in entradas:
                            st.markdown(f"- [{noticia['titulo']}]({noticia['link']})")
                    else:
                        st.write("No se encontraron noticias recientes.")

st.divider()

# --- SECCIÓN 4: INTELIGENCIA ARTIFICIAL ---
st.header("💡 Visión Estratégica de Mercado (IA)")
st.info("El siguiente análisis es generado en tiempo real por el motor Gemini 3.5 Flash, cruzando la macroeconomía local con las tendencias globales (1M y 6M).")

# Botón para generar el reporte de forma interactiva
if st.button("Generar / Actualizar Análisis IA", type="primary"):
    with st.spinner("Analizando ciclo económico y evaluando los 11 sectores GICS. Esto puede tardar hasta 30 segundos..."):
        # Llamamos al motor de IA programado en data/news.py
        reporte_ia = generar_analisis_ia(macro_arg, macro_int, brecha)
        
        # Mostramos el reporte en pantalla
        st.markdown(reporte_ia)
