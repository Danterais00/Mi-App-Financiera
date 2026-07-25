import yfinance as yf
import pandas as pd
import streamlit as st

@st.cache_data(ttl=43200)
def descargar_datos_mercado(lista_tickers):
    datos_fundamentales = []
    datos_tecnicos = []
    datos_revenue = []
    datos_eps = []
    analisis_completo = {}
    fechas_headers = []

    for ticker in lista_tickers:
        try:
            accion = yf.Ticker(ticker)
            info = accion.info
            if info is None: info = {}
        except:
            continue

        p_actual = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        if not p_actual:
            try: p_actual = accion.history(period="2d")['Close'].iloc[-1]
            except: continue
            
        if not p_actual or pd.isna(p_actual): continue

        v_justo = info.get('targetMeanPrice')
        upside = ((v_justo / p_actual) - 1) if p_actual and v_justo else None
        
        gross = info.get('grossProfits')
        rev = info.get('totalRevenue')
        fcf = info.get('freeCashflow')
        mcap = info.get('marketCap')
        
        gross_margin = (gross / rev) if (gross and rev and rev > 0) else None
        fcf_yield = (fcf / mcap) if (fcf and mcap and mcap > 0) else None
        
        # --- EXTRACCIÓN DE LOGO (MOTOR DE GOOGLE) ---
        website = info.get('website')
        domain = None
        if website and isinstance(website, str):
            domain = website.split('//')[-1].split('/')[0].replace('www.', '')
        
        # Usamos el servicio de Google: estable y devuelve un ícono por defecto si no hay logo
        logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128" if domain else "https://www.google.com/s2/favicons?domain=finance.yahoo.com&sz=128"
        # --------------------------------------------
        
        datos_fundamentales.append({
            "Ticker": ticker, "Empresa": info.get('longName', ticker),
            "Precio": p_actual, "Fair Value (Target)": v_justo, "Upside (%)": upside,
            "Beta": info.get('beta'), "Volumen Promedio": info.get('averageVolume'),
            "PER": info.get('trailingPE'), "Forward P/E": info.get('forwardPE'),
            "PEG Ratio": info.get('pegRatio'), "EV/EBITDA": info.get('enterpriseToEbitda'),
            "Consenso (1-5)": info.get('recommendationMean'),
            "Margen Neto (%)": info.get('profitMargins'), "Gross Margin (%)": gross_margin,
            "ROE (%)": info.get('returnOnEquity'), "ROA (%)": info.get('returnOnAssets'),
            "FCF Yield (%)": fcf_yield, "Div Yield (%)": info.get('dividendYield'),
            "Payout Ratio (%)": info.get('payoutRatio'), "Short Interest (%)": info.get('shortPercentOfFloat'),
            "Debt/Equity": (info.get('debtToEquity') / 100) if info.get('debtToEquity') else None, 
            "Current Ratio": info.get('currentRatio'), "Quick Ratio": info.get('quickRatio')
        })

        rsi_val, dist_sma, dist_ath, estado_rsi = None, None, None, "Neutral"
        try:
            hist = accion.history(period="max")
            if len(hist) >= 14:
                close_s = hist['Close']
                ath = close_s.max()
                dist_ath = ((p_actual / ath) - 1) * 100 if ath else None
                if len(hist) >= 200:
                    dist_sma = ((p_actual / close_s.rolling(window=200).mean().iloc[-1]) - 1) * 100
                
                delta = close_s.diff()
                gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                if loss.iloc[-1] != 0: rsi_val = 100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1])))
                else: rsi_val = 100 if gain.iloc[-1] > 0 else 50
                
                if rsi_val < 30: estado_rsi = "Oportunidad (Sobreventa)"
                elif rsi_val > 70: estado_rsi = "Eufórico (Sobrecompra)"
        except: pass
        
        datos_tecnicos.append({"Ticker": ticker, "Dist. Máx Histórico": dist_ath, "RSI (14d)": rsi_val, "Estado RSI": estado_rsi, "Dist. Media 200d": dist_sma})

        icon_r, icon_e = '●', '●'
        try:
            df_q = accion.quarterly_financials
            if df_q is not None and not df_q.empty:
                if not fechas_headers:
                    for idx, d in enumerate(df_q.columns[:5][::-1]):
                        fechas_headers.append(f"Trim {5-idx}<br><small style='color:#888;'>{d.strftime('%m/%y')}</small>")

                if "Total Revenue" in df_q.index:
                    rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                    fila_r = {"Ticker": ticker}
                    for i, v in enumerate(rev_s):
                        if i < len(fechas_headers): fila_r[fechas_headers[i]] = v
                    if len(rev_s) == 5:
                        r_growth = (rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])
                        icon_r = '<span style="color:#2ecca6;">▲</span>' if r_growth > 0.05 else '<span style="color:#ff6b6b;">▼</span>' if r_growth < -0.05 else '<span style="color:#ffd54f;">●</span>'
                    fila_r["Tendencia"] = icon_r
                    datos_revenue.append(fila_r)

                et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                if et_e:
                    eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                    fila_e = {"Ticker": ticker}
                    for i, v in enumerate(eps_s):
                        if i < len(fechas_headers): fila_e[fechas_headers[i]] = v
                    if len(eps_s) == 5:
                        e_growth = (eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])
                        icon_e = '<span style="color:#2ecca6;">▲</span>' if e_growth > 0.05 else '<span style="color:#ff6b6b;">▼</span>' if e_growth < -0.05 else '<span style="color:#ffd54f;">●</span>'
                    fila_e["Tendencia"] = icon_e
                    datos_eps.append(fila_e)
        except: pass

        analisis_completo[ticker] = {
            "nombre": info.get('longName', ticker), "rev_t": icon_r, "eps_t": icon_e,
            "net_margin": info.get('profitMargins', -1), "upside_val": upside,
            "beta_val": info.get('beta', 99), "rsi_val": rsi_val, "dist_sma": dist_sma,
            "logo_url": logo_url # <- Guardamos la URL segura
        }

    return datos_fundamentales, datos_tecnicos, datos_revenue, datos_eps, analisis_completo
