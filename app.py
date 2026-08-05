import streamlit as st
import pandas as pd
import yfinance as yf
from streamlit_option_menu import option_menu

# Importamos todas las funciones blindadas desde nuestro motor de datos
from data.news import (
    obtener_macro_argentina, 
    obtener_macro_internacional, 
    obtener_valuaciones_mercado, 
    obtener_datos_gics,
    obtener_datos_merval,
    obtener_noticias_acciones, 
    generar_analisis_ia
)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SmartInvest - Terminal", layout="wide")

st.title("SmartInvest - Terminal de Decisiones de Inversión")

# --- MENÚ DE NAVEGACIÓN ---
menu = option_menu(
    menu_title=None,
    options=[
        "Nivel 1: Macro", 
        "Nivel 2: Valuaciones", 
        "Nivel 3: Sectores GICS", 
        "Nivel 4: Merval",
        "Nivel 5: IA Cuantitativa", 
        "Top 10",
        "Análisis de Tickers",
        "Noticias Cartera"
    ],
    icons=['globe', 'bar-chart', 'pie-chart', 'graph-up', 'robot', 'trophy', 'search', 'newspaper'],
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
            *   🔴 **RSI > 70:** ¡No compres! Ya subió demasiado. Si tienes, considera vender una parte.
            *   🟢 **RSI < 30:** Oportunidad. La acción cayó mucho y los vendedores están agotados.
            *   ⚪ **RSI entre 40 y 60:** Zona neutral. Se compra si los fundamentos (P/E) son buenos.

        ### 3. Asignar el Riesgo (Filtro de Liquidez)
        *   **La regla:** Mira la columna `Panel`.
        *   Si vas a invertir mucho dinero o vas a necesitar sacarlo rápido, solo opera el **Panel Principal**.
        *   Si tienes un dinero que no vas a tocar por 2 o 3 años, busca "joyas ocultas" en el **Panel General**.
        """)

elif menu == "Nivel 5: IA Cuantitativa":
    st.header("🤖 Motor de Recomendación IA (Asesor Copilot)")
    st.write("El Asesor Financiero evaluará la Macro, las Valuaciones, los Sectores GICS y tu Tablero Merval para entregarte recomendaciones prácticas y operables.")
    
    if st.button("Generar Recomendaciones Automáticas", type="primary"):
        with st.spinner("Compilando todas las bases de datos en tiempo real..."):
            resultado_ia = generar_analisis_ia(macro_arg, macro_int, gics)
            st.markdown(resultado_ia, unsafe_allow_html=True)

# --- SECCIONES RESTAURADAS DE SMARTINVEST ---

elif menu == "Top 10":
    st.header("🏆 Top 10: Mejores Oportunidades")
    st.write("Clasificación de los mejores activos según nuestro Score Cuantitativo y análisis de valuación.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sectores Globales (GICS)")
        if gics:
            # Ordenamos por nuestro Score Quant interno
            df_gics = pd.DataFrame(gics).sort_values(by="Score", ascending=False).head(10)
            st.dataframe(df_gics[['Sector', 'ETF', 'Score', '1M (%)']], hide_index=True, use_container_width=True)
            
    with col2:
        st.subheader("Oportunidades Locales (Merval)")
        if merval:
            # Buscamos activos sobrevendidos y baratos
            df_m = pd.DataFrame(merval).sort_values(by=["RSI", "P/BV"]).head(10)
            st.dataframe(df_m[['Ticker', 'Empresa', 'RSI', 'P/BV', 'Tendencia']], hide_index=True, use_container_width=True)

elif menu == "Análisis de Tickers":
    st.header("🔍 Análisis Individual de Tickers")
    st.write("Consulta datos históricos, gráficos y ratios fundamentales de cualquier acción.")
    
    ticker_input = st.text_input("Ingresa un Ticker (Ej: AAPL, SPY, o YPFD.BA para locales):", "SPY")
    
    if ticker_input:
        try:
            with st.spinner(f"Analizando {ticker_input}..."):
                stock_data = yf.Ticker(ticker_input)
                hist_data = stock_data.history(period="6mo")
                
                if not hist_data.empty:
                    st.subheader(f"Evolución de Precio - {ticker_input.upper()} (Últimos 6 Meses)")
                    st.line_chart(hist_data['Close'])
                    
                    st.write("**Métricas Clave:**")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    precio_actual = hist_data['Close'].iloc[-1]
                    precio_ayer = hist_data['Close'].iloc[-2]
                    var_diaria = ((precio_actual / precio_ayer) - 1) * 100
                    
                    col1.metric("Precio Actual", f"${precio_actual:.2f}")
                    col2.metric("Var. Diaria", f"{var_diaria:.2f}%", f"{var_diaria:.2f}%")
                    
                    info = stock_data.info
                    pe_ratio = info.get("trailingPE", info.get("forwardPE", "N/D"))
                    if isinstance(pe_ratio, float): pe_ratio = f"{pe_ratio:.2f}"
                    col3.metric("P/E Ratio", pe_ratio)
                    
                    dy = info.get('dividendYield', 0)
                    col4.metric("Div. Yield", f"{dy*100:.2f}%" if dy else "N/D")
                    
                    with st.expander(f"Ver Resumen del Negocio ({ticker_input.upper()})"):
                        st.write(info.get("longBusinessSummary", "No hay descripción disponible para esta empresa."))
                else:
                    st.warning("No se encontraron datos. Si es una acción argentina, recuerda agregar '.BA' al final (ej: GGAL.BA).")
        except Exception as e:
            st.error(f"Ocurrió un error al conectar con el mercado: {e}")

elif menu == "Noticias Cartera":
    st.header("📰 Noticias del Mercado")
    st.write("Últimas novedades financieras de los activos más relevantes.")
    
    # Lista predeterminada de seguimiento global
    tickers_cartera = ["SPY", "QQQ", "AAPL", "MSFT", "XLE", "XLF"]
    
    with st.spinner("Descargando noticias de fuentes RSS..."):
        noticias_data = obtener_noticias_acciones(tickers_cartera)
        
        for t, lista_n in noticias_data.items():
            if lista_n:
                with st.expander(f"🗞️ Noticias sobre {t}", expanded=True):
                    for n in lista_n:
                        st.markdown(f"- [{n['titulo']}]({n['link']})")
