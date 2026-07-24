import pandas as pd

# 🧠 MENTE 1: Estrategia Defensiva (Value & Dividends)
BENCHMARKS_DEFENSIVO = {
    "PER": {"cond": lambda x: 0 < x <= 20, "ref": "0 - 20"},
    "EV/EBITDA": {"cond": lambda x: 0 < x <= 12, "ref": "< 12 (Barato)"},
    "Margen Neto (%)": {"cond": lambda x: x >= 0.10, "ref": "> 10%"},
    "ROE (%)": {"cond": lambda x: x >= 0.12, "ref": "> 12%"},
    "FCF Yield (%)": {"cond": lambda x: x >= 0.05, "ref": "> 5%"},
    "Div Yield (%)": {"cond": lambda x: x > 0.02, "ref": "> 2%"},
    "Payout Ratio (%)": {"cond": lambda x: 0 < x <= 0.60, "ref": "< 60% (Seguro)"},
    "Debt/Equity": {"cond": lambda x: x <= 1.0, "ref": "< 1.0"},
    "Current Ratio": {"cond": lambda x: x >= 1.5, "ref": "> 1.5"},
    "Short Interest (%)": {"cond": lambda x: x < 0.05, "ref": "< 5%"}
}

# 🧠 MENTE 2: Estrategia Agresiva (Growth & Momentum)
BENCHMARKS_CRECIMIENTO = {
    "Forward P/E": {"cond": lambda x: 0 < x <= 35, "ref": "< 35"},
    "PEG Ratio": {"cond": lambda x: 0 < x <= 1.5, "ref": "< 1.5 (Ganga)"},
    "Gross Margin (%)": {"cond": lambda x: x >= 0.40, "ref": "> 40%"},
    "ROE (%)": {"cond": lambda x: x >= 0.15, "ref": "> 15%"},
    "ROA (%)": {"cond": lambda x: x >= 0.05, "ref": "> 5%"},
    "FCF Yield (%)": {"cond": lambda x: x >= 0.02, "ref": "> 2%"},
    "Debt/Equity": {"cond": lambda x: x <= 1.5, "ref": "< 1.5"},
    "Current Ratio": {"cond": lambda x: x >= 1.2, "ref": "> 1.2"},
    "Short Interest (%)": {"cond": lambda x: x < 0.10, "ref": "< 10%"},
    "Consenso (1-5)": {"cond": lambda x: 1.0 <= x <= 2.5, "ref": "1.0 - 2.5 (Compra)"}
}

def calcular_puntajes(df_fun, lista_tickers, modo_estrategia):
    """Calcula puntajes dependiendo de la estrategia seleccionada."""
    benchmarks = BENCHMARKS_CRECIMIENTO if "Crecimiento" in modo_estrategia else BENCHMARKS_DEFENSIVO
    
    df_total = pd.DataFrame(df_fun).set_index("Ticker").T
    
    # Separamos métricas de mercado para no ensuciar la tabla contable
    metricas_mercado = ["Precio", "Fair Value (Target)", "Upside (%)", "Beta", "Volumen Promedio", "Forward P/E", "PEG Ratio", "EV/EBITDA", "Consenso (1-5)"]
    df_comp = df_total.drop(index=[m for m in metricas_mercado if m in df_total.index], errors='ignore')
    
    refs = [benchmarks[idx]["ref"] if idx in benchmarks else "-" for idx in df_comp.index]
    df_comp.insert(0, "REFERENCIA", refs)
    
    puntos = {t: 0 for t in lista_tickers}
    posibles = {t: 0 for t in lista_tickers}
    
    # Puntuamos a la empresa contra su propio benchmark (Evaluación Global)
    for idx in df_total.index.drop("Empresa"):
        for t in lista_tickers:
            if t in df_total.columns:
                val = df_total.loc[idx, t]
                if pd.notna(val) and idx in benchmarks:
                    posibles[t] += 1
                    try:
                        v_n = float(val)
                        if benchmarks[idx]["cond"](v_n):
                            puntos[t] += 1
                    except:
                        pass
                        
    return df_total, df_comp, puntos, posibles
