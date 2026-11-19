import json
import requests
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def test_reservas():
    res = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "fuentes": {}}

    # 1. Buscar en el catálogo oficial de Datos.gob.ar todas las series activas de "reservas internacionales"
    try:
        r_cat = requests.get("https://apis.datos.gob.ar/series/api/search/?q=reservas+internacionales&limit=10", headers=HEADERS, timeout=10)
        if r_cat.status_code == 200:
            items = r_cat.json().get("data", [])
            series_encontradas = []
            for it in items:
                f = it.get("field", {})
                series_encontradas.append({
                    "id": f.get("id"),
                    "titulo": f.get("title"),
                    "ultimo_dato_fecha": f.get("time_index_end"),
                    "frecuencia": f.get("frequency")
                })
            res["fuentes"]["1_catalogo_datos_gob"] = {"status": "OK", "series": series_encontradas}
        else:
            res["fuentes"]["1_catalogo_datos_gob"] = {"status": f"HTTP_{r_cat.status_code}"}
    except Exception as e:
        res["fuentes"]["1_catalogo_datos_gob"] = {"status": "ERROR", "msg": str(e)}

    # 2. Probar API BCRA v2.0 y v3.0 con Headers completos
    urls_bcra = [
        "https://api.bcra.gob.ar/estadisticas/v2.0/datosvariable/1/2026-10-01/2026-12-31",
        "https://api.bcra.gob.ar/estadisticas/v3.0/Monetarias/1?desde=2026-10-01&hasta=2026-12-31"
    ]
    for i, u in enumerate(urls_bcra):
        try:
            r = requests.get(u, headers=HEADERS, verify=False, timeout=10)
            res["fuentes"][f"2_bcra_{i}"] = {"status": r.status_code, "body": r.text[:300]}
        except Exception as e:
            res["fuentes"][f"2_bcra_{i}"] = {"status": "ERROR", "msg": str(e)}

    # 3. Probar endpoints alternativos de ArgentinaDatos / Bluelytics / CriptoYa / FinanzasArg
    urls_alt = [
        "https://api.argentinadatos.com/v1/finanzas/indices/reservas",
        "https://api.argentinadatos.com/v1/bcra/reservas",
        "https://mercados.ambito.com//reservas/variacion-diaria",
        "https://mercados.ambito.com//variaciones-mercado/general"
    ]
    for i, u in enumerate(urls_alt):
        try:
            r = requests.get(u, headers=HEADERS, timeout=10)
            res["fuentes"][f"3_alt_{i}"] = {"url": u, "status": r.status_code, "body": r.text[:300]}
        except Exception as e:
            res["fuentes"][f"3_alt_{i}"] = {"url": u, "status": "ERROR", "msg": str(e)}

    return res

if __name__ == "__main__":
    out = test_reservas()
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4, ensure_ascii=False)
