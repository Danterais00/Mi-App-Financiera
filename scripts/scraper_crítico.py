import json
import requests
from datetime import datetime
# import bs4, curl_cffi # Puedes usar librerías pesadas aquí sin afectar a Streamlit

def extraer_datos_criticos():
    # Estructura del JSON que consumirá Streamlit
    datos = {
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "riesgo_pais_alternativo": None,
        "dolar_futuro_rofex": [],
        "curva_iamc": []
    }
    
    # 1. Aquí colocas tu lógica de web scraping dura (Rofex, IAMC, etc.)
    # Como este script corre en GitHub Actions, no tendrás el error de IP baneada.
    # Ejemplo simulado:
    try:
        # scraping_rofex = ...
        datos["dolar_futuro_rofex"] = [{"vencimiento": "Ene-25", "tna": "45.5"}]
    except Exception as e:
        print(f"Error en Rofex: {e}")

    return datos

if __name__ == "__main__":
    datos_extraidos = extraer_datos_criticos()
    
    # Guarda los datos en la raíz del repositorio
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(datos_extraidos, f, indent=4)
        
    print("✅ Archivo datos_criticos.json generado exitosamente.")
