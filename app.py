import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Analizador Financiero", layout="centered")

st.title("📈 Mi Terminal de Inversiones")
st.write("Introduce el ticker de una acción para ver su salud financiera.")

# Entrada de Ticker
ticker_input = st.text_input("Ticker (ej: AAPL, TSLA, MELI, BTC-USD)", "AAPL").upper()

if ticker_input:
    try:
        accion = yf.Ticker(ticker_input)
        info = accion.info
        
        # Nombre y Precio
        nombre_empresa = info.get('longName', ticker_input)
        precio_actual = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
        moneda = info.get('currency', 'USD')

        st.header(f"{nombre_empresa}")
        st.subheader(f"Precio Actual: {precio_actual} {moneda}")

        # Columnas de datos clave
        col1, col2, col3 = st.columns(3)
        col1.metric("Market Cap", f"{info.get('marketCap', 0):,}")
        col2.metric("P/E Ratio", info.get('trailingPE', 'N/A'))
        col3.metric("Div. Yield", f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "0%")

        # Gráfico
        st.write("### Evolución del último año")
        hist = accion.history(period="1y")
        st.line_chart(hist['Close'])

        # Recomendaciones de analistas
        if st.checkbox("Mostrar recomendaciones de analistas"):
            st.write(accion.recommendations)

    except Exception as e:
        st.error(f"No pudimos encontrar datos para {ticker_input}. Revisa si el ticker es correcto.")

st.info("Nota: Los datos provienen de Yahoo Finance.")
