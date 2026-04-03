import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Analizador Premium - Ranking", layout="wide")

st.title("🏆 Ranking de Selección de Acciones")
st.write("El ranking se basa en cuántos indicadores superan el promedio del grupo analizado.")

tickers_input = st.text_input("Tickers (separados por coma):", "AAPL, MSFT, GOOGL, NVDA, AMZN").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20]
    datos_tabla = []
    # Diccionario para contar los puntos (celdas verdes) de cada empresa
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    
    with st.spinner('Realizando análisis comparativo...'):
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
                st.warning(f"No se pudieron obtener datos para {ticker}")

    if datos_tabla:
        df = pd.DataFrame(datos_tabla)
        df.set_index("Ticker", inplace=True)
        df_final = df.T

        # 1. Calcular PROMEDIO
        filas_numericas = df_final.index.drop("Empresa")
        df_final.loc[filas_numericas, "PROMEDIO"] = df_final.loc[filas_numericas].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        # 2. Generar HTML y Contar Puntos
        html_tabla = '<table style="width:100%; border-collapse: collapse; text-align: center; font-family: sans-serif;">'
        html_tabla += '<tr style="background-color: #f0f2f6;"><th style="border: 1px solid #ddd; padding: 12px;">Indicador</th>'
        for col in df_final.columns:
            html_tabla += f'<th style="border: 1px solid #ddd; padding: 12px;">{col}</th>'
        html_tabla += '</tr>'

        for nombre_fila in df_final.index:
            html_tabla += '<tr>'
            html_tabla += f'<td style="border: 1px solid #ddd; padding: 10px; font-weight: bold; background-color: #fafafa;">{nombre_fila}</td>'
            
            promedio_fila = df_final.loc[nombre_fila, "PROMEDIO"]

            for nombre_col in df_final.columns:
                valor = df_final.loc[nombre_fila, nombre_col]
                estilo_celda = 'border: 1px solid #ddd; padding: 10px;'
                
                if nombre_fila == "Empresa":
                    valor_display = f"<b>{valor}</b>"
                else:
                    try:
                        val_num = float(valor)
                        # Lógica de colores y SUMA DE PUNTOS
                        es_verde = False
                        if nombre_col != "PROMEDIO":
                            if nombre_fila == "Debt/Equity":
                                if val_num < promedio_fila: es_verde = True
                            elif nombre_fila in ["PER (P/E)", "EPS", "ROE (%)", "ROA (%)", "Current Ratio", "Quick Ratio"]:
                                if val_num > promedio_fila: es_verde = True
                            
                            if es_verde:
                                estilo_celda += 'background-color: #c8e6c9; font-weight: bold;'
                                ranking_puntos[nombre_col] += 1 # Sumamos punto al ticker
                        
                        valor_display = f"{val_num * 100:.2f}%" if "%" in nombre_fila else f"{val_num:.2f}"
                    except:
                        valor_display = "-"

                html_tabla += f'<td style="{estilo_celda}">{valor_display}</td>'
            html_tabla += '</tr>'
        html_tabla += '</table>'

        # Mostrar Tabla
        st.write("### Tabla Comparativa")
        st.write(html_tabla, unsafe_allow_html=True)

        # 3. RESUMEN Y RANKING
        st.divider()
        st.write("### 🥇 Resumen de Selección")
        
        # Ordenar el ranking de mayor a menor
        ranking_ordenado = sorted(ranking_puntos.items(), key=lambda x: x[1], reverse=True)
        
        # Mostrar conclusión principal
        mejor_empresa = ranking_ordenado[0][0]
        puntos_mejor = ranking_ordenado[0][1]
        
        st.success(f"Basado en los indicadores seleccionados, la mejor opción de inversión actual es **{mejor_empresa}** con **{puntos_mejor} de 7** indicadores favorables.")

        # Mostrar lista completa
        st.write("**Ranking por cantidad de indicadores positivos (Celdas Verdes):**")
        for ticker, puntos in ranking_ordenado:
            # Una barra de progreso visual para cada empresa
            st.write(f"- **{ticker}**: {puntos} celdas verdes")
            st.progress(puntos / 7)

        st.download_button("Descargar CSV", df_final.to_csv(), "analisis.csv", "text/csv")
else:
    st.info("Ingresa los tickers para calcular el ranking.")
