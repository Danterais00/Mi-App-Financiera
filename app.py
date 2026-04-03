import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Comparador Fundamental Pro", layout="wide")

st.title("⚖️ Comparador de Acciones")
st.write("Introduce los tickers separados por coma (ej: AAPL, TSLA, MSFT)")

# Entrada de múltiples tickers
tickers_input = st.text_input("Tickers:", "AAPL, MSFT, GOOGL").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20] # Límite de 20
    datos_tabla = []
    
    with st.spinner('Obteniendo datos de Yahoo Finance...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                
                # Función para formatear a 2 decimales de forma segura
                def fmt_2(valor):
                    return f"{valor:.2f}" if isinstance(valor, (int, float)) else "N/A"

                # Construimos la fila con el orden que deseas
                fila = {
                    "Ticker": ticker,
                    "Empresa": info.get('longName', 'N/A'), # Primera fila tras el Ticker
                    "Precio": fmt_2(info.get('currentPrice')),
                    "PER (P/E)": fmt_2(info.get('trailingPE')), # Redondeado a 2 decimales
                    "EPS": fmt_2(info.get('trailingEps')),
                    "ROE (%)": f"{info.get('returnOnEquity', 0) * 100:.2f}%" if info.get('returnOnEquity') else "N/A",
                    "ROA (%)": f"{info.get('returnOnAssets', 0) * 100:.2f}%" if info.get('returnOnAssets') else "N/A",
                    "Debt/Equity": fmt_2(info.get('debtToEquity')),
                    "Current Ratio": fmt_2(info.get('currentRatio')),
                    "Quick Ratio": fmt_2(info.get('quickRatio'))
                }
                datos_tabla.append(fila)
            except Exception:
                st.warning(f"No se pudieron obtener datos para: {ticker}")

    if datos_tabla:
        df = pd.DataFrame(datos_tabla)
        df.set_index("Ticker", inplace=True)
        
        # Al transponer (.T), las llaves del diccionario pasan a ser las filas
        df_final = df.T
        
        st.write("### Tabla Comparativa")
        st.table(df_final)
        
        st.download_button(
            label="Descargar tabla como CSV",
            data=df_final.to_csv(),
            file_name="analisis_fundamental.csv",
            mime="text/csv",
        )
else:
    st.info("Ingresa al menos un ticker para comenzar.")
