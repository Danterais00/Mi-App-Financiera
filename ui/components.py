import streamlit as st
import pandas as pd

def inyectar_css():
    st.markdown("""
    <style>
        .stApp { font-family: 'Inter', sans-serif; }
        .table-container { 
            overflow-x: auto; margin-bottom: 2.5rem; border-radius: 12px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.2); border: 1px solid #2a2e39; background-color: #12161f;
        }
        .custom-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 0.9rem; }
        .custom-table th { 
            background-color: #171b26; color: #a3a8b8; padding: 14px 15px; 
            border-bottom: 1px solid #2a2e39; font-weight: 600; white-space: nowrap;
            font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .custom-table td { padding: 12px 15px; border-bottom: 1px solid #1f2430; color: #e2e8f0; }
        .custom-table tr:last-child td { border-bottom: none; }
        .custom-table tr:hover td { background-color: #1a1f2b; transition: background-color 0.2s ease; }
        .col-header { font-weight: 600; background-color: #12161f !important; border-right: 1px solid #1f2430; color: #ffffff; }
        .col-ref { font-weight: 600; background-color: #161b26 !important; border-right: 1px solid #1f2430; color: #4d8bf0; font-size: 0.85rem; }
        .highlight-green { color: #2ecca6 !important; font-weight: bold; background-color: rgba(46, 204, 166, 0.05) !important;}
        .highlight-red { color: #ff6b6b !important; font-weight: bold; background-color: rgba(255, 107, 107, 0.05) !important;}
        
        /* --- ESTILOS DE LOGOS NUEVOS --- */
        .company-logo {
            width: 22px;
            height: 22px;
            border-radius: 50%;
            vertical-align: middle;
            margin-right: 8px;
            object-fit: cover;
            background-color: white;
            padding: 1px;
        }
        .top10-logo {
            width: 45px;
            height: 45px;
            border-radius: 50%;
            margin-bottom: 6px;
            object-fit: cover;
            background-color: white;
            padding: 2px;
            border: 2px solid #2a2e39;
        }
    </style>
    """, unsafe_allow_html=True)

TOOLTIPS = {
    "PER": "0-20: Rango razonable. Mide cuánto pagas por los beneficios del pasado.",
    "Forward P/E": "Mide cuánto pagas por los beneficios estimados del próximo año.",
    "PEG Ratio": "< 1.5 indica que la empresa está barata respecto a su crecimiento explosivo.",
    "EV/EBITDA": "Valor real de adquisición incluyendo deuda. < 12 es excelente.",
    "Payout Ratio (%)": "Porcentaje de ganancias destinado a pagar dividendos. > 70% es riesgoso.",
    "Short Interest (%)": "Porcentaje de acciones apostadas a la baja. > 10% indica pesimismo institucional.",
    "Consenso (1-5)": "1.0 = Fuerte Compra | 3.0 = Mantener | 5.0 = Fuerte Venta.",
    "Margen Neto (%)": "Porcentaje de ventas convertido en ganancia limpia.",
    "Gross Margin (%)": "Margen Bruto. Mide el foso económico (Moat).",
    "ROE (%)": "Rentabilidad sobre el capital de los accionistas.",
    "ROA (%)": "Rentabilidad sobre los activos totales.",
    "FCF Yield (%)": "Cuánto efectivo libre genera por cada dólar que cuesta la empresa.",
    "Debt/Equity": "Nivel de apalancamiento/deuda."
}

def formatear_moneda(n):
    if pd.isna(n) or n == 0: return "-"
    p = "$" if n >= 0 else "-$"
    num = abs(n)
    if num >= 1e12: return f"{p}{num/1e12:.2f}T"
    if num >= 1e9: return f"{p}{num/1e9:.2f}B"
    return f"{p}{num/1e6:.2f}M" if num >= 1e6 else f"{p}{num:,.2f}"
