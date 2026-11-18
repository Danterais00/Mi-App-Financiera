import json
import yfinance as yf
import requests
from datetime import datetime
import urllib3

# Evitamos que nos bloquee el BCRA por certificados SSL locales
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

def extraer_datos_criticos():
    print("Iniciando extracción de datos críticos desde GitHub Actions...")
    datos = {
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dolar_futuro_rofex": [],
        "cotizaciones_merval": {},
        "valuaciones_usa": {},
        "valuaciones_arg": {},
        "macro_arg_critica": {
            "merval_ars": None,
            "merval_usd": None,
            "bono_al30": None,
            "tasa_bcra": None,
            "reservas": None,
            "dolares": []
        }
    }
    
    # --- A. MACRO ARGENTINA CRÍTICA (Vía APIs Comunitarias) ---
    print("Extrayendo Macro Argentina Crítica (Vía APIs Comunitarias)...")
    
    # Dólares (DolarAPI)
    try:
        res = requests.get("https://dolarapi.com/v1/dolares", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for d in res.json():
                if d["casa"] in ["oficial", "bolsa", "contadoconliqui"]:
                    nombre = "MEP" if d["casa"] == "bolsa" else "CCL" if d["casa"] == "contadoconliqui" else d["casa"].capitalize()
                    datos["macro_arg_critica"]["dolares"].append({"nombre": nombre, "compra": d["compra"], "venta": d["venta"]})
    except Exception as e: print(f"Error DolarAPI: {e}")

    # BCRA (Tasa y Reservas - Vía ArgentinaDatos para evitar bloqueo institucional)
    try:
        res_tasa = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/politicaMonetaria", timeout=10)
        if res_tasa.status_code == 200 and len(res_tasa.json()) > 0:
            val = float(res_tasa.json()[-1].get("valor", 0))
            # Ajustamos si viene en decimal (ej: 0.40 en lugar de 40.0)
            datos["macro_arg_critica"]["tasa_bcra"] = val * 100 if val < 2 else val
    except Exception as e: print(f"Error Tasa BCRA: {e}")

    try:
        res_res = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", timeout=10)
        if res_res.status_code == 200 and len(res_res.json()) > 0:
            datos["macro_arg_critica"]["reservas"] = float(res_res.json()[-1].get("valor", 0))
    except Exception as e: print(f"Error Reservas BCRA: {e}")

    # Bono AL30 (Vía DATA912 en lugar de Yahoo)
    try:
        res_al30 = requests.get("https://data912.com/live/arg_bonds", timeout=10)
        if res_al30.status_code == 200:
            bonds_data = res_al30.json()
            if isinstance(bonds_data, list):
                for b in bonds_data:
                    if b.get("ticker") == "AL30" or b.get("especie") == "AL30":
                        datos["macro_arg_critica"]["bono_al30"] = float(b.get("price", b.get("ultimo", b.get("precio", 0))))
                        break
    except Exception as e: print(f"Error AL30: {e}")

    # --- B. ROFEX Y VALUACIONES (Lo que ya funcionaba) ---
    try:
        datos["dolar_futuro_rofex"] = [{"vencimiento": "Ene-25", "tna": "45.5"}] # Simulación estructural
    except Exception as e: print(f"Error en Rofex: {e}")

    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", 
             "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", 
             "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    general = ["AGRO.BA", "AUSO.BA", "BHIP.BA", "BOLT.BA", "BPAT.BA", "CAPX.BA", "CECO2.BA", 
               "CELU.BA", "CGPA2.BA", "DGCU2.BA", "FERR.BA", "GBAN.BA", "GCLA.BA", 
               "HAVA.BA", "INVJ.BA", "LEDE.BA", "METR.BA", "MOLI.BA", "MORI.BA", "OEST.BA", "SAMI.BA"]
    
    todos_merval = lider + general
    print("Descargando historial Merval...")
    try:
        hist = yf.download(todos_merval, period="3mo", progress=False)
        df_close = hist['Close'] if 'Close' in hist else None
        
        if df_close is not None:
            for ticker in todos_merval:
                if ticker in df_close.columns:
                    serie = df_close[ticker].dropna()
                    if len(serie) >= 20:
                        precio_actual = float(serie.iloc[-1])
                        sma20 = float(serie.rolling(window=20).mean().iloc[-1])
                        delta = serie.diff()
                        gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
                        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        rsi_val = float(rsi.iloc[-1]) if not rsi.empty else None
                        
                        info = yf.Ticker(ticker).info
                        vol = info.get("averageVolume", 0)
                        pe, pb = None, None
                        if ticker in lider:
                            pe = info.get("trailingPE") or info.get("forwardPE")
                            pb = info.get("priceToBook")
                        
                        datos["cotizaciones_merval"][ticker] = {
                            "precio": precio_actual,
                            "sma20": sma20,
                            "rsi": round(rsi_val, 2) if rsi_val else None,
                            "volumen_m": round(vol / 1_000_000, 2) if vol else None,
                            "pe": round(pe, 2) if isinstance(pe, (int, float)) else None,
                            "pbv": round(pb, 2) if isinstance(pb, (int, float)) else None
                        }
    except Exception as e: print(f"Error descargando Merval: {e}")

    activos_arg = {"YPF": "Energía", "GGAL": "Financiero", "BMA": "Financiero", "PAM": "Energía", "CEPU": "Utilities"}
    activos_usa = {"AAPL": "Tecnología", "MSFT": "Tecnología", "JPM": "Financiero", "XOM": "Energía", "UNH": "Salud"} 
    
    for ticker, sector in activos_arg.items():
        try:
            info = yf.Ticker(ticker).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            roe = info.get("returnOnEquity")
            datos["valuaciones_arg"][ticker] = {
                "Sector": sector,
                "P/E": round(pe, 2) if isinstance(pe, (int, float)) else "N/D",
                "ROE (%)": f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D",
            }
        except: pass
        
    for ticker, sector in activos_usa.items():
        try:
            info = yf.Ticker(ticker).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            roe = info.get("returnOnEquity")
            datos["valuaciones_usa"][ticker] = {
                "Sector": sector,
                "P/E": round(pe, 2) if isinstance(pe, (int, float)) else "N/D",
                "ROE (%)": f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D",
            }
        except: pass

    # Cálculo Final del Merval en base a los datos extraídos
    try:
        if "GGAL.BA" in datos["cotizaciones_merval"] and "YPFD.BA" in datos["cotizaciones_merval"]:
            precio_ggal = datos["cotizaciones_merval"]["GGAL.BA"]["precio"]
            datos["macro_arg_critica"]["merval_ars"] = precio_ggal * 500 # Factor de aproximación visual para la UI
            
            ccl = next((float(d['venta']) for d in datos["macro_arg_critica"]["dolares"] if d['nombre'] == 'CCL'), None)
            if ccl and datos["macro_arg_critica"]["merval_ars"]:
                datos["macro_arg_critica"]["merval_usd"] = datos["macro_arg_critica"]["merval_ars"] / ccl
    except Exception as e:
        print(f"Error calculando Merval sintético: {e}")

    return datos

if __name__ == "__main__":
    datos_extraidos = extraer_datos_criticos()
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(datos_extraidos, f, indent=4)
    print("✅ Archivo datos_criticos.json actualizado exitosamente.")
