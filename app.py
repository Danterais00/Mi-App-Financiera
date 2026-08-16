import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime
import urllib.request
import xml.etree.ElementTree as ET
import json

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS SMARTINVEST PRO
st.set_page_config(
    page_title="SmartInvest AI - Terminal Pro Nivel 5",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZADO (SMARTINVEST DARK PRO) ---
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Urbanist:wght@600;700;800&display=swap');

    :root {
        --bg-main: #0a0a0f;
        --bg-card: #14141f;
        --bg-input: #1c1c2b;
        --border-color: #252538;
        --text-main: #f3f4f6;
        --text-muted: #9ca3af;
        --primary: #10b981;
        --danger: #ef4444;
        --blue: #3b82f6;
        --warning: #f59e0b;
    }

    .stApp {
        background-color: var(--bg-main);
        font-family: 'Inter', sans-serif;
        color: var(--text-main);
    }

    #MainMenu, footer, header {visibility: hidden;}

    .smart-header {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 16px 20px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .smart-header h1 {
        font-family: 'Urbanist', sans-serif;
        font-size: 24px;
        font-weight: 800;
        color: #fff;
        margin: 0;
    }
    .smart-header h1 span { color: var(--blue); }

    .ribbon-title {
        font-size: 13px;
        font-weight: 700;
        color: var(--blue);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 15px;
        margin-bottom: 10px;
    }
    .ribbon-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 20px;
    }
    .ribbon-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 12px 14px;
        display: flex;
        flex-direction: column;
    }
    .ribbon-card .lbl { font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 700; }
    .ribbon-card .val { font-size: 15px; font-weight: 800; font-family: 'Urbanist'; color: #fff; margin-top: 3px; }
    .ribbon-card .sub { font-size: 11px; font-weight: 700; margin-top: 2px; }

    .top-card {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .top-card-header { display: flex; justify-content: space-between; align-items: center; }
    .ticker-title { font-family: 'Urbanist'; font-size: 20px; font-weight: 800; color: #fff; }
    .score-badge { background: rgba(16, 185, 129, 0.15); border: 1px solid var(--primary); color: var(--primary); font-weight: 800; font-size: 12px; padding: 2px 8px; border-radius: 6px; }

    .rag-pill { font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px; display: inline-block; margin: 6px 0; }
    .rag-strong-buy { background: rgba(16, 185, 129, 0.2); color: var(--primary); border: 1px solid var(--primary); }
    .rag-ideal { background: rgba(59, 130, 246, 0.2); color: var(--blue); border: 1px solid var(--blue); }
    .rag-caution { background: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }
    .rag-avoid { background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }

    .smart-table { width: 100%; border-collapse: separate; border-spacing: 0 4px; margin-top: 10px; }
    .smart-table th { color: var(--text-muted); font-size: 11px; text-transform: uppercase; font-weight: 700; padding: 8px 10px; border-bottom: 1px solid var(--border-color); text-align: center; }
    .smart-table td { background-color: var(--bg-card); padding: 10px; font-size: 12px; border-top: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color); text-align: center; }
    .smart-table td:first-child { border-left: 1px solid var(--border-color); border-radius: 6px 0 0 6px; font-weight: 700; color: #fff; }
    .smart-table td:last-child { border-right: 1px solid var(--border-color); border-radius: 0 6px 6px 0; }
    .cell-highlight { background-color: rgba(16, 185, 129, 0.18) !important; color: #a7f3d0 !important; font-weight: 700; }
    .row-promedio td { background-color: #1c1c30 !important; color: var(--warning) !important; font-weight: 700; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

TOOLTIPS = {
    "Net Income": "Beneficio neto real tras restar gastos e impuestos.",
    "Cost of Revenue": "Gastos directos para fabricar o entregar el producto.",
    "PER": "0-10: Bajo / 10-17: Moderado / 17-25: Alto / >25: Crecimiento Agresivo.",
    "Margen Neto (%)": "Porcentaje de ventas que se convierte en ganancia limpia.",
    "ROE (%)": "Rentabilidad sobre el capital de los accionistas.",
    "ROA (%)": "Rentabilidad sobre el total de activos de la empresa.",
    "Free Cash Flow": "Caja libre tras capex; disponible para dividendos/recompras.",
    "Div Yield (%)": "Rendimiento por dividendo anual en efectivo.",
    "Debt/Equity": "Nivel de apalancamiento financiero.",
    "Current Ratio": "Capacidad para cubrir pasivos de corto plazo.",
    "Quick Ratio": "Liquidez inmediata excluyendo inventarios."
}

# --- FUNCIONES DE CAPTURA MACRO & ARGENTINA API ---
@st.cache_data(ttl=300)
def obtener_datos_macro_globales():
    tickers_macro = {
        "S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Nikkei 225": "^N225",
        "Brent Oil": "BZ=F", "Bono US 10Y": "^TNX", "VIX": "^VIX"
    }
    res = {}
    for nombre, symb in tickers_macro.items():
        try:
            tk = yf.Ticker(symb)
            h = tk.history(period="2d")
            if len(h) >= 2:
                p_act, p_prev = float(h['Close'].iloc[-1]), float(h['Close'].iloc[-2])
                res[nombre] = {"precio": p_act, "var": ((p_act - p_prev) / p_prev) * 100}
            elif len(h) == 1:
                res[nombre] = {"precio": float(h['Close'].iloc[-1]), "var": 0.0}
        except Exception:
            res[nombre] = {"precio": 0.0, "var": 0.0}
    return res

@st.cache_data(ttl=300)
def obtener_datos_argentina():
    res = {
        "merval_ars": 0.0, "merval_var": 0.0,
        "oficial": 0.0, "mep": 0.0, "ccl": 0.0, "brecha": 0.0, "riesgo_pais": 0
    }
    try:
        tk_m = yf.Ticker("^MERV")
        hm = tk_m.history(period="2d")
        if len(hm) >= 2:
            p1, p2 = float(hm['Close'].iloc[-1]), float(hm['Close'].iloc[-2])
            res["merval_ars"] = p1
            res["merval_var"] = ((p1 - p2) / p2) * 100
    except Exception: pass

    try:
        req = urllib.request.Request("https://dolarapi.com/v1/dolares", headers={'User-Agent': 'Mozilla/5.0'})
        raw = urllib.request.urlopen(req, timeout=3).read()
        data = json.loads(raw)
        dolas = {item['casa']: float(item['venta']) for item in data if 'casa' in item and 'venta' in item}
        res["oficial"] = dolas.get("oficial", 0.0)
        res["mep"] = dolas.get("bolsa", 0.0)
        res["ccl"] = dolas.get("contadoconliqui", 0.0)
        if res["oficial"] > 0 and res["ccl"] > 0:
            res["brecha"] = ((res["ccl"] - res["oficial"]) / res["oficial"]) * 100
    except Exception: pass

    try:
        req_rp = urllib.request.Request("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo", headers={'User-Agent': 'Mozilla/5.0'})
        raw_rp = urllib.request.urlopen(req_rp, timeout=3).read()
        data_rp = json.loads(raw_rp)
        if isinstance(data_rp, dict) and "valor" in data_rp:
            res["riesgo_pais"] = int(data_rp["valor"])
    except Exception: pass

    return res

@st.cache_data(ttl=600)
def obtener_noticias_en_vivo():
    url = "https://news.google.com/rss/search?q=mercado+financiero+bolsa+acciones+OR+merval&hl=es-419&gl=AR&ceid=AR:es-419"
    noticias = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=4).read()
        root = ET.fromstring(html)
        for item in root.findall('.//item')[:4]:
            noticias.append(item.find('title').text)
    except Exception:
        noticias = [
            "Mercados atentos a los datos de inflación e tasas de interés globales.",
            "Expectativa en la plaza financiera local por la evolución del dólar y bonos.",
            "Volatilidad en commodities energéticos por factores geopolíticos."
        ]
    return noticias

# BARRA LATERAL (CONFIGURACIÓN GLOBAL)
st.sidebar.markdown("### ⚙️ Panel de Control")
modo_estrategia = st.sidebar.radio("Estrategia Activa:", ["Crecimiento (Agresivo)", "Fortaleza (Defensivo)"])
st.sidebar.markdown("---")
st.sidebar.info("💡 **SmartInvest Nivel 5:** Workflow cronológico secuencial (Top-Down).")

# ENCABEZADO
st.markdown("""
<div class="smart-header">
    <div>
        <h1>Smart<span>Invest</span> AI</h1>
        <div style="font-size:11px; color:var(--text-muted); font-weight:600;">Terminal Pro v2.0 • Top-Down Investment Workflow</div>
    </div>
</div>
""", unsafe_allow_html=True)

# NAVEGACIÓN EN 3 PASOS CRONOLÓGICOS
paso_activo = st.radio(
    "Navegación por Etapas de Inversión:",
    ["🌐 PASO A: Panorama Macro & Coyuntura", "🔍 PASO B: Análisis & Cobertura de Activos", "🏆 PASO C: TOP 10 Elite & Selección"],
    horizontal=True
)

st.markdown("---")

# ==========================================
# PASO A: PANORAMA MACRO & COYUNTURA GLOBAL
# ==========================================
if paso_activo == "🌐 PASO A: Panorama Macro & Coyuntura":
    macro_data = obtener_datos_macro_globales()
    arg_data = obtener_datos_argentina()
    noticias_vivo = obtener_noticias_en_vivo()

    st.markdown("### 🌐 Paso A: Clima de Mercado & Coyuntura Global")

    # CINTA 1: GLOBAL
    sp_v = macro_data.get('S&P 500', {}).get('var', 0)
    nk_v = macro_data.get('Nikkei 225', {}).get('var', 0)
    oil_p = macro_data.get('Brent Oil', {}).get('precio', 0)
    oil_v = macro_data.get('Brent Oil', {}).get('var', 0)
    us10_p = macro_data.get('Bono US 10Y', {}).get('precio', 0)
    vix_p = macro_data.get('VIX', {}).get('precio', 0)

    st.markdown('<div class="ribbon-title">🌍 CINTA 1: CLIMA GLOBAL & COMMODITIES</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="ribbon-grid">
        <div class="ribbon-card"><span class="lbl">S&P 500</span><span class="val">{macro_data.get('S&P 500', {}).get('precio', 0):,.1f}</span><span class="sub" style="color:{'#10b981' if sp_v >= 0 else '#ef4444'}">{sp_v:+.2f}%</span></div>
        <div class="ribbon-card"><span class="lbl">Nasdaq 100</span><span class="val">{macro_data.get('Nasdaq', {}).get('precio', 0):,.1f}</span><span class="sub" style="color:{'#10b981' if macro_data.get('Nasdaq', {}).get('var', 0) >= 0 else '#ef4444'}">{macro_data.get('Nasdaq', {}).get('var', 0):+.2f}%</span></div>
        <div class="ribbon-card"><span class="lbl">Nikkei 225</span><span class="val">{macro_data.get('Nikkei 225', {}).get('precio', 0):,.1f}</span><span class="sub" style="color:{'#10b981' if nk_v >= 0 else '#ef4444'}">{nk_v:+.2f}%</span></div>
        <div class="ribbon-card"><span class="lbl">Petróleo Brent</span><span class="val">${oil_p:.2f}</span><span class="sub" style="color:{'#10b981' if oil_v >= 0 else '#ef4444'}">{oil_v:+.2f}%</span></div>
        <div class="ribbon-card"><span class="lbl">Bono US 10Y</span><span class="val">{us10_p:.2f}%</span><span class="sub" style="color:#3b82f6;">Tasa Ref.</span></div>
        <div class="ribbon-card"><span class="lbl">VIX (Miedo)</span><span class="val">{vix_p:.2f}</span><span class="sub" style="color:{'#ef4444' if vix_p > 20 else '#10b981'};">{'Alta Volatilidad' if vix_p > 20 else 'Estable'}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # CINTA 2: ARGENTINA
    merv_p = arg_data.get('merval_ars', 0)
    merv_v = arg_data.get('merval_var', 0)
    ccl_p = arg_data.get('ccl', 0)
    merv_usd = (merv_p / ccl_p) if (merv_p > 0 and ccl_p > 0) else 0

    st.markdown('<div class="ribbon-title">🇦🇷 CINTA 2: MONITOR ARGENTINA & MAPA CAMBIARIO</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="ribbon-grid">
        <div class="ribbon-card"><span class="lbl">S&P Merval (ARS)</span><span class="val">{merv_p:,.0f}</span><span class="sub" style="color:{'#10b981' if merv_v >= 0 else '#ef4444'}">{merv_v:+.2f}%</span></div>
        <div class="ribbon-card"><span class="lbl">Merval (USD CCL)</span><span class="val">{merv_usd:,.0f} pts</span><span class="sub" style="color:#3b82f6;">Ajustado CCL</span></div>
        <div class="ribbon-card"><span class="lbl">Dólar Oficial</span><span class="val">${arg_data.get('oficial', 0):,.2f}</span><span class="sub" style="color:var(--text-muted);">Banco Nación</span></div>
        <div class="ribbon-card"><span class="lbl">Dólar MEP</span><span class="val">${arg_data.get('mep', 0):,.2f}</span><span class="sub" style="color:#10b981;">Bolsa</span></div>
        <div class="ribbon-card"><span class="lbl">Dólar CCL</span><span class="val">${arg_data.get('ccl', 0):,.2f}</span><span class="sub" style="color:#10b981;">Contado c/ Liq.</span></div>
        <div class="ribbon-card"><span class="lbl">Brecha Cambiaria</span><span class="val">{arg_data.get('brecha', 0):.1f}%</span><span class="sub" style="color:#f59e0b;">CCL vs Oficial</span></div>
        <div class="ribbon-card"><span class="lbl">Riesgo País</span><span class="val">{arg_data.get('riesgo_pais', 0)} pb</span><span class="sub" style="color:#f59e0b;">EMBI JP Morgan</span></div>
    </div>
    """, unsafe_allow_html=True)

    # CINTA 3: NOTICIAS
    st.markdown('<div class="ribbon-title">📡 CINTA 3: TITULARES Y DRIVERS EN VIVO (RSS)</div>', unsafe_allow_html=True)
    for n in noticias_vivo:
        st.markdown(f"""
        <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px; padding:10px 14px; margin-bottom:6px; font-size:12.5px; color:var(--text-main);">
            📌 {n}
        </div>
        """, unsafe_allow_html=True)

    # CINTA 4: REPORTE PARA IA
    st.markdown('<div class="ribbon-title">⚡ CINTA 4: GENERADOR AUTOMÁTICO REPORTE MATUTINO (1-CLICK COPY PARA IA)</div>', unsafe_allow_html=True)
    if st.button("Generar Reporte Matutino Nivel 5", type="primary"):
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        titulares_formatted = "\n".join([f"- {item}" for item in noticias_vivo[:3]])

        reporte_prompt = f"""
### 📝 RESUMEN MATUTINO DE MERCADOS – SmartInvest AI ({fecha_actual})

**🌍 Panorama Internacional**
Wall Street opera con tendencia {'positiva' if sp_v >= 0 else 'bajista'} (S&P 500: {sp_v:+.2f}%), con el bono del Tesoro a 10 años cotizando en {us10_p:.2f}% y el Petróleo Brent en ${oil_p:.2f}. El índice de volatilidad VIX se ubica en {vix_p:.2f} puntos.

**🇦🇷 Mercado Local (Argentina)**
El S&P Merval cotiza en {merv_p:,.0f} puntos ({merv_v:+.2f}%) (~{merv_usd:,.0f} USD CCL). En el mercado cambiario, el Dólar CCL cotiza a ${ccl_p:,.2f} con una brecha del {arg_data.get('brecha', 0):.1f}% frente al oficial, mientras el Riesgo País se posiciona en {arg_data.get('riesgo_pais', 0)} pb.

**📡 Principales Titulares de Hoy:**
{titulares_formatted}

*Copia este cuadro directamente y pégalo en tu IA para solicitar un análisis macro estratégico.*
"""
        st.code(reporte_prompt.strip(), language="markdown")

# ==========================================
# PASO B Y C: ANÁLISIS DE ACTIVOS Y TOP 10
# ==========================================
else:
    st.markdown("### 🔍 Módulo de Análisis & Selección de Activos")
    tickers_raw = st.text_input("Ingresá los Tickers de Cobertura (separados por coma):", "BP, CVX, ET, PBR, TEN, VIST, XOM, SHEL, AAPL.BA, MSFT.BA, GOOGL.BA, AMZN.BA, MELI.BA, NVDA.BA").upper()

    def corregir_ticker(t):
        t = t.strip()
        if t == "BRKB": return "BRK-B"
        if t == "BRKA": return "BRK-A"
        return t

    if tickers_raw:
        lista_tickers = [corregir_ticker(t) for t in tickers_raw.split(",") if t.strip()][:30]

        datos_fundamentales, datos_tecnicos, datos_revenue, datos_eps = [], [], [], []
        analisis_completo = {}
        ranking_puntos = {ticker: 0 for ticker in lista_tickers}
        posibles_puntos = {ticker: 0 for ticker in lista_tickers}
        fechas_headers = []
        nombres_base = ["4 Trim. atrás", "3 Trim. atrás", "2 Trim. atrás", "1 Trim. atrás", "Último Trim."]

        with st.spinner("Ejecutando modelo cuantitativo fundamental y técnico sobre los tickers..."):
            for ticker in lista_tickers:
                try:
                    accion = yf.Ticker(ticker)
                    info = accion.info or {}
                except Exception:
                    info = {}

                p_actual = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                try:
                    if not p_actual or pd.isna(p_actual):
                        hist_backup = accion.history(period="2d")
                        if not hist_backup.empty: p_actual = float(hist_backup['Close'].iloc[-1])
                except Exception: pass

                if not p_actual or pd.isna(p_actual): continue

                vol_prom = info.get('averageVolume')
                try:
                    if not vol_prom or pd.isna(vol_prom):
                        hist_vol = accion.history(period="20d")
                        if not hist_vol.empty: vol_prom = float(hist_vol['Volume'].mean())
                except Exception: pass

                v_justo = info.get('targetMeanPrice')
                beta = info.get('beta')
                upside = ((v_justo / p_actual) - 1) if (p_actual and v_justo and p_actual > 0) else None

                de_raw = info.get('debtToEquity')
                de_final = de_raw / 100 if de_raw is not None else None

                net_income = info.get('netIncomeToCommon') or info.get('netIncome')
                total_rev = info.get('totalRevenue')
                gross_prof = info.get('grossProfits')
                cost_of_rev = (total_rev - gross_prof) if (total_rev and gross_prof) else None

                fila_fun = {
                    "Ticker": ticker, "Empresa": info.get('longName', ticker),
                    "Precio": p_actual, "Fair Value (Target)": v_justo, "Upside (%)": upside,
                    "Beta (Volatilidad)": beta, "Volumen Promedio": vol_prom,
                    "Net Income": net_income, "Cost of Revenue": cost_of_rev,
                    "PER": info.get('trailingPE'), "Margen Neto (%)": info.get('profitMargins'),
                    "ROE (%)": info.get('returnOnEquity'), "ROA (%)": info.get('returnOnAssets'),
                    "Free Cash Flow": info.get('freeCashflow'), "Div Yield (%)": info.get('dividendYield'),
                    "Debt/Equity": de_final, "Current Ratio": info.get('currentRatio'), "Quick Ratio": info.get('quickRatio')
                }
                datos_fundamentales.append(fila_fun)

                dist_ath, rsi_val, dist_sma = None, None, None
                estado_rsi = "Neutral"
                try:
                    hist = accion.history(period="max")
                    if not hist.empty and len(hist) >= 14:
                        close_s = hist['Close']
                        p_ref = p_actual if p_actual is not None else float(close_s.iloc[-1])

                        ath = float(close_s.max())
                        dist_ath = ((p_ref / ath) - 1) * 100 if ath else None

                        if len(hist) >= 200:
                            sma200 = float(close_s.rolling(window=200).mean().iloc[-1])
                            dist_sma = ((p_ref / sma200) - 1) * 100 if sma200 else None

                        delta = close_s.diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        if loss.iloc[-1] != 0:
                            rsi_val = 100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1])))
                        else:
                            rsi_val = 100 if gain.iloc[-1] > 0 else 50

                        if rsi_val < 30: estado_rsi = "Oportunidad (Sobreventa)"
                        elif rsi_val > 70: estado_rsi = "Eufórico (Sobrecompra)"
                except Exception: pass

                fila_tec = {
                    "Ticker": ticker, "Distancia a Máx Histórico": dist_ath,
                    "RSI (14 días)": rsi_val, "Estado RSI": estado_rsi, "Distancia a Media 200d": dist_sma
                }
                datos_tecnicos.append(fila_tec)

                icon_r, icon_e = '●', '●'
                try:
                    df_q = accion.quarterly_financials
                    if df_q is not None and not df_q.empty:
                        if not fechas_headers:
                            fechas_raw = df_q.columns[:5][::-1]
                            for idx_f, d in enumerate(fechas_raw):
                                fechas_headers.append(f"{nombres_base[idx_f]} ({d.strftime('%d/%m/%Y')})")

                        if "Total Revenue" in df_q.index:
                            rev_s = df_q.loc["Total Revenue"].head(5).iloc[::-1]
                            fila_rev = {"Ticker": ticker}
                            for i, v in enumerate(rev_s):
                                if i < len(fechas_headers): fila_rev[fechas_headers[i]] = float(v) if pd.notna(v) else None
                            r_growth = ((rev_s.iloc[-1] - rev_s.iloc[0]) / abs(rev_s.iloc[0])) if len(rev_s) >= 2 else 0
                            icon_r = '▲' if r_growth > 0.05 else '▼' if r_growth < -0.05 else '●'
                            fila_rev["Tendencia"] = icon_r
                            datos_revenue.append(fila_rev)

                        et_e = "Basic EPS" if "Basic EPS" in df_q.index else "BasicEps" if "BasicEps" in df_q.index else None
                        if et_e:
                            eps_s = df_q.loc[et_e].head(5).iloc[::-1]
                            fila_eps = {"Ticker": ticker}
                            for i, v in enumerate(eps_s):
                                if i < len(fechas_headers): fila_eps[fechas_headers[i]] = float(v) if pd.notna(v) else None
                            e_growth = ((eps_s.iloc[-1] - eps_s.iloc[0]) / abs(eps_s.iloc[0])) if len(eps_s) >= 2 else 0
                            icon_e = '▲' if e_growth > 0.05 else '▼' if e_growth < -0.05 else '●'
                            fila_eps["Tendencia"] = icon_e
                            datos_eps.append(fila_eps)
                except Exception: pass

                analisis_completo[ticker] = {
                    "nombre": info.get('longName', ticker) if info else ticker,
                    "rev_t": icon_r, "eps_t": icon_e,
                    "net_margin": info.get('profitMargins', -1) if (info and info.get('profitMargins') is not None) else -1,
                    "upside_val": upside if upside is not None else -1,
                    "beta_val": beta if beta is not None else 99,
                    "rsi_val": rsi_val, "dist_sma": dist_sma
                }

        if datos_fundamentales:
            df_fund = pd.DataFrame(datos_fundamentales).set_index("Ticker")

            promedios = {}
            ratios_cols = ["PER", "Margen Neto (%)", "ROE (%)", "ROA (%)", "Free Cash Flow", "Div Yield (%)", "Debt/Equity", "Current Ratio", "Quick Ratio", "Net Income", "Cost of Revenue"]
            for col in ratios_cols:
                if col in df_fund.columns:
                    promedios[col] = pd.to_numeric(df_fund[col], errors='coerce').mean()

            for col in ratios_cols:
                if col in df_fund.columns:
                    prom = promedios[col]
                    for t in df_fund.index:
                        v_raw = df_fund.loc[t, col]
                        if pd.notna(v_raw) and v_raw is not None:
                            v_n = float(v_raw)
                            posibles_puntos[t] += 1
                            if col == "PER": es_mejor = v_n > 10
                            elif col in ["Debt/Equity", "Cost of Revenue"]: es_mejor = v_n < prom
                            else: es_mejor = v_n > prom
                            if es_mejor: ranking_puntos[t] += 1

            # VISTA PASO B O PASO C SEGÚN SELECCIÓN
            if paso_activo == "🔍 PASO B: Análisis & Cobertura de Activos":
                st.markdown("#### 📊 Tablero de Evaluación Fundamental & Técnica")
                tab_val, tab_fund, tab_rev, tab_eps, tab_tec = st.tabs([
                    "📊 Valuación & Targets", "🏛️ Ratios Fundamentales",
                    "💵 Ingresos (5 Trim.)", "📈 EPS (5 Trim.)", "🚦 Momento Técnico"
                ])

                # VALUACIÓN
                with tab_val:
                    html = "<table class='smart-table'><thead><tr><th>Ticker</th><th>Empresa</th><th>Precio</th><th>Fair Value (Target)</th><th>Upside %</th><th>Beta</th><th>Volumen Prom.</th></tr></thead><tbody>"
                    for _, f in df_fund.iterrows():
                        b_val = f['Beta (Volatilidad)']
                        b_icon = '⇠' if b_val and b_val <= 1 else '⇡' if b_val and b_val <= 1.5 else '⇢'
                        up_val = f['Upside (%)']
                        up_str = f"{up_val*100:.2f}%" if pd.notna(up_val) else "-"
                        up_style = "color:#10b981; font-weight:700;" if up_val and up_val > 0 else "color:#ef4444;"

                        p_str = f"${f['Precio']:,.2f}" if pd.notna(f['Precio']) else "-"
                        fv_str = f"${f['Fair Value (Target)']:,.2f}" if pd.notna(f['Fair Value (Target)']) else "-"
                        vol_str = f"{f['Volumen Promedio']/1e6:.2f}M" if pd.notna(f['Volumen Promedio']) else "-"

                        html += f"""<tr>
                            <td>{f.name}</td>
                            <td>{f['Empresa']}</td>
                            <td>{p_str}</td>
                            <td>{fv_str}</td>
                            <td style="{up_style}">{up_str}</td>
                            <td>{f"{b_val:.2f} {b_icon}" if pd.notna(b_val) else "-"}</td>
                            <td>{vol_str}</td>
                        </tr>"""
                    html += "</tbody></table>"
                    st.markdown(html, unsafe_allow_html=True)

                # RATIOS
                with tab_fund:
                    ratios_head = "".join([f"<th title='{TOOLTIPS.get(r, '')}'>{r}</th>" for r in ratios_cols])
                    html = f"<table class='smart-table'><thead><tr><th>Ticker</th>{ratios_head}</tr></thead><tbody>"

                    for t_idx, f in df_fund.iterrows():
                        html += f"<tr><td>{t_idx}</td>"
                        for r in ratios_cols:
                            val = f[r]
                            prom = promedios[r]
                            is_better = False
                            if pd.notna(val) and val is not None:
                                v_n = float(val)
                                if r == "PER": is_better = v_n > 10
                                elif r in ["Debt/Equity", "Cost of Revenue"]: is_better = v_n < prom
                                else: is_better = v_n > prom

                            cls = "cell-highlight" if is_better else ""
                            if pd.isna(val) or val is None: val_str = "-"
                            elif "%" in r: val_str = f"{val*100:.2f}%"
                            elif r in ["Free Cash Flow", "Net Income", "Cost of Revenue"]: val_str = fmt_num(val)
                            else: val_str = f"{val:.2f}"

                            html += f"<td class='{cls}'>{val_str}</td>"
                        html += "</tr>"

                    html += "<tr class='row-promedio'><td>PROMEDIO</td>"
                    for r in ratios_cols:
                        p_val = promedios[r]
                        if pd.isna(p_val): p_str = "-"
                        elif "%" in r: p_str = f"{p_val*100:.2f}%"
                        elif r in ["Free Cash Flow", "Net Income", "Cost of Revenue"]: p_str = fmt_num(p_val)
                        else: p_str = f"{p_val:.2f}"
                        html += f"<td>{p_str}</td>"
                    html += "</tr></tbody></table>"
                    st.markdown(html, unsafe_allow_html=True)

                # INGRESOS Y EPS
                for tab_obj, datos_list, titulo_lbl, es_moneda in [(tab_rev, datos_revenue, "Ingresos Totales", True), (tab_eps, datos_eps, "Basic EPS", False)]:
                    with tab_obj:
                        if datos_list:
                            df_m = pd.DataFrame(datos_list).set_index("Ticker")
                            f_cols = [c for c in df_m.columns if c != "Tendencia"]

                            html = f"<table class='smart-table'><thead><tr><th>Ticker</th>"
                            for fc in f_cols: html += f"<th>{fc}</th>"
                            html += "<th>Tendencia</th></tr></thead><tbody>"

                            for t_idx, row in df_m.iterrows():
                                html += f"<tr><td>{t_idx}</td>"
                                for fc in f_cols:
                                    val = row[fc]
                                    v_str = fmt_num(val, es_moneda) if es_moneda else (f"{val:.2f}" if pd.notna(val) else "-")
                                    html += f"<td>{v_str}</td>"
                                html += f"<td style='font-size:16px;'>{row['Tendencia']}</td></tr>"
                            html += "</tbody></table>"
                            st.markdown(html, unsafe_allow_html=True)

                            df_plot = df_m.drop(columns=["Tendencia"]).reset_index().melt(id_vars="Ticker")
                            df_plot['periodo'] = df_plot['variable'].str.split('(').str[0]
                            if es_moneda: df_plot['valor_b'] = df_plot['value'] / 1e9

                            y_col = 'valor_b' if es_moneda else 'value'
                            y_title = 'Billions $' if es_moneda else 'EPS ($)'

                            chart = alt.Chart(df_plot).mark_line(point=True).encode(
                                x=alt.X('periodo', sort=None, title="Trimestre"),
                                y=alt.Y(y_col, title=y_title),
                                color='Ticker'
                            ).properties(height=300)

                            st.altair_chart(chart, use_container_width=True)

                # TÉCNICO
                with tab_tec:
                    if datos_tecnicos:
                        df_t = pd.DataFrame(datos_tecnicos).set_index("Ticker")
                        html = "<table class='smart-table'><thead><tr><th>Ticker</th><th>Dist. Máx Histórico</th><th>RSI (14 días)</th><th>Estado RSI</th><th>Dist. Media 200d</th></tr></thead><tbody>"
                        for t_idx, row in df_t.iterrows():
                            rsi_v = row['RSI (14 días)']
                            rsi_str = f"{rsi_v:.2f}" if pd.notna(rsi_v) else "-"
                            dsma_v = row['Distancia a Media 200d']
                            dsma_str = f"{dsma_v:+.2f}%" if pd.notna(dsma_v) else "-"
                            dath_v = row['Distancia a Máx Histórico']
                            dath_str = f"{dath_v:+.2f}%" if pd.notna(dath_v) else "-"

                            html += f"""<tr>
                                <td>{t_idx}</td>
                                <td>{dath_str}</td>
                                <td style="font-weight:700;">{rsi_str}</td>
                                <td>{row['Estado RSI']}</td>
                                <td>{dsma_str}</td>
                            </tr>"""
                        html += "</tbody></table>"
                        st.markdown(html, unsafe_allow_html=True)

            # PASO C: TOP 10 ELITE
            elif paso_activo == "🏆 PASO C: TOP 10 Elite & Selección":
                st.markdown("### 🏆 Paso C: TOP 10 Selección Elite & Decisiones de Compra")

                final_scores = []
                for t in lista_tickers:
                    if t in analisis_completo:
                        meets_beta = analisis_completo[t]["beta_val"] < 1.5
                        meets_upside = analisis_completo[t]["upside_val"] > 0
                        if meets_beta and meets_upside:
                            p_fun = ranking_puntos[t]
                            p_crec = (1 if analisis_completo[t]["rev_t"] == "▲" else 0) + (1 if analisis_completo[t]["eps_t"] == "▲" else 0)
                            score_total = (p_fun + p_crec + 1) if modo_estrategia == "Crecimiento (Agresivo)" else (p_fun + 1)

                            rsi_v = analisis_completo[t]["rsi_val"]
                            dsma_v = analisis_completo[t]["dist_sma"]

                            if rsi_v is None or dsma_v is None: rec_tec, rag_cls = "⚪ Datos insuficientes", "rag-caution"
                            elif rsi_v < 30: rec_tec, rag_cls = "🟢 COMPRA FUERTE (Sobreventa RSI)", "rag-strong-buy"
                            elif 0 <= dsma_v <= 5: rec_tec, rag_cls = "🟢 COMPRA IDEAL (Soporte SMA200)", "rag-ideal"
                            elif rsi_v > 70: rec_tec, rag_cls = "🔴 EVITAR (Sobrecompra)", "rag-avoid"
                            elif dsma_v < 0: rec_tec, rag_cls = "🟡 PRECAUCIÓN (Tendencia Bajista)", "rag-caution"
                            else: rec_tec, rag_cls = "🟡 COMPRA MODERADA", "rag-ideal"

                            final_scores.append({
                                "Ticker": t, "Nombre": analisis_completo[t]["nombre"], "Total": score_total,
                                "Bonus": p_crec, "Fund": p_fun, "Beta": analisis_completo[t]["beta_val"],
                                "Upside": analisis_completo[t]["upside_val"], "Margin": analisis_completo[t]["net_margin"],
                                "RecTec": rec_tec, "RagClass": rag_cls
                            })

                top_10 = sorted(final_scores, key=lambda x: (x['Total'], x['Fund'], x['Margin']), reverse=True)[:10]

                if not top_10:
                    st.warning("Ningún ticker cumple las condiciones Sine Qua Non: Beta < 1.5 y Upside > 0%.")
                else:
                    for row_i in range(0, len(top_10), 2):
                        cols = st.columns(2)
                        for col_i, s in enumerate(top_10[row_i:row_i+2]):
                            puesto = row_i + col_i + 1
                            with cols[col_i]:
                                st.markdown(f"""
                                <div class="top-card">
                                    <div class="top-card-header">
                                        <div>
                                            <span style="font-size:10px; color:var(--text-muted);">Puesto #{puesto}</span>
                                            <div class="ticker-title">{s['Ticker']}</div>
                                            <div style="font-size:11px; color:var(--text-muted);">{s['Nombre']}</div>
                                        </div>
                                        <div class="score-badge">{s['Total']} Pts</div>
                                    </div>
                                    <div class="rag-pill {s['RagClass']}">{s['RecTec']}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                with st.expander("Ver Racional Completo"):
                                    st.write(f"🛡️ **Fortaleza:** {s['Fund']} pts sobre la media.")
                                    st.write(f"📈 **Momentum:** {'▲▲ Excelente' if s['Bonus']==2 else '▲ Positivo' if s['Bonus']==1 else '● Estable'}")
                                    st.write(f"💰 **Margen Neto:** {s['Margin']*100:.2f}%")
                                    st.write(f"⚡ **Beta:** {s['Beta']:.2f} | **Upside:** {s['Upside']*100:.1f}%")

                    st.markdown("---")
                    st.markdown("#### 📋 Generador de Prompt TOP 10 para IA (1-Click Copy)")
                    if st.button("Generar Prompt de Selección para IA", type="primary"):
                        top_summary = "\n".join([f"- **{x['Ticker']}** ({x['Nombre']}): Score {x['Total']} pts | Beta {x['Beta']:.2f} | Upside {x['Upside']*100:.1f}% | Señal: {x['RecTec']}" for x in top_10])

                        prompt_ia = f"""
Actúa como un Asesor Financiero Senior y analiza la siguiente selección de activos generada por SmartInvest bajo la estrategia {modo_estrategia}:

{top_summary}

Por favor provee un diagnóstico ejecutivo recomendando asignación de ponderación (%) para cada uno de estos activos en el portafolio.
"""
                        st.code(prompt_ia.strip(), language="markdown")
