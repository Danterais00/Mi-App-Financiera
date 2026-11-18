import json
import yfinance as yf
import pandas as pd
from datetime import datetime
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def probar_descarga_historica():
    diagnostico = {}
    
    # 1. Los 11 líderes de EE.UU. (Sectores GICS)
    lideres_usa = {
        "Tecnología": "MSFT",
        "Financiero": "JPM",
        "Energía": "XOM",
        "Salud": "UNH",
        "Cons. Discrecional": "AMZN",
        "Cons. Básico": "PG",
        "Industriales": "CAT",
        "Comunicaciones": "GOOGL",
        "Utilities": "NEE",
        "Materiales": "LIN",
        "Real Estate": "PLD"
    }

    # 2. Los 7 líderes de Argentina (ADRs y Locales)
    lideres_arg = {
        "Bancos": "GGAL",
        "Energía": "YPF",
        "Utilities": "CEPU",
        "Materiales": "TX",
        "Comunicaciones": "TEO",
        "Agro/Real Estate": "CRESY",
        "Tech/E-commerce": "MELI"
    }

    todos_tickers = list(lideres_usa.values()) + list(lideres_arg.values())
    
    try:
        diagnostico["tickers_solicitados"] = len(todos_tickers)
        
        # Descargamos 1 año de historia para calcular 1M, 6M y 1Y
        hist_data = yf.download(todos_tickers, period="1y", progress=False)
        
        if not hist_data.empty and 'Close' in hist_data:
            df_close = hist_data['Close']
            diagnostico["columnas_recibidas"] = list(df_close.columns)
            
            # Prueba de cálculo de rendimientos para un ticker de muestra (MSFT)
            if "MSFT" in df_close.columns:
                serie = df_close["MSFT"].dropna()
                if len(serie) >= 250:
                    actual = float(serie.iloc[-1])
                    precio_1m = float(serie.iloc[-21])
                    precio_6m = float(serie.iloc[-126])
                    precio_1y = float(serie.iloc[0])
                    
                    diagnostico["msft_sample"] = {
                        "precio_actual": actual,
                        "var_1m": round(((actual / precio_1m) - 1) * 100, 2),
                        "var_6m": round(((actual / precio_6m) - 1) * 100, 2),
                        "var_1y": round(((actual / precio_1y) - 1) * 100, 2)
                    }
                    diagnostico["status"] = "OK"
                else:
                    diagnostico["status"] = "DATOS_INCOMPLETOS"
        else:
            diagnostico["status"] = "DATAFRAME_VACIO"
            
    except Exception as e:
        diagnostico["status"] = f"ERROR: {type(e).__name__} - {str(e)}"
        
    return diagnostico

def extraer_datos_criticos():
    print("Ejecutando diagnóstico de YFinance (Líderes Sectoriales)...")
    diag = probar_descarga_historica()

    # Mantenemos la estructura mínima para no romper el front
    datos = {
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "diagnostico_yfinance": diag,
        "dolar_futuro_rofex": [],
        "cotizaciones_merval": {},
        "valuaciones_usa": {},
        "valuaciones_arg": {},
        "macro_arg_critica": {
            "merval_ars": None,
            "merval_usd": None,
            "bono_al30": None,
            "bono_al30d": None,
            "tasa_tamar": None,
            "tasa_badlar": None,
            "tasa_tna": None,
            "reservas_m": None,
            "dolares": []
        }
    }
    return datos

if __name__ == "__main__":
    datos_extraidos = extraer_datos_criticos()
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(datos_extraidos, f, indent=4)
    print("✅ Archivo datos_criticos.json actualizado con diagnóstico YFinance.")
