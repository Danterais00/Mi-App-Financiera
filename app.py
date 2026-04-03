import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Analizador Financiero", layout="centered")

st.title("📈 Mi Terminal de Inversiones")

ticker_input = st.text_input("Ticker (ej: NVDA, AAPL, MSFT)", "NVDA").upper()

if ticker_input:
    try:
        # Creamos el objeto de la acción
        accion = yf.Ticker(ticker_input)
        
        # Intentamos obtener el precio de una forma más directa y rápida
        # Esto falla menos que el método .info
        hist = accion.history(period="5d")
        
        if not hist.empty:
            precio_actual = hist['Close'].iloc[-1]
            precio_anterior = hist['Close'].iloc[-2]
            cambio = precio_actual - precio_anterior
            porcentaje = (cambio / precio_anterior) * 100

            # Mostrar métricas principales
            st.header(f"Resultados para: {ticker_input}")
            col1, col2 = st.columns(2)
            col1.metric("Precio Actual", f"${precio_actual:.2f}")
            col2.metric("Variación diaria", f"{cambio:.2f}", f"{porcentaje:.2f}%")

            # Gráfico de un año
            st.write("### Histórico del último año")
            hist_year = accion.history(period="1y")
            st.line_chart(hist_year['Close'])
            
            # Datos adicionales (Si Yahoo los permite)
            with st.expander("Ver detalles avanzados"):
                info = accion.info
                st.write(f"**Sector:** {info.get('sector', 'N/A')}")
                st.write(f"**Resumen:** {info.get('longBusinessSummary', 'No disponible')}")
        else:
            st.error("Yahoo Finance no devolvió datos. Intenta con otro ticker o espera unos minutos.")

    except Exception as e:
        st.error(f"Error técnico: {e}")

st.info("Tip: Si no carga, intenta refrescar la página. A veces Yahoo bloquea temporalmente la conexión.")
