@st.cache_data(ttl=1800)
def obtener_macro_argentina():
    # Estructura base para evitar que UI falle si algo falta
    datos_UI = {
        "dolares": [], "riesgo_pais": None, 
        "merval": {"valor": None},
        "merval_usd": {"valor": None},
        "bono_al30": {"valor": None},
        "inflacion": None, "tasa_bcra": None, "reservas": None
    }
    
    # 1. Obtenemos datos libres de bloqueos del Puente GitHub
    datos_puente = obtener_datos_criticos_puente()
    if datos_puente and "macro_arg_critica" in datos_puente:
        mc = datos_puente["macro_arg_critica"]
        datos_UI["dolares"] = mc.get("dolares", [])
        datos_UI["merval"]["valor"] = mc.get("merval_ars")
        datos_UI["merval_usd"]["valor"] = mc.get("merval_usd")
        datos_UI["bono_al30"]["valor"] = mc.get("bono_al30")
        datos_UI["tasa_bcra"] = mc.get("tasa_bcra")
        datos_UI["reservas"] = mc.get("reservas")

    # 2. Inflación y Riesgo País (Estos no sufren bloqueo, los mantenemos directos)
    try:
        res_rp = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais", headers=HEADERS, timeout=10)
        if res_rp.status_code == 200 and len(res_rp.json()) > 0:
            datos_UI["riesgo_pais"] = {"valor": res_rp.json()[-1]["valor"], "variacion": ""}
    except: pass

    try:
        res_inf = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", headers=HEADERS, timeout=10)
        if res_inf.status_code == 200 and len(res_inf.json()) > 0:
            datos_UI["inflacion"] = float(res_inf.json()[-1]["valor"]) 
    except: pass
    
    return datos_UI
