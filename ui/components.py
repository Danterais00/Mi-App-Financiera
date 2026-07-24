import streamlit as st
import pandas as pd

def inyectar_css():
    st.markdown("""
    <style>
        .stApp { background-color: #000000; color: #e0e0e0; font-family: 'Inter', sans-serif; }
        .table-container { overflow-x: auto; margin-bottom: 2rem; border-radius: 8px; border: 1px solid #333; }
        .custom-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 0.9rem; background-color: #0a0a0a; }
        .custom-table th { background-color: #1a1a1a; color: #ffffff; padding: 12px 15px; border-bottom: 2px solid #333; font-weight: 600; white-space: nowrap; }
        .custom-table td { padding: 10px 15px; border-bottom: 1px solid #222; color: #d1d1d1; }
        .custom-table tr:hover td { background-color: #1a1c23; transition: background-color 0.2s ease; }
        .col-header { font-weight: bold; background-color: #111 !important; border-right: 1px solid #333; }
        .highlight-green { background-color: rgba(46, 125, 50, 0.2) !important; color: #81c784 !important; font-weight: bold; }
        .highlight-red { background-color: rgba(198, 40, 40, 0.2) !important; color: #e57373 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Diccionario de definiciones para los Tooltips
TOOLTIPS = {
    "PER": "0-10: Infravalorada. 10-17: Saludable. 17-25: Alto. >25: Crecimiento agresivo.",
    "Margen Neto (%)": "Eficiencia operativa. Porcentaje de ventas convertido en ganancia limpia.",
    "ROE (%)": "Rentabilidad sobre el capital de los accionistas.",
    "ROA (%)": "Rentabilidad sobre los activos totales.",
    "Free Cash Flow": "Caja libre tras gastos; dinero real para dividendos.",
    "Debt/Equity": "Nivel de apalancamiento/deuda.",
}

def formatear_moneda(n):
    """Convierte números largos en formato $ Billions o Millions"""
    if pd.isna(n) or n == 0: return "-"
    p = "$" if n >= 0 else "-$"
    num = abs(n)
    if num >= 1e12: return f"{p}{num/1e12:.2f}T"
    if num >= 1e9: return f"{p}{num/1e9:.2f}B"
    return f"{p}{num/1e6:.2f}M" if num >= 1e6 else f"{p}{num:,.2f}"
