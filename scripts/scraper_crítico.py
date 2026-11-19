import json
import requests
import yfinance as yf
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def ejecutar_test_correcciones():
    reporte = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "test_1_reservas_actualizadas": {},
        "test_2_al30_historico": {},
        "test_3_saneamiento_adrs": {},
        "test_4_pe_merval_local": {}
    }

    # --- TEST 1: Buscar Reservas BCRA actualizadas a Nov 2026 ---
    # Fuente A: Serie diaria oficial Datos.gob.ar (174.1_RR_II_0_0_22)
    try:
        r_gob = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=174.1_RR_II_0_0_22&limit=5&sort=desc&format=json", timeout=8)
        if r_gob.status_code == 200:
            filas = [f for f in r_gob.json().get("data", []) if f[1] is not None]
            if filas:
                reporte["test_1_reservas_actualizadas"]["datos_gob_diaria"] = {"status": "OK", "fecha": filas[0][0], "valor": filas[0][1]}
    except Exception as e:
        reporte["test_1_reservas_actualizadas"]["datos_gob_diaria"] = {"status": "ERROR", "detalle": str(e)}

    # Fuente B: API BCRA v3.0 Monetarias (Variable 1 = Reservas Internacionales)
    try:
        r_bcra = requests.get("https://api.bcra.gob.ar/estadisticas/v3.0/Monetarias/1?limit=1", verify=False, timeout=8)
        if r_bcra.status_code == 200:
            res = r_bcra.json().get("results", [])
            if res:
                reporte["test_1_reservas_actualizadas"]["bcra_v3"] = {"status": "OK", "fecha": res[0].get("fecha"), "valor": res[0].get("valor")}
    except Exception as e:
        reporte["test_1_reservas_actualizadas"]["bcra_v3"] = {"status": "ERROR", "detalle": str(e)}

    # Fuente C: ArgentinaDatos Reservas
    try:
        r_ad = requests.get("https://api.argentinadatos.com/v1/finanzas/bcra/reservas", headers=HEADERS, timeout=8)
        if r_ad.status_code == 200:
            ult = r_ad.json()[-1]
            reporte["test_1_reservas_actualizadas"]["argentinadatos"] = {"status": "OK", "dato": ult}
    except Exception as e:
        reporte["test_1_reservas_actualizadas"]["argentinadatos"] = {"status": "ERROR", "detalle": str(e)}

    # --- TEST 2: Historial 1M del Bono AL30 ---
    # Fuente A: Data912 histórico o live
    try:
        r_d9 = requests.get("https://data912.com/historical/bonds/AL30", headers=HEADERS, timeout=8)
        if r_d9.status_code == 200:
            hist = r_d9.json()
            if len(hist) >= 21:
                act = float(hist[-1]["c"])
                prev = float(hist[-21]["c"])
                var_1m = round(((act / prev) - 1) * 100, 2)
                reporte["test_2_al30_historico"]["data912_hist"] = {"status": "OK", "ultimo": act, "hace_21d": prev, "var_1m_pct": var_1m}
        else:
            reporte["test_2_al30_historico"]["data912_hist"] = {"status": "HTTP_" + str(r_d9.status_code)}
    except Exception as e:
        reporte["test_2_al30_historico"]["data912_hist"] = {"status": "ERROR", "detalle": str(e)}

    # Fuente B: yfinance AL30D.BA / AL30.BA
    for sym in ["AL30.BA", "AL30D.BA"]:
        try:
            h = yf.Ticker(sym).history(period="2mo")
            if len(h) >= 21:
                act = float(h["Close"].iloc[-1])
                prev = float(h["Close"].iloc[-21])
                reporte["test_2_al30_historico"][sym] = {"status": "OK", "ultimo": round(act, 2), "var_1m_pct": round(((act/prev)-1)*100, 2)}
            else:
                reporte["test_2_al30_historico"][sym] = {"status": "SIN_DATOS_SUFICIENTES", "filas": len(h)}
        except Exception as e:
            reporte["test_2_al30_historico"][sym] = {"status": "ERROR", "detalle": str(e)}

    # --- TEST 3: Verificar moneda financiera y FCF Yield en ADRs ---
    for adr in ["YPF", "VIST", "PAM", "LOMA"]:
        try:
            info = yf.Ticker(adr).info
            fcf = info.get("freeCashflow")
            mcap = info.get("marketCap")
            fin_curr = info.get("financialCurrency")
            curr = info.get("currency")
            raw_yield = round((fcf / mcap) * 100, 2) if (fcf and mcap) else None
            # Regla de saneamiento: solo válido si financialCurrency == currency y abs(yield) < 100%
            valido = (fin_curr == curr) and (raw_yield is not None) and (-100 < raw_yield < 100)
            reporte["test_3_saneamiento_adrs"][adr] = {
                "currency_cotizacion": curr,
                "currency_balance": fin_curr,
                "raw_fcf_yield_pct": raw_yield,
                "resultado_saneado": f"{raw_yield}%" if valido else "N/D (Descalce moneda)"
            }
        except Exception as e:
            reporte["test_3_saneamiento_adrs"][adr] = {"status": "ERROR", "detalle": str(e)}

    # --- TEST 4: Verificar P/E disponible en Merval Local ---
    for loc in ["GGAL.BA", "YPFD.BA", "EDN.BA", "SUPV.BA"]:
        try:
            info = yf.Ticker(loc).info
            pe = info.get("trailingPE")
            reporte["test_4_pe_merval_local"][loc] = round(float(pe), 2) if isinstance(pe, (int, float)) else "N/D"
        except:
            reporte["test_4_pe_merval_local"][loc] = "ERROR"

    return reporte

if __name__ == "__main__":
    res = ejecutar_test_correcciones()
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=4)
    print("Test completado.")
