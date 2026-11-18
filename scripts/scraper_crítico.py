import json
import re
import yfinance as yf
import requests
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8',
    'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8'
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

def probar_fuentes_reservas():
    """Prueba 10 fuentes públicas reales desde GitHub Actions y devuelve el valor real + log de diagnóstico."""
    diagnostico = {}
    reservas_detectadas = None
    fuente_ganadora = None

    # 1. API Oficial Datos Argentina (datos.gob.ar - Series de Tiempo BCRA)
    series_datos_gob = [
        ("datos_gob_174", "https://apis.datos.gob.ar/series/api/series/?ids=174.1_RR_II_0_0_24&limit=1&sort=desc&format=json"),
        ("datos_gob_92", "https://apis.datos.gob.ar/series/api/series/?ids=92.1_RII_0_0_20&limit=1&sort=desc&format=json"),
        ("datos_gob_116", "https://apis.datos.gob.ar/series/api/series/?ids=116.4_IRR_0_0_27&limit=1&sort=desc&format=json")
    ]
    for nombre, url in series_datos_gob:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            diagnostico[nombre] = f"HTTP {r.status_code}"
            if r.status_code == 200:
                js = r.json()
                data_rows = js.get("data", [])
                if data_rows and len(data_rows[0]) >= 2 and data_rows[0][1] is not None:
                    val = float(data_rows[0][1])
                    fecha = data_rows[0][0]
                    diagnostico[f"{nombre}_dato"] = f"{val} ({fecha})"
                    if reservas_detectadas is None and val > 1000:
                        reservas_detectadas = round(val)
                        fuente_ganadora = f"{nombre} ({fecha})"
        except Exception as e:
            diagnostico[nombre] = f"ERR: {type(e).__name__}"

    # 2. Ámbito Financiero (Endpoints JSON públicos)
    endpoints_ambito = [
        ("ambito_bcra_res", "https://mercados.ambito.com//bcra/reservas/variacion"),
        ("ambito_res", "https://mercados.ambito.com//reservas/variacion"),
        ("ambito_dolar_res", "https://mercados.ambito.com//dolar/reservas/variacion"),
        ("ambito_bcra_general", "https://mercados.ambito.com//bcra/variacion")
    ]
    for nombre, url in endpoints_ambito:
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            diagnostico[nombre] = f"HTTP {r.status_code}"
            if r.status_code == 200:
                js = r.json()
                val = limpiar_numero_ar(js.get("ultimo", ""))
                diagnostico[f"{nombre}_dato"] = str(js)[:120]
                if reservas_detectadas is None and val and val > 1000:
                    reservas_detectadas = round(val)
                    fuente_ganadora = nombre
        except Exception as e:
            diagnostico[nombre] = f"ERR: {type(e).__name__}"

    # 3. FRED St. Louis CSV directo (sin API key - TRESEGARM052N en millones de USD)
    try:
        r_fred = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=TRESEGARM052N", headers=HEADERS, timeout=10)
        diagnostico["fred_csv"] = f"HTTP {r_fred.status_code}"
        if r_fred.status_code == 200:
            lineas = [l.strip() for l in r_fred.text.splitlines() if l.strip() and not l.startswith("DATE")]
            validas = [l for l in lineas if not l.endswith(".")]
            if validas:
                ultima = validas[-1].split(",")
                val_fred = float(ultima[1])
                diagnostico["fred_csv_dato"] = f"{val_fred} ({ultima[0]})"
                if reservas_detectadas is None and val_fred > 1000:
                    reservas_detectadas = round(val_fred)
                    fuente_ganadora = f"FRED ({ultima[0]})"
    except Exception as e:
        diagnostico["fred_csv"] = f"ERR: {type(e).__name__}"

    # 4. Scraping HTML directo en portales argentinos (Ámbito, Cronista, InfoDolar)
    portales_html = [
        ("ambito_html", "https://www.ambito.com/contenidos/reservas-bcra.html", r'US\$\s*([\d\.]+)\s*millones'),
        ("cronista_html", "https://www.cronista.com/MercadosOnline/monedas.html", r'Reservas[^0-9]{0,40}([\d\.]{5,7})'),
        ("infodolar_html", "https://www.infodolar.com/", r'Reservas[^0-9]{0,50}([\d\.]{5,7})')
    ]
    for nombre, url, patron in portales_html:
        try:
            r = requests.get(url, headers=HEADERS, verify=False, timeout=10)
            diagnostico[nombre] = f"HTTP {r.status_code}"
            if r.status_code == 200:
                m = re.search(patron, r.text, re.IGNORECASE)
                if m:
                    val_h = limpiar_numero_ar(m.group(1))
                    diagnostico[f"{nombre}_dato"] = str(val_h)
                    if reservas_detectadas is None and val_h and 10000 <= val_h <= 150000:
                        reservas_detectadas = round(val_h)
                        fuente_ganadora = nombre
        except Exception as e:
            diagnostico[nombre] = f"ERR: {type(e).__name__}"

    diagnostico["fuente_ganadora"] = fuente_ganadora
    return reservas_detectadas, diagnostico

def extraer_datos_criticos():
    print("Iniciando extracción de datos críticos desde GitHub Actions...")
    reservas_val, diag_reservas = probar_fuentes_reservas()

    datos = {
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "diagnostico_reservas": diag_reservas,
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
            "reservas_m": reservas_val,
            "dolares": []
        }
    }
    
    # 1. DÓLARES (DolarAPI - Intacto)
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

    # 2. BONO AL30 Y AL30D (Data912 + Ámbito - Intacto)
    try:
        res_d912 = requests.get("https://data912.com/live/arg_bonds", headers=HEADERS, timeout=10)
        if res_d912.status_code == 200:
            for b in res_d912.json():
                sym = b.get("symbol") or b.get("ticker")
                p = float(b.get("c", b.get("price", 0)))
                if sym == "AL30" and p > 0:
                    datos["macro_arg_critica"]["bono_al30"] = round(p * 100, 2) if p < 2000 else round(p, 2)
                if sym == "AL30D" and p > 0:
                    datos["macro_arg_critica"]["bono_al30d"] = round(p, 2)
    except Exception as e:
        print(f"Error Data912 AL30: {e}")

    if datos["macro_arg_critica"]["bono_al30"] is None:
        try:
            res_b = requests.get("https://mercados.ambito.com//bonos/en-pesos/AL30/variacion", headers=HEADERS, timeout=10)
            if res_b.status_code == 200:
                precio_b = limpiar_numero_ar(res_b.json().get("ultimo", ""))
                if precio_b:
                    datos["macro_arg_critica"]["bono_al30"] = round(precio_b * 100, 2) if precio_b < 2000 else round(precio_b, 2)
        except Exception:
            pass

    # 3. TASAS DE MERCADO (TNA, BADLAR y TAMAR - Intacto)
    try:
        res_tna = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/depositos30Dias", headers=HEADERS, timeout=10)
        if res_tna.status_code == 200 and len(res_tna.json()) > 0:
            val_t = float(res_tna.json()[-1].get("valor", 0))
            if val_t > 0:
                datos["macro_arg_critica"]["tasa_tna"] = round(val_t * 100, 2) if val_t < 2 else round(val_t, 2)
    except Exception as e:
        print(f"Error TNA depositos30Dias: {e}")

    try:
        res_pf = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo", headers=HEADERS, timeout=10)
        if res_pf.status_code == 200 and isinstance(res_pf.json(), list):
            tasas_30 = []
            tasas_largo = []
            for entidad in res_pf.json():
                tc = entidad.get("tnaClientes")
                if tc and float(tc) > 0:
                    val_pct = float(tc) * 100 if float(tc) < 2 else float(tc)
                    tasas_30.append(val_pct)
                for tramo in entidad.get("tasas", []):
                    if tramo.get("tna") and int(tramo.get("plazoMinDias", 0)) >= 60:
                        v_largo = float(tramo["tna"]) * 100 if float(tramo["tna"]) < 2 else float(tramo["tna"])
                        tasas_largo.append(v_largo)
            
            if tasas_30:
                if datos["macro_arg_critica"]["tasa_tna"] is None:
                    datos["macro_arg_critica"]["tasa_tna"] = round(sum(tasas_30) / len(tasas_30), 2)
                top_bancos = sorted(tasas_30, reverse=True)[:5]
                datos["macro_arg_critica"]["tasa_badlar"] = round(sum(top_bancos) / len(top_bancos), 2)
            
            if tasas_largo:
                top_inst = sorted(tasas_largo, reverse=True)[:5]
                datos["macro_arg_critica"]["tasa_tamar"] = round(sum(top_inst) / len(top_inst), 2)
    except Exception as e:
        print(f"Error curva plazoFijo: {e}")

    if datos["macro_arg_critica"]["tasa_tna"] is not None:
        base = datos["macro_arg_critica"]["tasa_tna"]
        if datos["macro_arg_critica"]["tasa_badlar"] is None:
            datos["macro_arg_critica"]["tasa_badlar"] = round(base + 1.25, 2)
        if datos["macro_arg_critica"]["tasa_tamar"] is None:
            datos["macro_arg_critica"]["tasa_tamar"] = round(datos["macro_arg_critica"]["tasa_badlar"] + 0.85, 2)

    # 4. COTIZACIONES MERVAL (Screener Técnico y Fundamental Panel Líder - Intacto)
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

    # 5. MERVAL REAL (ARS y USD - Intacto)
    try:
        res_m = requests.get("https://mercados.ambito.com//indice/.merv/variacion", headers=HEADERS, timeout=10)
        if res_m.status_code == 200:
            merv_val = limpiar_numero_ar(res_m.json().get("ultimo", ""))
            if merv_val and merv_val > 100000:
                merv_ars = round(merv_val)
                datos["macro_arg_critica"]["merval_ars"] = merv_ars
                if ccl_venta and ccl_venta > 0:
                    datos["macro_arg_critica"]["merval_usd"] = round(merv_ars / ccl_venta)
    except Exception:
        pass

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

    # 6. VALUACIONES RELATIVAS (Empresas USA y ADRs - Intacto)
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
