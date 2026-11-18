import json
import yfinance as yf
import requests
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
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
            "bono_al30d": None,
            "tasa_tamar": None,
            "tasa_badlar": None,
            "tasa_tna": None,
            "reservas_m": None,
            "dolares": []
        }
    }
    
    # 1. DÓLARES (DolarAPI)
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

    # 2. MERVAL REAL (ARS y USD) vía Endpoint Público Ámbito
    try:
        url_ambito_merv = "https://mercados.ambito.com//indice/.merv/variacion"
        res_m = requests.get(url_ambito_merv, headers=HEADERS, timeout=10)
        if res_m.status_code == 200:
            data_m = res_m.json()
            val_str = str(data_m.get("ultimo", "")).replace(".", "").replace(",", ".")
            if val_str:
                merv_ars = round(float(val_str))
                datos["macro_arg_critica"]["merval_ars"] = merv_ars
                if ccl_venta and ccl_venta > 0:
                    datos["macro_arg_critica"]["merval_usd"] = round(merv_ars / ccl_venta)
    except Exception as e:
        print(f"Error Ámbito Merval: {e}")

    # 3. BONO AL30 (ARS y USD) vía Ámbito / Data912
    try:
        url_al30 = "https://mercados.ambito.com//bonos/en-pesos/AL30/variacion"
        res_b = requests.get(url_al30, headers=HEADERS, timeout=10)
        if res_b.status_code == 200:
            data_b = res_b.json()
            val_b = str(data_b.get("ultimo", "")).replace(".", "").replace(",", ".")
            if val_b:
                precio_b = float(val_b)
                datos["macro_arg_critica"]["bono_al30"] = round(precio_b * 100, 2) if precio_b < 2000 else round(precio_b, 2)
    except Exception as e:
        print(f"Error Ámbito AL30: {e}")

    if datos["macro_arg_critica"]["bono_al30"] is None:
        try:
            res_d912 = requests.get("https://data912.com/live/arg_bonds", headers=HEADERS, timeout=10)
            if res_d912.status_code == 200:
                for b in res_d912.json():
                    if b.get("symbol") == "AL30" or b.get("ticker") == "AL30":
                        p = float(b.get("c", b.get("price", 0)))
                        if p > 0:
                            datos["macro_arg_critica"]["bono_al30"] = round(p * 100, 2) if p < 2000 else round(p, 2)
                    if b.get("symbol") == "AL30D" or b.get("ticker") == "AL30D":
                        pd_val = float(b.get("c", b.get("price", 0)))
                        if pd_val > 0:
                            datos["macro_arg_critica"]["bono_al30d"] = round(pd_val, 2)
        except Exception as e:
            print(f"Error Data912 AL30: {e}")

    # 4. RESERVAS BCRA (En Millones de USD enteros)
    try:
        res_res = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", headers=HEADERS, timeout=10)
        if res_res.status_code == 200 and len(res_res.json()) > 0:
            val_res = float(res_res.json()[-1].get("valor", 0))
            if val_res > 0:
                datos["macro_arg_critica"]["reservas_m"] = round(val_res)
    except Exception as e:
        print(f"Error Reservas ArgentinaDatos: {e}")

    # 5. TASAS OFICIALES (TAMAR, BADLAR y TNA Plazo Fijo 30 días)
    # 5A. BADLAR vía ArgentinaDatos
    try:
        res_badlar = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/badlar", headers=HEADERS, timeout=10)
        if res_badlar.status_code == 200 and len(res_badlar.json()) > 0:
            val_b = float(res_badlar.json()[-1].get("valor", 0))
            if val_b > 0:
                datos["macro_arg_critica"]["tasa_badlar"] = round(val_b * 100, 2) if val_b < 2 else round(val_b, 2)
    except Exception as e:
        print(f"Error BADLAR ArgentinaDatos: {e}")

    # 5B. TNA Plazo Fijo 30 días vía ArgentinaDatos
    try:
        res_tna = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/depositos30Dias", headers=HEADERS, timeout=10)
        if res_tna.status_code == 200 and len(res_tna.json()) > 0:
            val_t = float(res_tna.json()[-1].get("valor", 0))
            if val_t > 0:
                datos["macro_arg_critica"]["tasa_tna"] = round(val_t * 100, 2) if val_t < 2 else round(val_t, 2)
    except Exception as e:
        print(f"Error TNA ArgentinaDatos: {e}")

    # 5C. TAMAR (y respaldos de BADLAR/TNA/Reservas) vía API Oficial BCRA v4.0
    try:
        res_vars = requests.get("https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias", headers=HEADERS, verify=False, timeout=12)
        if res_vars.status_code == 200:
            payload = res_vars.json()
            lista_vars = payload.get("results", payload) if isinstance(payload, dict) else payload
            if isinstance(lista_vars, list):
                for v in lista_vars:
                    desc = str(v.get("descripcion", "")).lower()
                    id_var = v.get("idVariable")
                    if not id_var:
                        continue
                    
                    # Buscar TAMAR (Bancos privados / total en TNA)
                    if "tamar" in desc and "privados" in desc and "tna" in desc and datos["macro_arg_critica"]["tasa_tamar"] is None:
                        r_tamar = requests.get(f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{id_var}?limit=1", headers=HEADERS, verify=False, timeout=10)
                        if r_tamar.status_code == 200:
                            res_list = r_tamar.json().get("results", [])
                            if res_list:
                                datos["macro_arg_critica"]["tasa_tamar"] = round(float(res_list[-1]["valor"]), 2)
                    
                    # Respaldo BADLAR si falló ArgentinaDatos
                    if "badlar" in desc and "privados" in desc and "tna" in desc and datos["macro_arg_critica"]["tasa_badlar"] is None:
                        r_bad = requests.get(f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{id_var}?limit=1", headers=HEADERS, verify=False, timeout=10)
                        if r_bad.status_code == 200:
                            res_list = r_bad.json().get("results", [])
                            if res_list:
                                datos["macro_arg_critica"]["tasa_badlar"] = round(float(res_list[-1]["valor"]), 2)

                    # Respaldo Reservas si falló ArgentinaDatos
                    if "reservas internacionales" in desc and datos["macro_arg_critica"]["reservas_m"] is None:
                        r_res = requests.get(f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{id_var}?limit=1", headers=HEADERS, verify=False, timeout=10)
                        if r_res.status_code == 200:
                            res_list = r_res.json().get("results", [])
                            if res_list:
                                datos["macro_arg_critica"]["reservas_m"] = round(float(res_list[-1]["valor"]))
    except Exception as e:
        print(f"Error API BCRA v4.0: {e}")

    # Si TAMAR no estuvo disponible por descripción específica, intentar búsqueda amplia por "tamar" en BCRA
    if datos["macro_arg_critica"]["tasa_tamar"] is None:
        try:
            res_vars = requests.get("https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias", headers=HEADERS, verify=False, timeout=10)
            if res_vars.status_code == 200:
                payload = res_vars.json()
                lista_vars = payload.get("results", payload) if isinstance(payload, dict) else payload
                for v in lista_vars:
                    if "tamar" in str(v.get("descripcion", "")).lower():
                        r_tamar = requests.get(f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{v['idVariable']}?limit=1", headers=HEADERS, verify=False, timeout=10)
                        if r_tamar.status_code == 200 and r_tamar.json().get("results"):
                            val_tm = float(r_tamar.json()["results"][-1]["valor"])
                            if 5 <= val_tm <= 150: # Validar que sea TNA y no TEA
                                datos["macro_arg_critica"]["tasa_tamar"] = round(val_tm, 2)
                                break
        except Exception:
            pass

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

    # Respaldo dinámico para Merval ARS si Ámbito falló
    if datos["macro_arg_critica"]["merval_ars"] is None and len(datos["cotizaciones_merval"]) > 0:
        try:
            p_ggal = datos["cotizaciones_merval"].get("GGAL.BA", {}).get("precio", 0)
            p_ypfd = datos["cotizaciones_merval"].get("YPFD.BA", {}).get("precio", 0)
            p_pamp = datos["cotizaciones_merval"].get("PAMP.BA", {}).get("precio", 0)
            p_bma = datos["cotizaciones_merval"].get("BMA.BA", {}).get("precio", 0)
            if p_ggal and p_ypfd and p_pamp and p_bma:
                merv_calc = round((p_ggal * 165) + (p_ypfd * 145) + (p_pamp * 110) + (p_bma * 75))
                datos["macro_arg_critica"]["merval_ars"] = merv_calc
                if ccl_venta and ccl_venta > 0:
                    datos["macro_arg_critica"]["merval_usd"] = round(merv_calc / ccl_venta)
        except Exception as e:
            print(f"Error cálculo canasta Merval: {e}")

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
