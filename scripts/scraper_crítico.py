import json
import requests
import yfinance as yf
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def ejecutar_test_fcf_y_pbv():
    reporte = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ccl_referencia": None,
        "test_1_conversion_fcf_adrs": {},
        "test_2_pbv_bancos": {},
        "test_3_auditoria_tgs": {}
    }

    # Obtener Dólar CCL actual para conversión
    ccl = None
    try:
        rd = requests.get("https://dolarapi.com/v1/dolares", timeout=8)
        if rd.status_code == 200:
            for d in rd.json():
                if d.get("casa", "").lower() == "contadoconliqui":
                    ccl = float(d.get("venta"))
                    reporte["ccl_referencia"] = ccl
                    break
    except Exception as e:
        reporte["ccl_referencia"] = f"ERROR: {e}"

    # TEST 1: Probar conversión FCF (ARS -> USD via CCL) en ADRs descalzados
    adrs_test = ["YPF", "TGS", "CEPU", "LOMA", "CRESY", "IRS", "VIST", "PAM"]
    for t in adrs_test:
        try:
            info = yf.Ticker(t).info
            fcf = info.get("freeCashflow")
            mcap = info.get("marketCap")
            curr = info.get("currency")
            fin_curr = info.get("financialCurrency")

            if isinstance(fcf, (int, float)) and isinstance(mcap, (int, float)) and mcap > 0:
                if fin_curr == curr:
                    fcf_usd = fcf
                    metodo = "Directo (USD)"
                elif fin_curr == "ARS" and curr == "USD" and ccl and ccl > 0:
                    fcf_usd = fcf / ccl
                    metodo = f"Convertido ARS->USD (CCL {ccl})"
                else:
                    fcf_usd = None
                    metodo = "Sin conversión posible"

                yield_final = round((fcf_usd / mcap) * 100, 2) if fcf_usd is not None else "N/D"
                reporte["test_1_conversion_fcf_adrs"][t] = {
                    "monedas": f"{fin_curr} -> {curr}",
                    "metodo": metodo,
                    "fcf_yield_calculado": f"{yield_final}%" if isinstance(yield_final, float) else yield_final
                }
            else:
                reporte["test_1_conversion_fcf_adrs"][t] = {"status": "SIN_FCF_EN_YAHOO"}
        except Exception as e:
            reporte["test_1_conversion_fcf_adrs"][t] = {"status": "ERROR", "msg": str(e)}

    # TEST 2: Verificar P/BV en Bancos (JPM, GGAL, BMA)
    for b in ["JPM", "GGAL", "BMA"]:
        try:
            info = yf.Ticker(b).info
            pb = info.get("priceToBook")
            reporte["test_2_pbv_bancos"][b] = {
                "P/BV": round(float(pb), 2) if isinstance(pb, (int, float)) else "N/D",
                "ROE": f"{info.get('returnOnEquity')*100:.1f}%" if isinstance(info.get('returnOnEquity'), (int, float)) else "N/D"
            }
        except Exception as e:
            reporte["test_2_pbv_bancos"][b] = {"status": "ERROR", "msg": str(e)}

    # TEST 3: Auditar EV/EBITDA negativo en TGS
    try:
        info_tgs = yf.Ticker("TGS").info
        reporte["test_3_auditoria_tgs"] = {
            "enterpriseValue": info_tgs.get("enterpriseValue"),
            "ebitda": info_tgs.get("ebitda"),
            "enterpriseToEbitda": info_tgs.get("enterpriseToEbitda"),
            "financialCurrency": info_tgs.get("financialCurrency")
        }
    except Exception as e:
        reporte["test_3_auditoria_tgs"] = {"status": "ERROR", "msg": str(e)}

    return reporte

if __name__ == "__main__":
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(ejecutar_test_fcf_y_pbv(), f, indent=4, ensure_ascii=False)
