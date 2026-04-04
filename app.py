import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

st.set_page_config(page_title="Terminal Pro: Top 5 Elite", layout="wide")

st.title("🚀 Terminal de Selección de Activos: TOP 5 Inteligente")
st.write("Ranking optimizado con corrección de sesgo sectorial y desempate por eficiencia.")

tickers_raw = st.text_input("Ingresa Tickers:", "AAPL, MSFT, NVDA, JPM, GS, SHEL, XOM, TSLA, META, GOOGL").upper()

if tickers_raw:
    lista_tickers = [t.strip().replace("BRKB", "BRK-B") for t in tickers_raw.split(",") if t.strip()]
    
    db_fundamentales, db_trends = [], {}
    
    with st.spinner('Ejecutando algoritmos de desempate y limpieza...'):
        for ticker in lista_tickers:
            try:
                tk = yf.Ticker(ticker)
                info = tk.info
                
                # --- EXTRACCIÓN DE DATOS ---
                metrics = {
                    "Ticker": ticker,
                    "Empresa": info.get('longName', 'N/A'),
                    "Precio": info.get('currentPrice'),
                    "PER": info.get('trailingPE'),
                    "PEG": info.get('pegRatio'),
                    "Net Margin": info.get('profitMargins'),
                    "ROE": info.get('returnOnEquity'),
                    "ROA": info.get('returnOnAssets'),
                    "FCF": info.get('freeCashflow'),
                    "DivYield": info.get('dividendYield'),
                    "DebtEquity": info.get('debtToEquity'),
                    "CurrentRatio": info.get('currentRatio'),
                    "QuickRatio": info.get('quickRatio')
                }
                db_fundamentales.append(metrics)
                
                # --- TENDENCIAS (REVENUE/EPS) ---
                df_q = tk.quarterly_financials
                r_pts, e_pts = 0, 0
                if df_q is not None and not df_q.empty:
                    if "Total Revenue" in df_q.index:
                        rev = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                        if len(rev) >= 2 and ((rev.iloc[-1] - rev.iloc[0])/abs(rev.iloc[0])) > 0.05: r_pts = 1
                    if "Basic EPS" in df_q.index:
                        eps = df_q.loc["Basic EPS"].head(5).iloc[::-1]
                        if len(eps) >= 2 and ((eps.iloc[-1] - eps.iloc[0])/abs(eps.iloc[0])) > 0.05: e_pts = 1
                
                db_trends[ticker] = {"r": r_pts, "e": e_pts}
            except: pass

    if db_fundamentales:
        df = pd.DataFrame(db_fundamentales)
        # Promedios omitiendo Ticker y Empresa
        promedios = df.mean(numeric_only=True)
        
        ranking_final = []
        for _, row in df.iterrows():
            ticker = row['Ticker']
            pts_fund = 0
            posibles_fund = 0
            
            # Lista de métricas a comparar (Menor es mejor para Debt y PEG)
            for m in ["PER", "PEG", "Net Margin", "ROE", "ROA", "FCF", "DivYield", "DebtEquity", "CurrentRatio", "QuickRatio"]:
                val = row[m]
                if pd.notna(val) and m in promedios:
                    posibles_fund += 1
                    prom = promedios[m]
                    if m in ["DebtEquity", "PEG"]:
                        if val < prom: pts_fund += 1
                    else:
                        if val > prom: pts_fund += 1
            
            # Score de Crecimiento
            pts_crec = db_trends.get(ticker, {}).get("r", 0) + db_trends.get(ticker, {}).get("e", 0)
            
            # Score Relativo (Solución al sesgo sectorial)
            score_relativo = (pts_fund / posibles_fund) * 100 if posibles_fund > 0 else 0
            
            ranking_final.append({
                "Ticker": ticker,
                "Nombre": row["Empresa"],
                "Pts_Fund": pts_fund,
                "Pts_Crec": pts_crec,
                "Total": pts_fund + pts_crec,
                "NetMargin": row["Net Margin"] if pd.notna(row["Net Margin"]) else -1,
                "Eficiencia": score_relativo
            })

        # --- SECCIÓN 4: TOP 5 CON DESEMPATE ---
        # Ordenamos por: Total (1º), Eficiencia Relativa (2º) y Margen Neto (3º - Desempate final)
        top_5 = sorted(ranking_final, key=lambda x: (x['Total'], x['Eficiencia'], x['NetMargin']), reverse=True)[:5]

        st.divider()
        st.subheader("🏆 4. Selección Elite: TOP 5 Recomendado")
        st.info("Sistema de desempate activo: A igual puntaje, se prioriza la eficiencia relativa y el margen neto.")

        cols = st.columns(5)
        for i, stock in enumerate(top_5):
            with cols[i]:
                st.markdown(f"### #{i+1} {stock['Ticker']}")
                st.caption(stock['Nombre'])
                st.metric("Puntos", f"{stock['Total']}", f"{stock['Eficiencia']:.1f}% Efic.")
                
                with st.expander("Ver Racional"):
                    st.write(f"**1. Análisis Fundamental:**")
                    st.write(f"Superó al promedio en **{stock['Pts_Fund']}** de los indicadores aplicables a su sector.")
                    st.write(f"**2. Análisis de Crecimiento:**")
                    if stock['Pts_Crec'] == 2: st.success("Crecimiento dual: Ingresos y EPS ▲")
                    elif stock['Pts_Crec'] == 1: st.warning("Crecimiento parcial registrado.")
                    else: st.error("Sin momentum de crecimiento actual.")
                    
                    if stock['NetMargin'] > 0:
                        st.write(f"**3. Factor Desempate:**")
                        st.write(f"Margen Neto: **{stock['NetMargin']*100:.2f}%**")
