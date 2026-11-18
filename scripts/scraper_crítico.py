import json
import re
import yfinance as yf
import requests
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def probar_nuevas_fuentes():
    """Diagnóstico para integrar Dólar Mayorista, Curva de Bonos (TIR), ForexFactory, Rofex y BCRA."""
    diagnostico = {}

    # 1. Dólar Mayorista (DolarAPI)
    try:
        r = requests.get("https://dolarapi.com/v1/dolares/mayorista", headers=HEADERS, timeout=10)
        diagnostico["mayorista"] = f"HTTP {r.status_code}"
        if r.status_code == 200:
            diagnostico["mayorista_data"] = r.json()
    except Exception as e:
        diagnostico["mayorista"] = f"ERR: {type(e).__name__}"

    # 2. Curva Bonos (Data912) - Verificando si existe la TIR
    try:
        r = requests.get("https://data912.com/live/arg_bonds", headers=HEADERS, timeout=10)
        diagnostico["bonos_largos"] = f"HTTP {r.status_code}"
        if r.status_code == 200:
            data = r.json()
            al35 = next((it for it in data if it.get("ticker") == "AL35" or it.get("symbol") == "AL35"), None)
            if al35:
                diagnostico["bonos_largos_al35_keys"] = list(al35.keys())
                diagnostico["bonos_largos_al35_sample"] = al35
    except Exception as e:
        diagnostico["bonos_largos"] = f"ERR: {type(e).__name__}"

    # 3. Datos Macro EE.UU. en tiempo real (ForexFactory XML)
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.xml", headers=HEADERS, timeout=10)
        diagnostico["forex_factory"] = f"HTTP {r.status_code}"
        if r.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.content)
            eventos = []
            for event in root.findall("event")[:10]:
                title = event.find("title").text if event.find("title") is not None else ""
                if "Retail Sales" in title or "CPI" in title:
                    eventos.append({
                        "title": title,
                        "actual": event.find("actual").text if event.find("actual") is not None else "",
                        "forecast": event.find("forecast").text if event.find("forecast") is not None else ""
                    })
            diagnostico["forex_factory_eventos"] = eventos
    except Exception as e:
        diagnostico["forex_factory"] = f"ERR: {type(e).__name__}"

    # 4. Futuros ROFEX (Rava)
    try:
        r = requests.get("https://www.rava.com/", headers=HEADERS, verify=False, timeout=10)
        diagnostico["rofex_rava"] = f"HTTP {r.status_code}"
        if r.status_code == 200:
            # Buscar ej: DOdic26 o DOene27
            rofex_matches = re.findall(r'DO[a-z]{3}\d{0,2}[^0-9]*?[\d\.\,]+', r.text, re.IGNORECASE)
            diagnostico["rofex_rava_matches"] = rofex_matches[:5]
    except Exception as e:
        diagnostico["rofex_rava"] = f"ERR: {type(e).__name__}"

    # 5. Intervención BCRA (Ámbito Noticias)
    try:
        r = requests.get("https://www.ambito.com/contenidos/dolar-bcra.html", headers=HEADERS, timeout=10)
        diagnostico["bcra_ambito"] = f"HTTP {r.status_code}"
        if r.status_code == 200:
            bcra_matches = re.findall(r'(?:BCRA|Central) (?:compró|vendió|adquirió).*?(?:US\$|dólares).*?millones', r.text, re.IGNORECASE)
            diagnostico["bcra_ambito_matches"] = bcra_matches[:5]
    except Exception as e:
        diagnostico["bcra_ambito"] = f"ERR: {type(e).__name__}"

    return diagnostico

def extraer_datos_criticos():
    print("Ejecutando diagnóstico de nuevas fuentes...")
    diag = probar_nuevas_fuentes()

    # Mantenemos los datos críticos mínimos para no romper el json
    datos = {
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "diagnostico_nuevas_fuentes": diag,
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
    return datos

if __name__ == "__main__":
    datos_extraidos = extraer_datos_criticos()
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(datos_extraidos, f, indent=4)
    print("✅ Archivo datos_criticos.json actualizado con diagnóstico.")
