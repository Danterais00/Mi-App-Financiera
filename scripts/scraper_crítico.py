import json
import yfinance as yf
from datetime import datetime

def extraer_datos_criticos():
    print("Iniciando extracción de datos críticos desde GitHub Actions...")
    datos = {
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dolar_futuro_rofex": [],
        "cotizaciones_merval": {},
        "valuaciones_usa": {},
        "valuaciones_arg": {}
    }
    
    # 1. Simulación Rofex (Como estaba antes)
    try:
        datos["dolar_futuro_rofex"] = [{"vencimiento": "Ene-25", "tna": "45.5"}]
    except Exception as e:
        print(f"Error en Rofex: {e}")

    # 2. Extracción Merval (Eludiendo el bloqueo de Streamlit)
    lider = ["ALUA.BA", "BBAR.BA", "BMA.BA", "BYMA.BA", "CEPU.BA", "COME.BA", "CRES.BA", 
             "CVH.BA", "EDN.BA", "GGAL.BA", "IRSA.BA", "LOMA.BA", "MIRG.BA", "PAMP.BA", 
             "SUPV.BA", "TECO2.BA", "TGNO4.BA", "TGSU2.BA", "TRAN.BA", "TXAR.BA", "VALO.BA", "YPFD.BA"]
    
    # Panel General Reducido (Solo activos con volumen histórico aceptable)
    general = ["AGRO.BA", "AUSO.BA", "BHIP.BA", "BOLT.BA", "BPAT.BA", "CAPX.BA", "CECO2.BA", 
               "CELU.BA", "CGPA2.BA", "DGCU2.BA", "FERR.BA", "GBAN.BA", "GCLA.BA", 
               "HAVA.BA", "INVJ.BA", "LEDE.BA", "METR.BA", "MOLI.BA", "MORI.BA", "OEST.BA", "SAMI.BA"]
    
    todos_merval = lider + general
    print(f"Descargando historial Merval para {len(todos_merval)} tickers...")
    
    try:
        # Descarga masiva rápida
        hist = yf.download(todos_merval, period="3mo", progress=False)
        df_close = hist['Close'] if 'Close' in hist else None
        
        if df_close is not None:
            for ticker in todos_merval:
                if ticker in df_close.columns:
                    serie = df_close[ticker].dropna()
                    if len(serie) >= 20: # Necesario para medias móviles
                        precio_actual = float(serie.iloc[-1])
                        sma20 = float(serie.rolling(window=20).mean().iloc[-1])
                        
                        # Cálculo simple RSI
                        delta = serie.diff()
                        gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
                        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        rsi_val = float(rsi.iloc[-1]) if not rsi.empty else None
                        
                        # Obtener Info Fundamental (Solo P/E y P/BV para Panel Líder)
                        info = yf.Ticker(ticker).info
                        vol = info.get("averageVolume", 0)
                        
                        pe, pb = None, None
                        if ticker in lider:
                            pe = info.get("trailingPE") or info.get("forwardPE")
                            pb = info.get("priceToBook")
                        
                        datos["cotizaciones_merval"][ticker] = {
                            "precio": precio_actual,
                            "sma20": sma20,
                            "rsi": round(rsi_val, 2) if rsi_val else None,
                            "volumen_m": round(vol / 1_000_000, 2) if vol else None,
                            "pe": round(pe, 2) if isinstance(pe, (int, float)) else None,
                            "pbv": round(pb, 2) if isinstance(pb, (int, float)) else None
                        }
        print("Merval descargado exitosamente.")
    except Exception as e:
        print(f"Error descargando Merval: {e}")

    # 3. Valuaciones Relativas (ADRs y Empresas Individuales de USA)
    activos_arg = {"YPF": "Energía", "GGAL": "Financiero", "BMA": "Financiero", "PAM": "Energía", "CEPU": "Utilities"}
    activos_usa = {"AAPL": "Tecnología", "MSFT": "Tecnología", "JPM": "Financiero", "XOM": "Energía", "UNH": "Salud"} # Reemplazamos ETFs por empresas líderes
    
    print("Descargando valuaciones fundamentales...")
    for ticker, sector in activos_arg.items():
        try:
            info = yf.Ticker(ticker).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            roe = info.get("returnOnEquity")
            datos["valuaciones_arg"][ticker] = {
                "Sector": sector,
                "P/E": round(pe, 2) if isinstance(pe, (int, float)) else "N/D",
                "ROE (%)": f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D",
            }
        except: pass
        
    for ticker, sector in activos_usa.items():
        try:
            info = yf.Ticker(ticker).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            roe = info.get("returnOnEquity")
            datos["valuaciones_usa"][ticker] = {
                "Sector": sector,
                "P/E": round(pe, 2) if isinstance(pe, (int, float)) else "N/D",
                "ROE (%)": f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/D",
            }
        except: pass
        
    print("Valuaciones fundamentales descargadas.")

    return datos

if __name__ == "__main__":
    datos_extraidos = extraer_datos_criticos()
    with open("datos_criticos.json", "w", encoding="utf-8") as f:
        json.dump(datos_extraidos, f, indent=4)
    print("✅ Archivo datos_criticos.json actualizado exitosamente.")
