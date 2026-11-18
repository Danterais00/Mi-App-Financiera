import json
import re
import yfinance as yf
import requests
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def limpiar_numero_ar(texto):
    if not texto:
        return None
    limpio = re.sub(r'[^\d,.-]', '', str(texto)).strip()
    if not limpio:
        return None
    if ',' in limpio and '.' in limpio:
        limpio = limpio.replace('.', '').replace(',', '.')
    elif ',' in limpio:
        limpio = limpio.replace(',', '.')
    try:
        return float(limpio)
    except ValueError:
        return None

def extraer_datos_criticos():
    print("Iniciando extracción de datos críticos desde GitHub Actions...")
    datos = {
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "diagnostico_apis": {},
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
    
    # 1. DÓLARES (DolarAPI - Comprobado OK)
    try:
        res = requests.get("https://dolarapi.com/v1/dolares", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for d in res.json():
                if d["casa"] in ["oficial", "blue", "bolsa", "contadoconliqui"]:
                    nombre = "MEP" if d["casa"] == "bolsa" else "CCL" if d["casa"] == "contadoconliqui" else d["casa"].capitalize()
                    datos["macro_arg_critica"]["dolares"].append({
                        "nombre": nombre, 
                        "compra": float(d["compra"]), 
                        "venta": float(d["venta"])
                    })
    except Exception as e:
        print(f"Error DolarAPI: {e}")

    ccl_venta = next((d['venta'] for d in datos["macro_arg_critica"]["dolares"] if d['nombre'] == 'CCL'), None)

    # 2. MERVAL REAL (ARS y USD - Comprobado OK)
    try:
        res_m = requests.get("https://mercados.ambito.com//indice/.merv/variacion", headers=HEADERS, timeout=10)
        if res_m.status_code == 200:
            merv_val = limpiar_numero_ar(res_m.json().get("ultimo", ""))
            if merv_val:
                merv_ars = round(merv_val)
                datos["macro_arg_critica"]["merval_ars"] = merv_ars
                if ccl_venta and ccl_venta > 0:
                    datos["macro_arg_critica"]["merval_usd"] = round(merv_ars / ccl_venta)
    except Exception as e:
        print(f"Error Ámbito Merval: {e}")

    # 3. BONO AL30 (ARS y USD - Comprobado OK)
    try:
        res_b = requests.get("https://mercados.ambito.com//bonos/en-pesos/AL30/variacion", headers=HEADERS, timeout=10)
        if res_b.status_code == 200:
            precio_b = limpiar_numero_ar(res_b.json().get("ultimo", ""))
            if precio_b:
                datos["macro_arg_critica"]["bono_al30"] = round(precio_b * 100, 2) if precio_b < 2000 else round(precio_b, 2)
    except Exception:
        pass

    try:
        res_d912 = requests.get("https://data912.com/live/arg_bonds", headers=HEADERS, timeout=10)
        if res_d912.status_code == 200:
            for b in res_d912.json():
                sym = b.get("symbol") or b.get("ticker")
                p = float(b.get("c", b.get("price", 0)))
                if sym == "AL30" and p > 0 and datos["macro_arg_critica"]["bono_al30"] is None:
                    datos["macro_arg_critica"]["bono_al30"] = round(p * 100, 2) if p < 2000 else round(p, 2)
                if sym == "AL30D" and p > 0:
                    datos["macro_arg_critica"]["bono_al30d"] = round(p, 2)
    except Exception:
        pass

    # 4. TNA PLAZO FIJO 30 DÍAS (Comprobado OK)
    try:
        res_tna = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/depositos30Dias", headers=HEADERS, timeout=10)
        datos["diagnostico_apis"]["depositos30Dias"] = res_tna.status_code
        if res_tna.status_code == 200 and len(res_tna.json()) > 0:
            val_t = float(res_tna.json()[-1].get("valor", 0))
            if val_t > 0:
                datos["macro_arg_critica"]["tasa_tna"] = round(val_t * 100, 2) if val_t < 2 else round(val_t, 2)
    except Exception as e:
        datos["diagnostico_apis"]["depositos30Dias"] = str(e)

    # 5. AUDITORÍA REAL DE ENDPOINTS EN ARGENTINADATOS (Tasas y Reservas)
    endpoints_prueba = {
        "plazoFijo": "https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo",
        "badlar": "https://api.argentinadatos.com/v1/finanzas/tasas/badlar",
        "tamar": "https://api.argentinadatos.com/v1/finanzas/tasas/tamar",
        "reservas_bcra": "https://api.argentinadatos.com/v1/finanzas/bcra/reservas",
        "reservas_ind": "https://api.argentinadatos.com/v1/finanzas/indices/reservas"
    }
    for nombre_ep, url_ep in endpoints_prueba.items():
        try:
            r = requests.get(url_ep, headers=HEADERS, timeout=10)
            datos["diagnostico_apis"][nombre_ep] = f"HTTP {r.status_code}"
            if r.status_code == 200:
                js = r.json()
                if isinstance(js, list) and len(js) > 0:
                    datos["diagnostico_apis"][f"{nombre_ep}_muestra"] = js[-1]
                    if nombre_ep == "badlar" and js[-1].get("valor"):
                        v = float(js[-1]["valor"])
                        datos["macro_arg_critica"]["tasa_badlar"] = round(v * 100, 2) if v < 2 else round(v, 2)
                    elif nombre_ep == "tamar" and js[-1].get("valor"):
                        v = float(js[-1]["valor"])
                        datos["macro_arg_critica"]["tasa_tamar"] = round(v * 100, 2) if v < 2 else round(v, 2)
                    elif "reservas" in nombre_ep and js[-1].get("valor"):
                        datos["macro_arg_critica"]["reservas_m"] = round(float(js[-1]["valor"]))
        except Exception as e:
            datos["diagnostico_apis"][nombre_ep] = str(e)

    # 6. COTIZACIONES MERVAL (Screener Técnico y Fundamental Panel Líder)
    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", 
             "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", 
             "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    general = ["AGRO.BA", "AUSO.BA", "BHIP.BA", "BOLT.BA", "BPAT.BA", "CAPX.BA", "CECO2.BA", 
               "CELU.BA", "CGPA2.BA", "DGCU2.BA", "FERR.BA", "GBAN.BA", "GCLA.BA", 
               "HAVA.BA", "INVJ.BA", "LEDE.BA", "METR.BA", "MOLI.BA", "MORI.BA", "OEST.BA", "SAMI.BA"]
    
    todos_merval = lider + general
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
    except Exception as e:
        print(f"Error descargando Merval: {e}")

    # 7. VALUACIONES RELATIVAS (Empresas USA y ADRs)
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
