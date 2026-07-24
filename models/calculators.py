import pandas as pd

# Definición de Benchmarks Absolutos (Salud Financiera)
BENCHMARKS = {
    "PER": {"cond": lambda x: 0 < x <= 25, "ref": "0 - 25"},
    "Margen Neto (%)": {"cond": lambda x: x >= 0.10, "ref": "> 10%"},
    "Gross Margin (%)": {"cond": lambda x: x >= 0.30, "ref": "> 30%"},
    "ROE (%)": {"cond": lambda x: x >= 0.15, "ref": "> 15%"},
    "ROA (%)": {"cond": lambda x: x >= 0.05, "ref": "> 5%"},
    "FCF Yield (%)": {"cond": lambda x: x >= 0.04, "ref": "> 4%"},
    "Div Yield (%)": {"cond": lambda x: x > 0.0, "ref": "> 0%"},
    "Debt/Equity": {"cond": lambda x: x <= 1.2, "ref": "< 1.2"},
    "Current Ratio": {"cond": lambda x: x >= 1.2, "ref": "> 1.2"},
    "Quick Ratio": {"cond": lambda x: x >= 1.0, "ref": "> 1.0"}
}

def calcular_puntajes(df_fun, lista_tickers):
    """Calcula puntajes basados en estándares absolutos del Value Investing."""
    df_total = pd.DataFrame(df_fun).set_index("Ticker").T
    df_comp = df_total.drop(["Precio", "Fair Value (Target)", "Upside (%)", "Beta", "Volumen Promedio"])
    
    # Agregar columna visual de referencia
    refs = [BENCHMARKS[idx]["ref"] if idx in BENCHMARKS else "-" for idx in df_comp.index]
    df_comp.insert(0, "REFERENCIA", refs)
    
    puntos = {t: 0 for t in lista_tickers}
    posibles = {t: 0 for t in lista_tickers}
    
    for idx in df_comp.index.drop("Empresa"):
        for col in [c for c in df_comp.columns if c != "REFERENCIA"]:
            val = df_comp.loc[idx, col]
            if pd.notna(val) and idx in BENCHMARKS:
                posibles[col] += 1
                try:
                    v_n = float(val)
                    es_mejor = BENCHMARKS[idx]["cond"](v_n)
                    if es_mejor:
                        puntos[col] += 1
                except:
                    pass
                    
    return df_total, df_comp, puntos, posibles
