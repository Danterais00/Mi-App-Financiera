import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Comparador Fundamental Pro", layout="wide")

st.title("⚖️ Comparador de Acciones con Promedios")
st.write("Introduce los tickers separados por coma (ej: AAPL, TSLA, MSFT)")

tickers_input = st.text_input("Tickers:", "AAPL, MSFT, GOOGL").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20]
    datos_tabla = []
    
    with st.spinner('Calculando datos y promedios...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                
                # Guardamos los datos como NÚMEROS (float) para poder promediar
                fila = {
                    "Ticker": ticker,
                    "Empresa": info.get('longName', 'N/A'),
                    "Precio": info.get('currentPrice'),
                    "PER (P/E)": info.get('trailingPE'),
                    "EPS": info.get('trailingEps'),
                    "ROE (%)": info.get('returnOnEquity'),
                    "ROA (%)": info.get('returnOnAssets'),
                    "Debt/Equity": info.get('debtToEquity'),
                    "Current Ratio": info.get('currentRatio'),
                    "Quick Ratio": info.get('quickRatio')
                }
                datos_tabla.append(fila)
            except Exception:
                st.warning(f"No se pudieron obtener datos para: {ticker}")

    if datos_tabla:
        # 1. Crear el DataFrame y Transponer
        df = pd.DataFrame(datos_tabla)
        df.set_index("Ticker", inplace=True)
        df_final = df.T

        # 2. Calcular el PROMEDIO
        # Solo calculamos promedio para las filas que son numéricas (todas menos "Empresa")
        filas_numericas = df_final.index.drop("Empresa")
        df_final.loc[filas_numericas, "PROMEDIO"] = df_final.loc[filas_numericas].mean(axis=1)
        
        # 3. Formatear la tabla para la vista
        def formatear_valor(valor, nombre_fila):
            if pd.isna(valor) or valor == "N/A":
                return "-"
            if nombre_fila == "Empresa":
                # Aplicamos NEGRITA con Markdown (HTML)
                return f"**{valor}**"
            if "%" in nombre_fila:
                return f"{valor * 100:.2f}%"
            return f"{valor:.2f}"

        # Aplicamos el formato a cada celda
        for fila in df_final.index:
            df_final.loc[fila] = df_final.loc[fila].apply(lambda x: formatear_valor(x, fila))

        # 4. Mostrar la tabla con estilo
        st.write("### Tabla Comparativa")
        
        # Usamos un poco de CSS para CENTRAR todo el texto de la tabla
        st.markdown("""
            <style>
            .stTable td {
                text-align: center !important;
            }
            .stTable th {
                text-align: center !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Mostramos la tabla. Usamos st.write(df_final.to_html(escape=False)) 
        # para que reconozca las negritas del nombre
        st.write(df_final.to_html(escape=False, justify='center'), unsafe_allow_html=True)
        
        st.download_button(
            label="Descargar datos (CSV)",
            data=df_final.to_csv(),
            file_name="analisis_con_promedios.csv",
            mime="text/csv",
        )
else:
    st.info("Ingresa tickers para generar la comparativa.")
