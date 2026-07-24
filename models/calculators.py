import pandas as pd

def calcular_puntajes(df_fun, lista_tickers):
    """Calcula promedios del sector y asigna puntos de fortaleza a cada ticker."""
    df_total = pd.DataFrame(df_fun).set_index("Ticker").T
    
    # Aislar solo las filas que son comparables matemáticamente
    df_comp = df_total.drop(["Precio", "Fair Value (Target)", "Upside (%)", "Beta", "Volumen Promedio"])
    df_comp["PROMEDIO"] = df_comp.apply(pd.to_numeric, errors='coerce').mean(axis=1)
    
    puntos = {t: 0 for t in lista_tickers}
    posibles = {t: 0 for t in lista_tickers}
    
    # Analizar indicador por indicador
    for idx in df_comp.index.drop("Empresa"):
        for col in [c for c in df_comp.columns if c != "PROMEDIO"]:
            val = df_comp.loc[idx, col]
            prom = df_comp.loc[idx, "PROMEDIO"]
            
            if pd.notna(val) and pd.notna(prom):
                posibles[col] += 1
                try:
                    v_n = float(val)
                    p_n = float(prom)
                    
                    # Lógica de puntaje según el indicador
                    if idx == "PER":
                        es_mejor = 0 < v_n < p_n
                    elif idx in ["Debt/Equity", "Cost of Revenue"]:
                        es_mejor = v_n < p_n
                    else:
                        es_mejor = v_n > p_n
                        
                    if es_mejor:
                        puntos[col] += 1
                except:
                    pass
                    
    return df_total, df_comp, puntos, posibles
