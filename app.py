import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu

# Importamos todas las funciones blindadas desde nuestro motor de datos
from data.news import (
    obtener_macro_argentina, 
    obtener_macro_internacional, 
    obtener_valuaciones_mercado, 
    obtener_datos_gics,
    obtener_datos_merval,       # NUEVA FUNCIÓN AGREGADA
    obtener_noticias_acciones, 
    generar_analisis_ia
)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Terminal de Decisiones de Inversión", layout="wide")

st.title("Terminal de Decisiones de Inversión")

# --- MENÚ DE NAVEGACIÓN ---
menu = option_menu(
    menu_title=None,
    options=[
        "Nivel 1: Macro", 
        "Nivel 2: Valuaciones", 
        "Nivel 3: Sectores GICS", 
        "Nivel 4: Merval",          # NUEVA PESTAÑA
        "Nivel 5: IA Cuantitativa", # IA DESPLAZADA AL NIVEL 5
        "Noticias Cartera"
    ],
    icons=['globe', 'bar-chart', 'pie-chart', 'graph-up', 'robot', 'newspaper'],
    default_index=0,
    orientation="horizontal",
)

# --- CARGA DE DATOS SILENCIOSA ---
# Se ejecutan en segundo plano y se guardan en caché para mantener la app rápida
macro_arg = obtener_macro_argentina()
macro_int = obtener_macro_internacional()
valuaciones = obtener_valuaciones_mercado()
gics = obtener_datos_gics()
merval = obtener_datos_merval()

# --- RENDERIZADO DE PESTAÑAS ---

if menu == "Nivel 1: Macro":
    st.header("🌍 Nivel 1: Tablero Macro")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Argentina")
        st.write(f"**Riesgo País:** {macro_arg.get('riesgo_pais', {}).get('valor', 'N/D')} pb")
        st.write(f"**Inflación Mensual:** {macro_arg.get('inflacion', 'N/D')}%")
        st.write(f"**Tasa Política Monetaria (BCRA):** {macro_arg.get('tasa_bcra', 'N/D')}%")
        if macro_arg.get("dolares"):
            st.write("**Cotizaciones Dólar:**")
            df_usd = pd.DataFrame(macro_arg["dolares"])
            st.dataframe(df_usd, hide_index=True)

    with col2:
        st.subheader("Internacional (EE.UU. y Global)")
        for clave, datos in macro_int.items():
            if datos.get("valor") is not None:
                st.write(f"**{clave}:** {datos['valor']}")

elif menu == "Nivel 2: Valuaciones":
    st.header("📊 Nivel 2: Mercado y Valuaciones Relativas")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("US Principales Índices y ETFs (USA)")
        if valuaciones.get("USA"):
            st.dataframe(pd.DataFrame(valuaciones["USA"]), hide_index=True, use_container_width=True)
            
    with col2:
        st.subheader("AR Principales ADRs (Argentina)")
        if valuaciones.get("ARG"):
            st.dataframe(pd.DataFrame(valuaciones["ARG"]), hide_index=True, use_container_width=True)

elif menu == "Nivel 3: Sectores GICS":
    st.header("🏢 Nivel 3: Rotación de Sectores GICS")
    if gics:
        st.dataframe(pd.DataFrame(gics), hide_index=True, use_container_width=True)

elif menu == "Nivel 4: Merval":
    st.header("📈 Nivel 4: Tablero de Control Merval y Panel General")
    
    # Procesamos los datos en un DataFrame
    df_merval = pd.DataFrame(merval)
    
    # Motor de Estilos (Semaforización)
    def aplicar_estilos_merval(df):
        def color_rsi(val):
            try:
                v = float(val)
                if v > 70: return 'color: #ff4b4b; font-weight: bold' # Rojo (Sobrecompra)
                elif v < 30: return 'color: #00ff00; font-weight: bold' # Verde (Sobreventa)
                return ''
            except: return ''
            
        def color_pbv(val):
            try:
                v = float(val)
                if v < 1: return 'color: #00ff00; font-weight: bold' # Verde (Cotiza bajo valor libro)
                return ''
            except: return ''

        return df.style.map(color_rsi, subset=['RSI']).map(color_pbv, subset=['P/BV'])

    # Renderizamos la tabla estilizada
    st.dataframe(aplicar_estilos_merval(df_merval), hide_index=True, use_container_width=True)
    
    # El Acordeón (Manual de Usuario)
    with st.expander("💡 ¿Cómo leer esta tabla para tomar decisiones? (El Método Práctico)", expanded=True):
        st.markdown("""
        Cuando mires un tablero como este en tu broker, aplica estos **3 filtros mentales** para decidir dónde poner tu dinero:

        ### 1. Buscar "Valor" (Filtro Fundamental)
        Busca empresas donde el mercado esté siendo pesimista pero la empresa gane dinero.
        *   **La regla:** Mira la columna `P/BV` y `P/E`.
        *   **Ejemplo en la tabla:** **TXAR** tiene un P/BV de 0.7x. Significa que el mercado la está valorando por menos del valor de sus fábricas y activos (está resaltado en verde). **CAPX** tiene un P/E de 3.8x, recuperas tu inversión rápido en términos de ganancias corporativas.

        ### 2. Buscar el "Momento de Entrada" (Filtro Técnico)
        Una empresa puede ser excelente (como YPF o TGSU2), pero si compras cuando todos están eufóricos, vas a perder plata en el corto plazo.
        *   **La regla:** Mira la columna `RSI`.
            *   🔴 **RSI > 70:** ¡No compres! Ya subió demasiado (Ej: TGSU2, YPFD). Si tienes, considera vender una parte.
            *   🟢 **RSI < 30:** Oportunidad. La acción cayó mucho y los vendedores están agotados (Ej: TXAR).
            *   ⚪ **RSI entre 40 y 60:** Zona neutral. Se compra si los fundamentos (P/E) son buenos (Ej: BMA, PAMP).

        ### 3. Asignar el Riesgo (Filtro de Liquidez)
        *   **La regla:** Mira la columna `Panel`.
        *   Si vas a invertir mucho dinero o vas a necesitar sacarlo rápido (para comprar un auto o una casa en 6 meses), solo opera el **Panel Principal**.
        *   Si tienes un dinero que no vas a tocar por 2 o 3 años, busca "joyas ocultas" en el **Panel General** (como BPAT o CAPX), sabiendo que cuando quieras vender, podrías tardar unos días en encontrar comprador a buen precio.
        """)

elif menu == "Nivel 5: IA Cuantitativa":
    st.header("🤖 Motor de Recomendación IA (Asesor Copilot)")
    st.write("El Asesor Financiero evaluará la Macro, las Valuaciones, los Sectores GICS y tu Tablero Merval para entregarte recomendaciones prácticas y operables.")
    
    if st.button("Generar Recomendaciones Automáticas", type="primary"):
        with st.spinner("Compilando todas las bases de datos en tiempo real..."):
            resultado_ia = generar_analisis_ia(macro_arg, macro_int, gics)
            st.markdown(resultado_ia, unsafe_allow_html=True)

elif menu == "Noticias Cartera":
    st.header("📰 Noticias del Mercado")
    st.info("Aquí puedes integrar tu flujo de noticias RSS.")
