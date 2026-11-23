import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

def _buscar_fila(df, candidatos):
    if df is None or df.empty:
        return None
    for nombre in candidatos:
        if nombre in df.index:
            s = pd.to_numeric(df.loc[nombre], errors='coerce').dropna()
            if not s.empty:
                return s
    return None

@st.cache_data(ttl=21600)
def descargar_datos_mercado(lista_tickers, _schema_version="v3_diag"):
    datos_fundamentales = []
    datos_tecnicos = []
    datos_revenue = []
    datos_eps = []
    analisis_completo = {}
    fechas_headers = []

    # Descargar SPY 1y una sola vez para calcular Beta de respaldo si info falla
    retornos_spy = None
    try:
        hist_spy = yf.Ticker("SPY").history(period="1y")['Close']
        if len(hist_spy) > 60:
            retornos_spy = hist_spy.pct_change().dropna()
    except:
        pass

    for ticker in lista_tickers:
        try:
            accion = yf.Ticker(ticker)
            info = accion.info
            if not isinstance(info, dict):
                info = {}
        except:
            accion = yf.Ticker(ticker)
            info = {}

        # Historial completo (sirve para precio, técnico, volumen y beta)
        try:
            hist = accion.history(period="max")
        except:
            hist = pd.DataFrame()

        p_actual = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        if (not p_actual or pd.isna(p_actual)) and not hist.empty:
            p_actual = float(hist['Close'].iloc[-1])

        if not p_actual or pd.isna(p_actual):
            continue

        # Estados contables trimestrales (respaldo matemático si info viene bloqueado)
        try:
            df_q = accion.quarterly_financials
        except:
            df_q = pd.DataFrame()
        try:
            df_bs = accion.quarterly_balance_sheet
        except:
            df_bs = pd.DataFrame()
        try:
            df_cf = accion.quarterly_cashflow
        except:
            df_cf = pd.DataFrame()

        # Series contables TTM (últimos 4 trimestres) y último balance
        rev_s_ttm = _buscar_fila(df_q, ["Total Revenue", "Operating Revenue"])
        gp_s_ttm = _buscar_fila(df_q, ["Gross Profit"])
        ni_s_ttm = _buscar_fila(df_q, ["Net Income", "Net Income Common Stockholders"])
        eps_s_ttm = _buscar_fila(df_q, ["Basic EPS", "Diluted EPS", "BasicEps"])
        fcf_s_ttm = _buscar_fila(df_cf, ["Free Cash Flow"])

        rev_ttm = float(rev_s_ttm.head(4).sum()) if rev_s_ttm is not None and len(rev_s_ttm) >= 1 else None
        gp_ttm = float(gp_s_ttm.head(4).sum()) if gp_s_ttm is not None and len(gp_s_ttm) >= 1 else None
        ni_ttm = float(ni_s_ttm.head(4).sum()) if ni_s_ttm is not None and len(ni_s_ttm) >= 1 else None
        eps_ttm = float(eps_s_ttm.head(4).sum()) if eps_s_ttm is not None and len(eps_s_ttm) >= 4 else None
        fcf_ttm = float(fcf_s_ttm.head(4).sum()) if fcf_s_ttm is not None and len(fcf_s_ttm) >= 1 else None

        eq_s = _buscar_fila(df_bs, ["Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"])
        assets_s = _buscar_fila(df_bs, ["Total Assets"])
        debt_s = _buscar_fila(df_bs, ["Total Debt", "Long Term Debt"])
        ca_s = _buscar_fila(df_bs, ["Current Assets"])
        cl_s = _buscar_fila(df_bs, ["Current Liabilities"])
        inv_s = _buscar_fila(df_bs, ["Inventory"])
        shares_s = _buscar_fila(df_bs, ["Ordinary Shares Number", "Share Issued"])

        equity = float(eq_s.iloc[0]) if eq_s is not None else None
        assets = float(assets_s.iloc[0]) if assets_s is not None else None
        debt = float(debt_s.iloc[0]) if debt_s is not None else None
        curr_assets = float(ca_s.iloc[0]) if ca_s is not None else None
        curr_liab = float(cl_s.iloc[0]) if cl_s is not None else None
        inventory = float(inv_s.iloc[0]) if inv_s is not None else 0.0
        shares = float(shares_s.iloc[0]) if shares_s is not None else None

        # --- MÉTRICAS CON FALLBACK AUTOMÁTICO ---
        v_justo = info.get('targetMeanPrice')
        upside = ((v_justo / p_actual) - 1) if p_actual and v_justo else None

        # Volumen promedio
        vol_prom = info.get('averageVolume')
        if not vol_prom and not hist.empty and 'Volume' in hist.columns:
            vol_prom = float(hist['Volume'].tail(20).mean())

        # Beta
        beta_val = info.get('beta')
        if beta_val is None and retornos_spy is not None and len(hist) > 60:
            try:
                ret_act = hist['Close'].tail(252).pct_change().dropna()
                df_align = pd.concat([ret_act, retornos_spy], axis=1, join='inner').dropna()
                if len(df_align) > 40:
                    cov = np.cov(df_align.iloc[:, 0], df_align.iloc[:, 1])[0][1]
                    var_m = np.var(df_align.iloc[:, 1])
                    if var_m > 0:
                        beta_val = round(float(cov / var_m), 2)
            except:
                pass

        # PER
        per_val = info.get('trailingPE')
        if per_val is None and eps_ttm and eps_ttm > 0:
            per_val = p_actual / eps_ttm

        # Márgenes
        margen_neto = info.get('profitMargins')
        if margen_neto is None and ni_ttm is not None and rev_ttm and rev_ttm > 0:
            margen_neto = ni_ttm / rev_ttm

        gross = info.get('grossProfits')
        rev = info.get('totalRevenue')
        gross_margin = (gross / rev) if (gross and rev and rev > 0) else None
        if gross_margin is None and gp_ttm is not None and rev_ttm and rev_ttm > 0:
            gross_margin = gp_ttm / rev_ttm

        # ROE y ROA
        roe_val = info.get('returnOnEquity')
        if roe_val is None and ni_ttm is not None and equity and equity > 0:
            roe_val = ni_ttm / equity

        roa_val = info.get('returnOnAssets')
        if roa_val is None and ni_ttm is not None and assets and assets > 0:
            roa_val = ni_ttm / assets

        # FCF Yield
        fcf = info.get('freeCashflow') or fcf_ttm
        mcap = info.get('marketCap') or (shares * p_actual if shares and p_actual else None)
        fcf_yield = (fcf / mcap) if (fcf is not None and mcap and mcap > 0) else None

        # Solvencia y Liquidez
        de_val = (info.get('debtToEquity') / 100) if info.get('debtToEquity') is not None else None
        if de_val is None and debt is not None and equity and equity > 0:
            de_val = debt / equity

        cr_val = info.get('currentRatio')
        if cr_val is None and curr_assets is not None and curr_liab and curr_liab > 0:
            cr_val = curr_assets / curr_liab

        qr_val = info.get('quickRatio')
        if qr_val is None and curr_assets is not None and curr_liab and curr_liab > 0:
            qr_val = (curr_assets - inventory) / curr_liab

        # --- EXTRACCIÓN DE LOGO (MOTOR DE GOOGLE) ---
        website = info.get('website')
        domain = None
        if website and isinstance(website, str):
            domain = website.split('//')[-1].split('/')[0].replace('www.', '')
        logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128" if domain else "https://www.google.com/s2/favicons?domain=finance.yahoo.com&sz=128"

        datos_fundamentales.append({
            "Ticker": ticker, "Empresa": info.get('longName', ticker),
            "Precio": p_actual, "Fair Value (Target)": v_justo, "Upside (%)": upside,
            "Beta": beta_val, "Volumen Promedio": vol_prom,
            "PER": per_val, "Forward P/E": info.get('forwardPE'),
            "PEG Ratio": info.get('pegRatio'), "EV/EBITDA": info.get('enterpriseToEbitda'),
            "Consenso (1-5)": info.get('recommendationMean'),
            "Margen Neto (%)": margen_neto, "Gross Margin (%)": gross_margin,
            "ROE (%)": roe_val, "ROA (%)": roa_val,
            "FCF Yield (%)": fcf_yield, "Div Yield (%)": info.get('dividendYield'),
            "Payout Ratio (%)": info.get('payoutRatio'), "Short Interest (%)": info.get('shortPercentOfFloat'),
            "Debt/Equity": de_val,
            "Current Ratio": cr_val, "Quick Ratio": qr_val
        })

        # --- ANÁLISIS TÉCNICO ---
        rsi_val, dist_sma, dist_ath, estado_rsi = None, None, None, "Neutral"
        try:
            if len(hist) >= 14:
                close_s = hist['Close']
                ath = close_s.max()
                dist_ath = ((p_actual / ath) - 1) * 100 if ath else None
                if len(hist) >= 200:
                    dist_sma = ((p_actual / close_s.rolling(window=200).mean().iloc[-1]) - 1) * 100
                
                delta = close_s.diff()
                gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                if loss.iloc[-1] != 0:
                    rsi_val = 100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1])))
                else:
                    rsi_val = 100 if gain.iloc[-1] > 0 else 50
                
                if rsi_val < 30: estado_rsi = "Oportunidad (Sobreventa)"
                elif rsi_val > 70: estado_rsi = "Eufórico (Sobrecompra)"
        except:
            pass
        
        datos_tecnicos.append({"Ticker": ticker, "Dist. Máx Histórico": dist_ath, "RSI (14d)": rsi_val, "Estado RSI": estado_rsi, "Dist. Media 200d": dist_sma})

        # --- EVOLUCIÓN FINANCIERA TRIMESTRAL ---
        icon_r, icon_e = '●', '●'
        try:
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
        except:
            pass

        analisis_completo[ticker] = {
            "nombre": info.get('longName', ticker), "rev_t": icon_r, "eps_t": icon_e,
            "net_margin": margen_neto if margen_neto is not None else -1, "upside_val": upside,
            "beta_val": beta_val if beta_val is not None else 99, "rsi_val": rsi_val, "dist_sma": dist_sma,
            "logo_url": logo_url
        }

    # --- DIAGNÓSTICO QUIRÚRGICO TEMPORAL (ELIMINAR TRAS EL TEST) ---
    if lista_tickers:
        try:
            t_diag = lista_tickers[0]
            acc_diag = yf.Ticker(t_diag)
            inf_diag = acc_diag.info or {}
            qf_diag = acc_diag.quarterly_financials
            bs_diag = acc_diag.quarterly_balance_sheet
            cf_diag = acc_diag.quarterly_cashflow
            with st.expander(f"🔬 Diagnóstico Técnico en Vivo ({t_diag})", expanded=True):
                st.write("**1. Versión yfinance:**", yf.__version__)
                st.write("**2. Claves recibidas en `ticker.info`:**", len(inf_diag), list(inf_diag.keys())[:15])
                st.write("**3. `quarterly_financials` vacío?:**", qf_diag is None or qf_diag.empty, "| Filas:", list(qf_diag.index)[:10] if qf_diag is not None and not qf_diag.empty else [])
                st.write("**4. `quarterly_balance_sheet` vacío?:**", bs_diag is None or bs_diag.empty, "| Filas:", list(bs_diag.index)[:10] if bs_diag is not None and not bs_diag.empty else [])
                st.write("**5. `quarterly_cashflow` vacío?:**", cf_diag is None or cf_diag.empty, "| Filas:", list(cf_diag.index)[:10] if cf_diag is not None and not cf_diag.empty else [])
                if datos_fundamentales:
                    st.write("**6. Diccionario calculado por extractor.py:**", datos_fundamentales[0])
        except Exception as e_diag:
            st.error(f"Error en diagnóstico: {e_diag}")

    return datos_fundamentales, datos_tecnicos, datos_revenue, datos_eps, analisis_completo
