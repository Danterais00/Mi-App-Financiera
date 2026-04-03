import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Analizador Fundamental", layout="wide")

st.title("📊 Terminal de Análisis Fundamental")

ticker_input = st.text_input("Ingresa el Ticker:", "NVDA").upper()

if ticker_input:
    try:
        accion = yf.Ticker(ticker_input)
        info = accion.info
        
        # --- ENCABEZADO ---
        st.header(f"{info.get('longName', ticker_input)}")
        
        # --- MÉTRICAS DE PRECIO ---
        hist = accion.history(period="2d")
        if not hist.empty:
            precio_actual = hist['Close'].iloc[-1]
            st.subheader(f"Precio Actual: ${precio_actual:.2f} {info.get('currency', 'USD')}")

        st.divider()

        # --- ANÁLISIS FUNDAMENTAL ---
        st.write("### Indicadores Clave")
        
        # Creamos dos filas de columnas para que no se vea amontonado
        col1, col2, col3, col4 = st.columns(4)
        col5, col6, col7, col8 = st.columns(4)

        # Función auxiliar para formatear porcentajes
        def fmt_pct(val):
            return f"{val*100:.2f}%" if val else "N/A"

        # Fila 1: Ratios de Liquidez y Deuda
        col1.metric("Current Ratio", info.get('currentRatio', 'N/A'))
        col2.metric("Quick Ratio", info.get('quickRatio', 'N/A'))
        col3.metric("Debt/Equity", info.get('debtToEquity', 'N/A'))
        col4.metric("EPS (Upa)", info.get('trailingEps', 'N/A'))

        # Fila 2: Rentabilidad y Valoración
        col5.metric("ROA", fmt_pct(info.get('returnOnAssets')))
        col6.metric("ROE", fmt_pct(info.get('returnOnEquity')))
        col7.metric("P/E Ratio (PER)", info.get('trailingPE', 'N/A'))
        col8.metric("Beta (Riesgo)", info.get('beta', 'N/A'))

        st.divider()

        # --- GRÁFICO ---
        st.write("### Evolución del Precio (1 Año)")
        hist_year = accion.history(period="1y")
        st.line_chart(hist_year['Close'])

        # --- DESCRIPCIÓN ---
        with st.expander("Ver descripción de la empresa"):
            st.write(info.get('longBusinessSummary', 'No hay descripción disponible.'))

    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
