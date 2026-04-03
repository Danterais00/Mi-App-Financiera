import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Analizador Fundamental Premium", layout="wide")

st.title("📊 Comparador de Salud Financiera")
st.write("Celdas en **verde** indican valores que superan (o son mejores) que el promedio del grupo.")

tickers_input = st.text_input("Tickers (separados por coma):", "AAPL, MSFT, GOOGL, NVDA, AMZN").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20]
    datos_tabla = []
    
    with st.spinner('Analizando mercado...'):
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
                st.warning(f"Error con {ticker}")

    if datos_tabla:
        df = pd.DataFrame(datos_tabla)
        df.set_index("Ticker", inplace=True)
        df_final = df.T

        # 1. Calcular PROMEDIO (ignora errores de texto)
        filas_numericas = df_final.index.drop("Empresa")
        df_final.loc[filas_numericas, "PROMEDIO"] = df_final.loc[filas_numericas].apply(pd.to_numeric, errors='coerce').mean(axis=1)
        
        # 2. Generar HTML
        html_tabla = '<table style="width:100%; border-collapse: collapse; text-align: center; font-family: sans-serif;">'
        
        # Encabezados
        html_tabla += '<tr style="background-color: #f0f2f6;">'
        html_tabla += '<th style="border: 1px solid #ddd; padding: 12px;">Indicador</th>'
        for col in df_final.columns:
            html_tabla += f'<th style="border: 1px solid #ddd; padding: 12px;">{col}</th>'
        html_tabla += '</tr>'

        # Filas
        for nombre_fila in df_final.index:
            html_tabla += '<tr>'
            html_tabla += f'<td style="border: 1px solid #ddd; padding: 10px; font-weight: bold; background-color: #fafafa;">{nombre_fila}</td>'
            
            promedio_fila = df_final.loc[nombre_fila, "PROMEDIO"]

            for nombre_col in df_final.columns:
                valor = df_final.loc[nombre_fila, nombre_col]
                estilo_celda = 'border: 1px solid #ddd; padding: 10px;'
                
                # Formateo visual inicial
                if nombre_fila == "Empresa":
                    valor_display = f"<b>{valor}</b>"
                else:
                    try:
                        val_num = float(valor)
                        
                        # --- LÓGICA DE COLORES ---
                        if nombre_col != "PROMEDIO":
                            # Caso A: Menor es mejor (Deuda)
                            if nombre_fila == "Debt/Equity":
                                if val_num < promedio_fila:
                                    estilo_celda += 'background-color: #c8e6c9; font-weight: bold;'
                            
                            # Caso B: Mayor es mejor (El resto de indicadores)
                            elif nombre_fila in ["PER (P/E)", "EPS", "ROE (%)", "ROA (%)", "Current Ratio", "Quick Ratio"]:
                                if val_num > promedio_fila:
                                    estilo_celda += 'background-color: #c8e6c9; font-weight: bold;'
                        
                        # Formato de salida
                        if "%" in nombre_fila:
                            valor_display = f"{val_num * 100:.2f}%"
                        else:
                            valor_display = f"{val_num:.2f}"
                    except:
                        valor_display = "-"

                html_tabla += f'<td style="{estilo_celda}">{valor_display}</td>'
            html_tabla += '</tr>'
        
        html_tabla += '</table>'

        st.write("### Resultados del Análisis")
        st.write(html_tabla, unsafe_allow_html=True)
        
        st.download_button("Descargar CSV", df_final.to_csv(), "analisis.csv", "text/csv")
else:
    st.info("Ingresa los tickers para comparar.")
