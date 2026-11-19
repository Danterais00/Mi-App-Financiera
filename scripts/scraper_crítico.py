import json
import requests
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/html, */*'
}

def test_bcra_v4():
    res = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "pruebas": {}}
    urls = [
        ("bcra_v4_monetarias", "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/1?limit=2"),
        ("bcra_v4_listado", "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias"),
        ("ambito_bcra", "https://mercados.ambito.com//bcra/reservas/variacion-diaria"),
        ("ambito_dolar_res", "https://mercados.ambito.com//economia/reservas/variacion-diaria"),
        ("bcra_web_principales", "https://www.bcra.gob.ar/PublicacionesEstadisticas/Principales_variables.asp")
    ]
    for nombre, u in urls:
        try:
            r = requests.get(u, headers=HEADERS, verify=False, timeout=10)
            res["pruebas"][nombre] = {"status": r.status_code, "body": r.text[:450]}
        except Exception as e:
            res["pruebas"][nombre] = {"status": "ERROR", "msg": str(e)}
    return res

if __name__ == "__main__":
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(test_bcra_v4(), f, indent=4, ensure_ascii=False)
