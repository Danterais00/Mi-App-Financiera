import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Analizador Premium", layout="wide")

st.title("📊 Comparador con Formato Condicional")
st.write("Los valores de **PER** por encima del promedio se resaltarán en **verde**.")

tickers_input = st.text_input("Tickers (separados por coma):", "AAPL, MSFT, GOOGL, NVDA").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20]
    datos_tabla = []
    
    with st.spinner('Procesando datos...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                
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
        # 1. Crear DataFrame y Transponer
        df = pd.DataFrame(datos_tabla)
        df.set_index("Ticker", inplace=True)
        df_final = df.T

        # 2. Calcular el PROMEDIO (solo filas numéricas)
        filas_numericas = df_final.index.drop("Empresa")
        df_final.loc[filas_numericas, "PROMEDIO"] = df_final.loc[filas_numericas].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        # 3. Guardar el valor del promedio del PER para la comparación posterior
        avg_per = df_final.loc["PER (P/E)", "PROMEDIO"]

        # 4. Construir la tabla manualmente en HTML para tener control total del diseño
        html_tabla = '<table style="width:100%; border-collapse: collapse; text-align: center; font-family: sans-serif;">'
        
        # Encabezados (Tickers)
        html_tabla += '<tr style="background-color: #f0f2f6;">'
        html_tabla += '<th style="border: 1px solid #ddd; padding: 12px;">Indicador</th>'
        for col in df_final.columns:
            html_tabla += f'<th style="border: 1px solid #ddd; padding: 12px;">{col}</th>'
        html_tabla += '</tr>'

        # Filas de datos
        for nombre_fila in df_final.index:
            html_tabla += '<tr>'
            html_tabla += f'<td style="border: 1px solid #ddd; padding: 10px; font-weight: bold; background-color: #fafafa;">{nombre_fila}</td>'
            
            for nombre_col in df_final.columns:
                valor = df_final.loc[nombre_fila, nombre_col]
                estilo_celda = 'border: 1px solid #ddd; padding: 10px;'
                
                # --- LÓGICA DE FORMATO ---
                
                # A. Formato para nombre de Empresa (Negrita)
                if nombre_fila == "Empresa":
                    valor_display = f"<b>{valor}</b>"
                
                # B. Formato para PER (Color Verde si > Promedio)
                elif nombre_fila == "PER (P/E)":
                    try:
                        val_num = float(valor)
                        # Solo pintamos las columnas de Tickers, no la de PROMEDIO
                        if nombre_col != "PROMEDIO" and val_num > avg_per:
                            estilo_celda += 'background-color: #c8e6c9; font-weight: bold;' # Verde claro
                        valor_display = f"{val_num:.2f}"
                    except:
                        valor_display = "-"

                # C. Formato para porcentajes
                elif "%" in nombre_fila:
                    try:
                        valor_display = f"{float(valor) * 100:.2f}%"
                    except:
                        valor_display = "-"
                
                # D. Formato para el resto de números
                else:
                    try:
                        valor_display = f"{float(valor):.2f}"
                    except:
                        valor_display = str(valor) if valor else "-"

                html_tabla += f'<td style="{estilo_celda}">{valor_display}</td>'
            html_tabla += '</tr>'
        
        html_tabla += '</table>'

        # 5. Mostrar la tabla
        st.write("### Tabla Comparativa de Fundamentales")
        st.write(html_tabla, unsafe_allow_html=True)
        
        st.download_button(
            label="Descargar datos (CSV)",
            data=df_final.to_csv(),
            file_name="analisis_comparativo.csv",
            mime="text/csv",
        )
else:
    st.info("Ingresa los tickers para comenzar el análisis.")
