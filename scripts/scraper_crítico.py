import json
import re
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8',
    'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8'
}

def limpiar_numero_ar(texto):
    """Convierte formatos argentinos (ej: '23,45' o '49.464,00') a float estándar."""
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

def extraer_bcra_html():
    """Extrae Reservas, TAMAR y BADLAR desde la tabla pública de Principales Variables del BCRA."""
    resultado = {"reservas_m": None, "tasa_tamar": None, "tasa_badlar": None}
    urls_bcra = [
        "https://www.bcra.gob.ar/PublicacionesEstadisticas/Principales_variables.asp",
        "https://bcra.gob.ar/PublicacionesEstadisticas/Principales_variables.asp"
    ]
    for url in urls_bcra:
        try:
            res = requests.get(url, headers=HEADERS, verify=False, timeout=15)
            if res.status_code == 200 and len(res.text) > 1000:
                soup = BeautifulSoup(res.text, 'html.parser')
                for fila in soup.find_all('tr'):
                    celdas = [c.get_text(" ", strip=True) for c in fila.find_all(['td', 'th'])]
                    if len(celdas) >= 2:
                        desc = celdas[0].lower()
                        val = limpiar_numero_ar(celdas[-1])
                        if val is None or val <= 0:
                            continue
                        if "reservas internacionales" in desc and resultado["reservas_m"] is None:
                            resultado["reservas_m"] = round(val)
                        elif "tamar" in desc and ("n.a." in desc or "privados" in desc or "total" in desc) and resultado["tasa_tamar"] is None:
                            if 3 <= val <= 150:
                                resultado["tasa_tamar"] = round(val, 2)
                        elif "badlar" in desc and ("privados" in desc or "n.a." in desc) and resultado["tasa_badlar"] is None:
                            if 3 <= val <= 150:
                                resultado["tasa_badlar"] = round(val, 2)
                if any(v is not None for v in resultado.values()):
                    break
        except Exception as e:
            print(f"Error scraping BCRA HTML ({url}): {e}")
    return resultado

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
            merv_val = limpiar_numero_ar(data_m.get("ultimo", ""))
            if merv_val:
                merv_ars = round(merv_val)
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
            precio_b = limpiar_numero_ar(res_b.json().get("ultimo", ""))
            if precio_b:
                datos["macro_arg_critica"]["bono_al30"] = round(precio_b * 100, 2) if precio_b < 2000 else round(precio_b, 2)
    except Exception as e:
        print(f"Error Ámbito AL30: {e}")

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
    except Exception as e:
        print(f"Error Data912 AL30: {e}")

    # 4. RESERVAS, TAMAR Y BADLAR (Vía Tabla HTML Oficial BCRA + Respaldos Ámbito / ArgentinaDatos)
    bcra_datos = extraer_bcra_html()
    datos["macro_arg_critica"]["reservas_m"] = bcra_datos["reservas_m"]
    datos["macro_arg_critica"]["tasa_tamar"] = bcra_datos["tasa_tamar"]
    datos["macro_arg_critica"]["tasa_badlar"] = bcra_datos["tasa_badlar"]

    # Respaldo BADLAR vía Ámbito Financiero
    if datos["macro_arg_critica"]["tasa_badlar"] is None:
        try:
            res_amb_bad = requests.get("https://mercados.ambito.com//tasas/badlar/variacion", headers=HEADERS, timeout=10)
            if res_amb_bad.status_code == 200:
                val_b = limpiar_numero_ar(res_amb_bad.json().get("ultimo", ""))
                if val_b and 3 <= val_b <= 150:
                    datos["macro_arg_critica"]["tasa_badlar"] = round(val_b, 2)
        except Exception as e:
            print(f"Error Ámbito BADLAR: {e}")

    # Respaldo TAMAR vía Ámbito Financiero
    if datos["macro_arg_critica"]["tasa_tamar"] is None:
        try:
            res_amb_tam = requests.get("https://mercados.ambito.com//tasas/tamar/variacion", headers=HEADERS, timeout=10)
            if res_amb_tam.status_code == 200:
                val_tm = limpiar_numero_ar(res_amb_tam.json().get("ultimo", ""))
                if val_tm and 3 <= val_tm <= 150:
                    datos["macro_arg_critica"]["tasa_tamar"] = round(val_tm, 2)
        except Exception as e:
            print(f"Error Ámbito TAMAR: {e}")

    # Respaldo Reservas vía Ámbito Financiero / ArgentinaDatos
    if datos["macro_arg_critica"]["reservas_m"] is None:
        try:
            res_amb_res = requests.get("https://mercados.ambito.com//bcra/reservas/variacion", headers=HEADERS, timeout=10)
            if res_amb_res.status_code == 200:
                val_r = limpiar_numero_ar(res_amb_res.json().get("ultimo", ""))
                if val_r and val_r > 1000:
                    datos["macro_arg_critica"]["reservas_m"] = round(val_r)
        except Exception:
            pass

    if datos["macro_arg_critica"]["reservas_m"] is None:
        try:
            res_res = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", headers=HEADERS, timeout=10)
            if res_res.status_code == 200 and len(res_res.json()) > 0:
                val_res = float(res_res.json()[-1].get("valor", 0))
                if val_res > 0:
                    datos["macro_arg_critica"]["reservas_m"] = round(val_res)
        except Exception:
            pass

    # 5. TNA PLAZO FIJO 30 DÍAS (ArgentinaDatos depositos30Dias + promedio plazoFijo)
    try:
        res_tna = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/depositos30Dias", headers=HEADERS, timeout=10)
        if res_tna.status_code == 200 and len(res_tna.json()) > 0:
            val_t = float(res_tna.json()[-1].get("valor", 0))
            if val_t > 0:
                datos["macro_arg_critica"]["tasa_tna"] = round(val_t * 100, 2) if val_t < 2 else round(val_t, 2)
    except Exception as e:
        print(f"Error TNA depositos30Dias: {e}")

    if datos["macro_arg_critica"]["tasa_tna"] is None:
        try:
            res_pf = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo", headers=HEADERS, timeout=10)
            if res_pf.status_code == 200 and isinstance(res_pf.json(), list):
                tasas_bancos = [float(b["tnaClientes"]) * 100 for b in res_pf.json() if b.get("tnaClientes")]
                if tasas_bancos:
                    datos["macro_arg_critica"]["tasa_tna"] = round(sum(tasas_bancos) / len(tasas_bancos), 2)
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
        except Exception:
            pass

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
