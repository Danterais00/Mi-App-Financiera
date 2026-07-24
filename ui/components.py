import streamlit as st
import pandas as pd

def inyectar_css():
    st.markdown("""
    <style>
        /* Ajuste general para eliminar el negro puro y usar el tema global */
        .stApp { font-family: 'Inter', sans-serif; }
        
        /* Contenedores de tablas estilo 'Cards' de SmartFinance */
        .table-container { 
            overflow-x: auto; 
            margin-bottom: 2.5rem; 
            border-radius: 12px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            border: 1px solid #2a2e39;
            background-color: #12161f;
        }
        
        /* Estilos de las tablas suavizados */
        .custom-table { width: 100%; border-collapse: collapse; text-align: center; font-size: 0.9rem; }
        .custom-table th { 
            background-color: #171b26; 
            color: #a3a8b8; 
            padding: 14px 15px; 
            border-bottom: 1px solid #2a2e39; 
            font-weight: 600; 
            white-space: nowrap;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .custom-table td { padding: 12px 15px; border-bottom: 1px solid #1f2430; color: #e2e8f0; }
        .custom-table tr:last-child td { border-bottom: none; }
        .custom-table tr:hover td { background-color: #1a1f2b; transition: background-color 0.2s ease; }
        
        /* Columna fijada visualmente */
        .col-header { font-weight: 600; background-color: #12161f !important; border-right: 1px solid #1f2430; color: #ffffff; }

        /* Semáforos más modernos y menos agresivos */
        .highlight-green { color: #2ecca6 !important; font-weight: bold; background-color: rgba(46, 204, 166, 0.05) !important;}
        .highlight-red { color: #ff6b6b !important; font-weight: bold; background-color: rgba(255, 107, 107, 0.05) !important;}
    </style>
    """, unsafe_allow_html=True)

TOOLTIPS = {
    "PER": "0-10: Infravalorada. 10-17: Saludable. 17-25: Alto. >25: Crecimiento agresivo.",
    "Margen Neto (%)": "Eficiencia operativa. Porcentaje de ventas convertido en ganancia limpia.",
    "ROE (%)": "Rentabilidad sobre el capital de los accionistas.",
    "ROA (%)": "Rentabilidad sobre los activos totales.",
    "Free Cash Flow": "Caja libre tras gastos; dinero real para dividendos.",
    "Debt/Equity": "Nivel de apalancamiento/deuda.",
}

def formatear_moneda(n):
    if pd.isna(n) or n == 0: return "-"
    p = "$" if n >= 0 else "-$"
    num = abs(n)
    if num >= 1e12: return f"{p}{num/1e12:.2f}T"
    if num >= 1e9: return f"{p}{num/1e9:.2f}B"
    return f"{p}{num/1e6:.2f}M" if num >= 1e6 else f"{p}{num:,.2f}"
