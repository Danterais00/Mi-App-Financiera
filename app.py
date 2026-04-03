import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Comparador Fundamental", layout="wide")

st.title("⚖️ Comparador de Acciones")
st.write("Introduce los tickers separados por coma (ej: AAPL, TSLA, MSFT, NVDA)")

# Entrada de múltiples tickers
tickers_input = st.text_input("Tickers:", "AAPL, MSFT, GOOGL").upper()

if tickers_input:
    # Convertimos el texto en una lista (quitando espacios vacíos)
    lista_tickers = [t.strip() for t in tickers_input.split(",")]
    
    datos_tabla = []
    
    with st.spinner('Obteniendo datos de Yahoo Finance...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                
                # Extraemos solo los datos que pediste
                # Usamos .get() para que si no existe el dato, ponga "N/A"
                fila = {
                    "Ticker": ticker,
                    "Precio": info.get('currentPrice', 'N/A'),
                    "PER (P/E)": info.get('trailingPE', 'N/A'),
                    "EPS": info.get('trailingEps', 'N/A'),
                    "ROE (%)": f"{info.get('returnOnEquity', 0) * 100:.2f}%" if info.get('returnOnEquity') else "N/A",
                    "ROA (%)": f"{info.get('returnOnAssets', 0) * 100:.2f}%" if info.get('returnOnAssets') else "N/A",
                    "Debt/Equity": info.get('debtToEquity', 'N/A'),
                    "Current Ratio": info.get('currentRatio', 'N/A'),
                    "Quick Ratio": info.get('quickRatio', 'N/A')
                }
                datos_tabla.append(fila)
            except Exception:
                st.warning(f"No se pudieron obtener datos para: {ticker}")

    if datos_tabla:
        # Creamos la tabla
        df = pd.DataFrame(datos_tabla)
        
        # Invertimos la tabla (Transponer) para que los Tickers sean las columnas
        # y los indicadores sean las filas, como pediste.
        df.set_index("Ticker", inplace=True)
        df_final = df.T
        
        st.write("### Tabla Comparativa")
        st.table(df_final) # st.table muestra una tabla estática y limpia
        
        # Botón extra por si quieres descargar los datos a Excel/CSV
        st.download_button(
            label="Descargar tabla como CSV",
            data=df_final.to_csv(),
            file_name="comparativa_financiera.csv",
            mime="text/csv",
        )
else:
    st.info("Ingresa al menos un ticker para comenzar.")
