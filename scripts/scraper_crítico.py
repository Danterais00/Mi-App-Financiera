import json
import requests
import yfinance as yf
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def buscar_dato_historico(datos, dias_atras):
    fecha_buscada = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
    return next((d for d in reversed(datos) if d["fecha"] <= fecha_buscada), None)

def ejecutar_test_v16():
    reporte = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "test_1_reservas_var_30d": {},
        "test_2_ccl_tendencia_30_90d": {},
        "test_3_valuacion_upside_peg": {},
        "test_4_liquidez_merval_usd": {}
    }

    # --- TEST 1: Reservas Brutas BCRA v4.0 (Actual vs hace ~22 ruedas / 30 días) ---
    try:
        r_bcra = requests.get("https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/1?limit=25", headers=HEADERS, verify=False, timeout=10)
        if r_bcra.status_code == 200:
            detalle = r_bcra.json().get("results", [{}])[0].get("detalle", [])
            if detalle:
                act = detalle[0]
                prev = detalle[-1]
                var_m = round(float(act["valor"]) - float(prev["valor"]))
                var_pct = round(((float(act["valor"]) / float(prev["valor"])) - 1) * 100, 2)
                reporte["test_1_reservas_var_30d"] = {
                    "status": "OK",
                    "actual": {"fecha": act["fecha"], "valor_m": round(float(act["valor"]))},
                    "anterior": {"fecha": prev["fecha"], "valor_m": round(float(prev["valor"]))},
                    "variacion_m": var_m,
                    "variacion_pct": var_pct
                }
    except Exception as e:
        reporte["test_1_reservas_var_30d"] = {"status": "ERROR", "msg": str(e)}

    # --- TEST 2: Tendencia Dólar CCL 30d y 90d ---
    ccl_actual = None
    try:
        r_ccl = requests.get("https://api.argentinadatos.com/v1/cotizaciones/dolares/contadoconliqui", headers=HEADERS, timeout=8)
        if r_ccl.status_code == 200:
            hist = r_ccl.json()
            if hist:
                ccl_actual = float(hist[-1]["venta"])
                d30 = buscar_dato_historico(hist, 30)
                d90 = buscar_dato_historico(hist, 90)
                var_30 = round(((ccl_actual / float(d30["venta"])) - 1) * 100, 2) if d30 else None
                var_90 = round(((ccl_actual / float(d90["venta"])) - 1) * 100, 2) if d90 else None
                reporte["test_2_ccl_tendencia_30_90d"] = {
                    "status": "OK",
                    "ccl_actual": ccl_actual,
                    "var_30d_pct": var_30,
                    "var_90d_pct": var_90
                }
    except Exception as e:
        reporte["test_2_ccl_tendencia_30_90d"] = {"status": "ERROR", "msg": str(e)}

    # --- TEST 3: Precio, Target Price, Upside (%) y PEG Ratio en USA y ADRs ---
    tickers_test = ["MSFT", "LLY", "XOM", "JPM", "VIST", "YPF", "GGAL", "BMA", "MELI"]
    for t in tickers_test:
        try:
            inf = yf.Ticker(t).info
            precio = inf.get("currentPrice") or inf.get("regularMarketPrice")
            target = inf.get("targetMeanPrice")
            peg = inf.get("pegRatio") or inf.get("trailingPegRatio")
            upside = round(((float(target) / float(precio)) - 1) * 100, 2) if (precio and target and precio > 0) else "N/D"
            reporte["test_3_valuacion_upside_peg"][t] = {
                "precio": round(float(precio), 2) if precio else "N/D",
                "target_price": round(float(target), 2) if target else "N/D",
                "upside_pct": f"{upside}%" if isinstance(upside, float) else upside,
                "peg_ratio": round(float(peg), 2) if isinstance(peg, (int, float)) else "N/D"
            }
        except Exception as e:
            reporte["test_3_valuacion_upside_peg"][t] = {"status": "ERROR", "msg": str(e)}

    # --- TEST 4: Liquidez diaria en USD (CCL) para acciones Merval ---
    if ccl_actual and ccl_actual > 0:
        for loc in ["YPFD.BA", "SUPV.BA", "EDN.BA", "HAVA.BA"]:
            try:
                h = yf.Ticker(loc).history(period="1mo")
                if not h.empty:
                    p = float(h["Close"].iloc[-1])
                    vol_20d = float(h["Volume"].dropna().tail(20).mean())
                    vol_ars_m = round((vol_20d * p) / 1_000_000, 2)
                    vol_usd_k = round(((vol_20d * p) / ccl_actual) / 1_000, 1)
                    reporte["test_4_liquidez_merval_usd"][loc] = {
                        "vol_20d_ars_m": f"${vol_ars_m} M",
                        "vol_20d_usd_k": f"USD {vol_usd_k} K"
                    }
            except Exception as e:
                reporte["test_4_liquidez_merval_usd"][loc] = {"status": "ERROR", "msg": str(e)}

    return reporte

if __name__ == "__main__":
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(ejecutar_test_v16(), f, indent=4, ensure_ascii=False)
