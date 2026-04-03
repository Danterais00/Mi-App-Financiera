import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

st.set_page_config(page_title="Terminal de Análisis Pro", layout="wide")

st.title("🚀 Terminal de Inversión: Selección, Auditoría y Noticias")
st.write("Análisis integral: Fundamentales, Tendencias y Pulso del Mercado en tiempo real.")

tickers_input = st.text_input("Tickers (separados por coma):", "AAPL, MSFT, NVDA, GOOGL, AMZN, TSLA").upper()

if tickers_input:
    lista_tickers = [t.strip() for t in tickers_input.split(",")][:20]
    
    datos_fundamentales, datos_revenue, datos_eps = [], [], []
    noticias_dict = {} # Para guardar las noticias de cada ticker
    analisis_completo = {}
    ranking_puntos = {ticker: 0 for ticker in lista_tickers}
    
    with st.spinner('Extrayendo datos y últimas noticias...'):
        for ticker in lista_tickers:
            try:
                accion = yf.Ticker(ticker)
                info = accion.info
                
                # --- 1. FUNDAMENTALES ---
                fila_fun = {
                    "Ticker": ticker, "Empresa": info.get('longName', 'N/A'),
                    "Precio": info.get('currentPrice'), "PER (P/E)": info.get('trailingPE'),
                    "EPS": info.get('trailingEps'), "ROE (%)": info.get('returnOnEquity'),
                    "ROA (%)": info.get('returnOnAssets'), "Debt/Equity": info.get('debtToEquity'),
                    "Current Ratio": info.get('currentRatio'), "Quick Ratio": info.get('quickRatio')
                }
                datos_fundamentales.append(fila_fun)

                # --- 2. REVENUE Y EPS ---
                df_q = accion.quarterly_financials
                rev_growth, eps_growth = 0, 0
                nombres_trimestres = ["4 Trim. atrás", "3 Trim. atrás", "2 Trim. atrás", "1 Trim. atrás", "Último Trim."]
                
                if df_q is not None and not df_q.empty:
                    if "Total Revenue" in df_q.index:
                        rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        fila_rev = {"Ticker": ticker}
                        for i, value in enumerate(rev_s):
                            if i < len(nombres_trimestres): fila_rev[nombres_trimestres[i]] = value
                        fila_rev["TTM"] = info.get('totalRevenue')
                        datos_revenue.append(fila_rev)
                        if len(rev_s) >= 2: rev_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) * 100
                    
                    et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                    if et_e:
                        eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                        fila_eps = {"Ticker": ticker}
                        for i, value in enumerate(eps_s):
                            if i < len(nombres_trimestres): fila_eps[nombres_trimestres[i]] = value
                        fila_eps["TTM"] = info.get('trailingEps')
                        datos_eps.append(fila_eps)
                        if len(eps_s) >= 2: eps_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) * 100

                # --- 3. NOTICIAS (NUEVO) ---
                noticias_dict[ticker] = accion.news[:3] # Tomamos las 3 noticias más recientes

                analisis_completo[ticker] = {"nombre": info.get('longName', ticker), "rev_growth": rev_growth, "eps_growth": eps_growth}
            except Exception: pass

    # (Funciones de formateo y Tablas 1, 2 y 3 se mantienen igual...)
    # [Omitido por brevedad, usa la lógica del código anterior para las tablas]
    
    # --- ASUMIREMOS QUE AQUÍ TERMINAN LAS TABLAS Y EL RANKING ---

    # --- SECCIÓN 5: MONITOR DE NOTICIAS ---
    st.divider()
    st.write("### 📰 5. Monitor de Noticias Recientes")
    st.write("Últimos titulares de fuentes financieras (Reuters, Yahoo, Bloomberg, etc.)")

    if noticias_dict:
        # Creamos pestañas para navegar entre las noticias de cada empresa
        tabs = st.tabs(lista_tickers)
        
        for i, ticker in enumerate(lista_tickers):
            with tabs[i]:
                noticias = noticias_dict.get(ticker, [])
                if not noticias:
                    st.write(f"No se encontraron noticias recientes para {ticker}.")
                else:
                    for n in noticias:
                        # Estilo de tarjeta para cada noticia
                        with st.container():
                            col_n1, col_n2 = st.columns([1, 4])
                            with col_n1:
                                st.caption(f"📌 {n.get('publisher', 'Fuente desconocida')}")
                            with col_n2:
                                st.markdown(f"**[{n.get('title')}]({n.get('link')})**")
                                # Opcional: mostrar fecha si está disponible (convertida de timestamp)
                            st.write("---")
    else:
        st.info("Ingresa tickers para ver las noticias correspondientes.")

    # --- CIERRE DE LA APP ---
else:
    st.info("Ingresa los tickers para iniciar el análisis completo.")
