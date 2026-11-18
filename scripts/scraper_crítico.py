import json
import requests
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def ejecutar_diagnostico_macro():
    print("Iniciando prueba de APIs Macroestructurales...")
    resultados = {"timestamp_prueba": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "pruebas_apis": {}}
    headers = {'User-Agent': 'Mozilla/5.0'}

    # 1. Prueba de Reservas Brutas (Buscando la FECHA exacta)
    try:
        r = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=300.1_AP_ACT_RESTER_0_M_21&limit=1&sort=desc&format=json", timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])[0]
            resultados["pruebas_apis"]["1_reservas_bcra"] = {
                "status": "OK", 
                "fecha_dato_oficial": data[0], 
                "valor_millones_usd": round(data[1] / 1_000_000) if data[1] > 1_000_000_000 else data[1]
            }
        else:
            resultados["pruebas_apis"]["1_reservas_bcra"] = {"status": "ERROR_API", "codigo": r.status_code}
    except Exception as e:
        resultados["pruebas_apis"]["1_reservas_bcra"] = {"status": "ERROR_TECNICO", "detalle": str(e)}

    # 2. Prueba de Riesgo País (Buscando el historial a 1 mes)
    try:
        r = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", headers=headers, timeout=10)
        if r.status_code == 200:
            datos_rp = r.json()
            ultimo = datos_rp[-1]
            
            # Calculamos la fecha de hace 30 días
            hace_un_mes = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            # Buscamos el dato más cercano a esa fecha hacia atrás
            previo = next((d for d in reversed(datos_rp) if d["fecha"] <= hace_un_mes), None)
            
            resultados["pruebas_apis"]["2_riesgo_pais_hist"] = {
                "status": "OK", 
                "dato_actual": ultimo, 
                "dato_hace_30_dias": previo
            }
        else:
            resultados["pruebas_apis"]["2_riesgo_pais_hist"] = {"status": "ERROR_API", "codigo": r.status_code}
    except Exception as e:
         resultados["pruebas_apis"]["2_riesgo_pais_hist"] = {"status": "ERROR_TECNICO", "detalle": str(e)}

    # 3. Prueba de Actividad Económica (EMAE - Rezago esperado)
    try:
        r = requests.get("https://apis.datos.gob.ar/series/api/series/?ids=143.3_NO_PR_2004_A_21&limit=1&sort=desc&format=json", timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])[0]
            resultados["pruebas_apis"]["3_actividad_emae"] = {
                "status": "OK", 
                "fecha_ultimo_dato_publicado": data[0], 
                "indice": data[1]
            }
        else:
            resultados["pruebas_apis"]["3_actividad_emae"] = {"status": "ERROR_API", "codigo": r.status_code}
    except Exception as e:
         resultados["pruebas_apis"]["3_actividad_emae"] = {"status": "ERROR_TECNICO", "detalle": str(e)}

    return resultados

if __name__ == "__main__":
    diag = ejecutar_diagnostico_macro()
    # Guardamos forzosamente en datos_criticos.json para poder leerlo desde GitHub
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(diag, f, indent=4)
    print("✅ Diagnóstico macroestructural finalizado con éxito.")
