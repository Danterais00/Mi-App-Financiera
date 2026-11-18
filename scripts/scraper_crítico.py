import json
import re
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def limpiar_numero_ar(texto):
    if not texto: return None
    limpio = re.sub(r'[^\d,.-]', '', str(texto)).strip()
    if not limpio: return None
    if ',' in limpio and '.' in limpio: limpio = limpio.replace('.', '').replace(',', '.')
    elif ',' in limpio: limpio = limpio.replace(',', '.')
    try: return float(limpio)
    except: return None

def extraer_datos_criticos():
    print("Iniciando extracción de datos críticos desde GitHub Actions...")
    
    reservas_val = None
    try:
        url_res = "https://apis.datos.gob.ar/series/api/series/?ids=300.1_AP_ACT_RESTER_0_M_21&limit=1&sort=desc&format=json"
        r = requests.get(url_res, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            d_rows = r.json().get("data", [])
            if d_rows and len(d_rows[0]) >= 2 and d_rows[0][1] is not None:
                v_usd = float(d_rows[0][1])
                reservas_val = round(v_usd / 1_000_000) if v_usd > 1_000_000_000 else round(v_usd)
    except: pass

    datos = {
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cotizaciones_merval": {}, "valuaciones_usa": {}, "valuaciones_arg": {},
        "macro_arg_critica": {
            "merval_ars": None, "merval_usd": None, "bono_al30": None, "bono_al30d": None,
            "tasa_tamar": None, "tasa_badlar": None, "tasa_tna": None, "reservas_m": reservas_val, "dolares": []
        }
    }
    
    # 1. DÓLARES
    try:
        res = requests.get("https://dolarapi.com/v1/dolares", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            for d in res.json():
                if d["casa"] in ["oficial", "blue", "bolsa", "contadoconliqui", "mayorista"]:
                    nombre = "MEP" if d["casa"] == "bolsa" else "CCL" if d["casa"] == "contadoconliqui" else d["casa"].capitalize()
                    datos["macro_arg_critica"]["dolares"].append({"nombre": nombre, "compra": float(d["compra"]), "venta": float(d["venta"])})
    except: pass
    ccl_venta = next((d['venta'] for d in datos["macro_arg_critica"]["dolares"] if d['nombre'] == 'CCL'), None)

    # 2. BONOS AL30
    try:
        res_d912 = requests.get("https://data912.com/live/arg_bonds", headers=HEADERS, timeout=10)
        if res_d912.status_code == 200:
            for b in res_d912.json():
                sym = b.get("symbol") or b.get("ticker")
                p = float(b.get("c", b.get("price", 0)))
                if sym == "AL30" and p > 0: datos["macro_arg_critica"]["bono_al30"] = round(p * 100, 2) if p < 2000 else round(p, 2)
                if sym == "AL30D" and p > 0: datos["macro_arg_critica"]["bono_al30d"] = round(p, 2)
    except: pass
    
    # Respaldo Ámbito para AL30 si falló data912
    if datos["macro_arg_critica"]["bono_al30"] is None:
        try:
            res_b = requests.get("https://mercados.ambito.com//bonos/en-pesos/AL30/variacion", headers=HEADERS, timeout=10)
            if res_b.status_code == 200:
                precio_b = limpiar_numero_ar(res_b.json().get("ultimo", ""))
                if precio_b: datos["macro_arg_critica"]["bono_al30"] = round(precio_b * 100, 2) if precio_b < 2000 else round(precio_b, 2)
        except: pass

    # 3. TASAS
    try:
        res_tna = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/depositos30Dias", headers=HEADERS, timeout=10)
        if res_tna.status_code == 200 and len(res_tna.json()) > 0:
            v_t = float(res_tna.json()[-1].get("valor", 0))
            if v_t > 0: datos["macro_arg_critica"]["tasa_tna"] = round(v_t * 100, 2) if v_t < 2 else round(v_t, 2)
    except: pass
    try:
        res_pf = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo", headers=HEADERS, timeout=10)
        if res_pf.status_code == 200:
            t30 = [float(e["tnaClientes"])*100 for e in res_pf.json() if e.get("tnaClientes") and float(e["tnaClientes"])>0]
            if t30:
                if datos["macro_arg_critica"]["tasa_tna"] is None: datos["macro_arg_critica"]["tasa_tna"] = round(sum(t30)/len(t30), 2)
                t5 = sorted(t30, reverse=True)[:5]
                datos["macro_arg_critica"]["tasa_badlar"] = round(sum(t5)/len(t5), 2)
                datos["macro_arg_critica"]["tasa_tamar"] = round(datos["macro_arg_critica"]["tasa_badlar"] + 0.85, 2)
    except: pass

    # 4. MERVAL SCREENER
    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    general = ["AGRO.BA", "AUSO.BA", "BHIP.BA", "BOLT.BA", "BPAT.BA", "CAPX.BA", "CECO2.BA", "CELU.BA", "CGPA2.BA", "DGCU2.BA", "FERR.BA", "GBAN.BA", "GCLA.BA", "HAVA.BA", "INVJ.BA", "LEDE.BA", "METR.BA", "MOLI.BA", "MORI.BA", "OEST.BA", "SAMI.BA"]
    try:
        hist = yf.download(lider + general, period="3mo", progress=False)
        if not hist.empty and 'Close' in hist:
            df_c = hist['Close']
            for t in (lider + general):
                if t in df_c.columns:
                    s = df_c[t].dropna()
                    if len(s) >= 20:
                        p_act = float(s.iloc[-1])
                        sma20 = float(s.rolling(window=20).mean().iloc[-1])
                        delta = s.diff()
                        gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
                        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                        rsi = float((100 - (100 / (1 + (gain / loss)))).iloc[-1])
                        info = yf.Ticker(t).info
                        vol = info.get("averageVolume", 0)
                        pe = info.get("trailingPE") or info.get("forwardPE") if t in lider else None
                        pb = info.get("priceToBook") if t in lider else None
                        datos["cotizaciones_merval"][t] = {"precio": p_act, "sma20": sma20, "rsi": round(rsi, 2), "volumen_m": round(vol/1e6, 2) if vol else None, "pe": round(pe, 2) if pe else None, "pbv": round(pb, 2) if pb else None}
    except: pass

    # MERVAL ARS/USD (Restaurado el código original)
    try:
        res_m = requests.get("https://mercados.ambito.com//indice/.merv/variacion", headers=HEADERS, timeout=10)
        if res_m.status_code == 200:
            merv_val = limpiar_numero_ar(res_m.json().get("ultimo", ""))
            if merv_val and merv_val > 100000:
                merv_ars = round(merv_val)
                datos["macro_arg_critica"]["merval_ars"] = merv_ars
                if ccl_venta and ccl_venta > 0:
                    datos["macro_arg_critica"]["merval_usd"] = round(merv_ars / ccl_venta)
    except: pass

    # Respaldo canasta Merval si falla Ámbito
    if datos["macro_arg_critica"]["merval_ars"] is None and len(datos["cotizaciones_merval"]) > 0:
        p_ggal = datos["cotizaciones_merval"].get("GGAL.BA", {}).get("precio", 0)
        p_ypfd = datos["cotizaciones_merval"].get("YPFD.BA", {}).get("precio", 0)
        p_pamp = datos["cotizaciones_merval"].get("PAMP.BA", {}).get("precio", 0)
        p_bma = datos["cotizaciones_merval"].get("BMA.BA", {}).get("precio", 0)
        if p_ggal and p_ypfd and p_pamp and p_bma:
            merv_calc = round((p_ggal * 165) + (p_ypfd * 145) + (p_pamp * 110) + (p_bma * 75))
            datos["macro_arg_critica"]["merval_ars"] = merv_calc
            if ccl_venta and ccl_venta > 0: datos["macro_arg_critica"]["merval_usd"] = round(merv_calc / ccl_venta)

    # 5. LÍDERES SECTORIALES (GARP: Valuación + Momentum)
    lideres_usa = {"MSFT": "Tecnología", "JPM": "Financiero", "XOM": "Energía", "UNH": "Salud", "AMZN": "Cons. Discrecional", "PG": "Cons. Básico", "CAT": "Industriales", "GOOGL": "Comunicaciones", "NEE": "Utilities", "LIN": "Materiales", "PLD": "Real Estate"}
    lideres_arg = {"GGAL": "Bancos", "YPF": "Energía", "CEPU": "Utilities", "TX": "Materiales", "TEO": "Comunicaciones", "CRESY": "Agro/Real Estate", "MELI": "E-commerce"}
    todos_lideres = list(lideres_usa.keys()) + list(lideres_arg.keys())
    
    df_hist_lideres = pd.DataFrame()
    try:
        hist_lideres = yf.download(todos_lideres, period="1y", progress=False)
        if not hist_lideres.empty and 'Close' in hist_lideres: df_hist_lideres = hist_lideres['Close']
    except: pass

    for t, sector in lideres_usa.items():
        try:
            info = yf.Ticker(t).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            roe = info.get("returnOnEquity")
            v1, v6, v12 = None, None, None
            if not df_hist_lideres.empty and t in df_hist_lideres.columns:
                s = df_hist_lideres[t].dropna()
                if len(s) >= 250:
                    act = float(s.iloc[-1])
                    v1 = round(((act / float(s.iloc[-21])) - 1) * 100, 1)
                    v6 = round(((act / float(s.iloc[-126])) - 1) * 100, 1)
                    v12 = round(((act / float(s.iloc[0])) - 1) * 100, 1)
            datos["valuaciones_usa"][t] = {"Sector": sector, "P/E": round(pe, 2) if isinstance(pe, (int, float)) else "N/D", "ROE (%)": f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D", "1M": v1, "6M": v6, "1Y": v12}
        except: pass
        
    for t, sector in lideres_arg.items():
        try:
            info = yf.Ticker(t).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            roe = info.get("returnOnEquity")
            v1, v6, v12 = None, None, None
            if not df_hist_lideres.empty and t in df_hist_lideres.columns:
                s = df_hist_lideres[t].dropna()
                if len(s) >= 250:
                    act = float(s.iloc[-1])
                    v1 = round(((act / float(s.iloc[-21])) - 1) * 100, 1)
                    v6 = round(((act / float(s.iloc[-126])) - 1) * 100, 1)
                    v12 = round(((act / float(s.iloc[0])) - 1) * 100, 1)
            datos["valuaciones_arg"][t] = {"Sector": sector, "P/E": round(pe, 2) if isinstance(pe, (int, float)) else "N/D", "ROE (%)": f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D", "1M": v1, "6M": v6, "1Y": v12}
        except: pass

    return datos

if __name__ == "__main__":
    d = extraer_datos_criticos()
    with open("datos_criticos.json", "w", encoding="utf-8") as f: json.dump(d, f, indent=4)
    print("✅ Archivo datos_criticos.json actualizado.")
