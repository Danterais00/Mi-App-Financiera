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
    
    # --- A. MACRO ARGENTINA CRÍTICA (Nuevos datos para el Panel N/D) ---
    print("Extrayendo Macro Argentina Crítica (BCRA y Merval)...")
    
    # Dólares
    try:
        res = requests.get("https://dolarapi.com/v1/dolares", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for d in res.json():
                if d["casa"] in ["oficial", "bolsa", "contadoconliqui"]:
                    nombre = "MEP" if d["casa"] == "bolsa" else "CCL" if d["casa"] == "contadoconliqui" else d["casa"].capitalize()
                    datos["macro_arg_critica"]["dolares"].append({"nombre": nombre, "compra": d["compra"], "venta": d["venta"]})
    except Exception as e: print(f"Error DolarAPI: {e}")

    # BCRA (Tasa y Reservas)
    try:
        res_vars = requests.get("https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias", verify=False, timeout=10)
        if res_vars.status_code == 200:
            variables = res_vars.json()
            id_res = next((v['idVariable'] for v in variables if "reservas internacionales" in v['descripcion'].lower()), 1)
            id_tasa = next((v['idVariable'] for v in variables if "política monetaria" in v['descripcion'].lower() or "pases" in v['descripcion'].lower()), 6)
            
            # Reservas
            res_r = requests.get(f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{id_res}", verify=False, timeout=10)
            if res_r.status_code == 200 and res_r.json().get('results'):
                datos["macro_arg_critica"]["reservas"] = float(res_r.json()['results'][-1]["valor"])
                
            # Tasa
            res_t = requests.get(f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{id_tasa}", verify=False, timeout=10)
            if res_t.status_code == 200 and res_t.json().get('results'):
                datos["macro_arg_critica"]["tasa_bcra"] = float(res_t.json()['results'][-1]["valor"])
    except Exception as e:
        print(f"Error API BCRA: {e}")
        # Fallbacks rápidos de ArgentinaDatos si falla el BCRA
        try:
            r1 = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/politicaMonetaria", timeout=5).json()
            if r1: datos["macro_arg_critica"]["tasa_bcra"] = float(r1[-1].get("valor")) * 100 if float(r1[-1].get("valor")) < 2 else float(r1[-1].get("valor"))
            r2 = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", timeout=5).json()
            if r2: datos["macro_arg_critica"]["reservas"] = float(r2[-1].get("valor"))
        except: pass

    # Merval ARS, USD y Bono AL30
    try:
        hist_macro = yf.download(["^MERV", "AL30.BA"], period="5d", progress=False)
        df_c = hist_macro['Close'] if 'Close' in hist_macro else None
        
        if df_c is not None:
            if "^MERV" in df_c.columns:
                s_merv = df_c["^MERV"].dropna()
                if not s_merv.empty:
                    merv_ars = float(s_merv.iloc[-1])
                    datos["macro_arg_critica"]["merval_ars"] = merv_ars
                    # Calculamos USD si tenemos CCL
                    ccl = next((float(d['venta']) for d in datos["macro_arg_critica"]["dolares"] if d['nombre'] == 'CCL'), None)
                    if ccl: datos["macro_arg_critica"]["merval_usd"] = merv_ars / ccl
            
            if "AL30.BA" in df_c.columns:
                s_al30 = df_c["AL30.BA"].dropna()
                if not s_al30.empty:
                    datos["macro_arg_critica"]["bono_al30"] = float(s_al30.iloc[-1])
    except Exception as e: print(f"Error Yahoo Macro: {e}")

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

    return datos

if __name__ == "__main__":
    datos_extraidos = extraer_datos_criticos()
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(datos_extraidos, f, indent=4)
    print("✅ Archivo datos_criticos.json actualizado exitosamente.")
