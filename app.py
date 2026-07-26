# --- RENDERIZADO DE VISTAS ---

# EXTRAEMOS LAS NOTICIAS FUERA DEL CONDICIONAL DE "DATOS CARGADOS"
if menu_seccion == "Noticias de Mercado":
    st.header("Noticias de Mercado")
    tab_gen, tab_acc = st.tabs(["🌐 Información General de Mercado", "📰 Noticias de Acciones"])
    
    with tab_gen:
        col_arg, col_int = st.columns(2)
        
        with col_arg:
            st.subheader("🇦🇷 Mercado Argentino")
            with st.spinner("Sincronizando datos locales..."):
                macro_arg = obtener_macro_argentina()
                rp = macro_arg.get("riesgo_pais")
                merv = macro_arg.get("merval")
                
                # HTML SIN SANGRÍAS PARA EVITAR EL ERROR DE MARKDOWN
                html_arg = f"""<div style="background-color: #12161f; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39; margin-bottom:15px;">
<p style="margin:0; color:#a3a8b8; font-size:0.85rem; font-weight:bold;">RIESGO PAÍS JP MORGAN</p>
<h3 style="margin:5px 0; color:#fff;">{rp['valor'] if rp else 'N/D'} pts <span style="font-size:1rem; color:{'#ff6b6b' if rp and rp['variacion'].startswith('+') else '#2ecca6'};">({rp['variacion'] if rp else '-'})</span></h3>
<p style="margin:10px 0 0 0; color:#a3a8b8; font-size:0.85rem; font-weight:bold;">S&P MERVAL</p>
<h3 style="margin:5px 0; color:#fff;">{f"{merv['valor']:,.0f}" if merv else 'N/D'} <span style="font-size:1rem; color:{'#2ecca6' if merv and merv['var'] > 0 else '#ff6b6b'};">({f"{merv['var']:.2f}%" if merv else "-"})</span></h3>
</div>"""
                st.markdown(html_arg, unsafe_allow_html=True)
                
                st.markdown("#### Cotizaciones del Dólar")
                dolares = macro_arg.get("dolares", [])
                if dolares:
                    d_html = '<div class="table-container"><table class="custom-table"><tr><th>Tipo</th><th>Compra</th><th>Venta</th></tr>'
                    for d in dolares:
                        d_html += f"<tr><td class='col-header'>{d['nombre']}</td><td>${d['compra']}</td><td>${d['venta']}</td></tr>"
                    d_html += "</table></div>"
                    st.write(d_html, unsafe_allow_html=True)
                else:
                    st.info("Mercado local cerrado o API en mantenimiento.")

        with col_int:
            st.subheader("🌎 Mercado Internacional")
            with st.spinner("Sincronizando contexto global..."):
                macro_int = obtener_macro_internacional()
                for nombre, datos in macro_int.items():
                    color = "#2ecca6" if datos['var'] > 0 else "#ff6b6b"
                    simbolo = "▲" if datos['var'] > 0 else "▼"
                    html_int = f"""<div style="background-color: #12161f; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39; margin-bottom:15px; display:flex; justify-content:space-between; align-items:center;">
<div>
<p style="margin:0; color:#a3a8b8; font-size:0.85rem; font-weight:bold;">{nombre}</p>
<h3 style="margin:5px 0; color:#fff;">{datos['valor']:.2f}</h3>
</div>
<div style="text-align:right;">
<h4 style="margin:0; color:{color};">{simbolo} {abs(datos['var']):.2f}%</h4>
</div>
</div>"""
                    st.markdown(html_int, unsafe_allow_html=True)

    with tab_acc:
        st.subheader("📰 Titulares Recientes de tu Cartera")
        # CONDICIONAL: SOLO PIDE TICKERS SI ENTRAS A ESTA SUB-PESTAÑA
        if st.session_state.datos_cargados:
            with st.spinner("Rastreando agencias de noticias..."):
                noticias = obtener_noticias_acciones(st.session_state.tickers)
                for ticker, headlines in noticias.items():
                    if headlines:
                        st.markdown(f"#### 🔵 {ticker}")
                        for h in headlines:
                            st.markdown(f"""
                            <div style="background-color: #171b26; padding: 12px; border-radius: 6px; border-left: 4px solid #4d8bf0; margin-bottom:10px;">
                                <a href="{h['link']}" target="_blank" style="color: #e2e8f0; text-decoration: none; font-weight: 600; font-size: 0.95rem;">{h['titulo']}</a>
                                <p style="margin: 5px 0 0 0; color: #8ba1b6; font-size: 0.75rem;">{h['fecha']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        st.write("")
        else:
            st.info("👈 Ingresa los tickers y presiona 'Sincronizar Datos' para ver las noticias específicas de tus acciones.")

# --- LÓGICA PARA EL RESTO DE LAS VISTAS ---
else:
    # AHORA EL RESTO DEL CÓDIGO DEPENDE DE QUE HAYA DATOS CARGADOS
    if st.session_state.datos_cargados:
        dft = st.session_state.df_total
        
        if menu_seccion == "Datos y Valuación":
            # (Aquí va tu código actual de la sección Datos y Valuación)
            st.header("Valuación Futura y Perfil de Mercado")
            filas_mostrar = ["Empresa", "Precio", "Fair Value (Target)", "Upside (%)", "Beta", "Volumen Promedio", "Forward P/E", "PEG Ratio", "EV/EBITDA", "Consenso (1-5)"]
            filas_reales = [f for f in filas_mostrar if f in dft.index]
            df_val = dft.loc[filas_reales]
            h1 = '<div class="table-container"><table class="custom-table"><tr><th>Indicador</th>'
            for col in df_val.columns:
                logo_html = f'<img src="{st.session_state.analisis[col]["logo_url"]}" class="company-logo" onerror="this.style.display=\'none\'">' if col in st.session_state.analisis and st.session_state.analisis[col].get("logo_url") else ''
                h1 += f'<th>{logo_html}{col}</th>'
            h1 += '</tr>'
            for idx in df_val.index:
                t_text = TOOLTIPS.get(idx, "")
                sty = "cursor: help; border-bottom: 1px dotted #888;" if t_text else ""
                h1 += f'<tr><td class="col-header" title="{t_text}"><span style="{sty}">{idx}</span></td>'
                for col in df_val.columns:
                    val = df_val.loc[idx, col]; cls = ""
                    if pd.isna(val) or val is None: v_sh = "-"
                    elif idx == "Beta":
                        v_b = float(val)
                        v_sh = f"<span style='color:#2ecca6;'>⇠</span> {v_b:.2f}" if v_b <= 1 else f"<span style='color:#ffd54f;'>⇡</span> {v_b:.2f}" if v_b <= 1.5 else f"<span style='color:#ff6b6b;'>⇢</span> {v_b:.2f}"
                    elif idx == "Upside (%)":
                        v_sh = f"{float(val)*100:.2f}%"
                        if float(val) > 0: cls = "highlight-green"
                    elif idx in ["Precio", "Fair Value (Target)"]: v_sh = f"${float(val):,.2f}"
                    elif idx == "Consenso (1-5)":
                        v_c = float(val); v_sh = f"{v_c:.1f}"
                        if v_c <= 2.5: cls = "highlight-green"
                    elif idx == "Empresa": v_sh = f"<b>{val}</b>"
                    elif idx == "Volumen Promedio": v_sh = f"{float(val)/1e6:.2f}M"
                    else: 
                        v_sh = f"{float(val):.2f}"
                        if idx == "PEG Ratio" and float(val) < 1.5: cls = "highlight-green"
                        elif idx == "EV/EBITDA" and float(val) < 12: cls = "highlight-green"
                    h1 += f'<td class="{cls}">{v_sh}</td>'
                h1 += '</tr>'
            st.write(h1 + '</table></div>', unsafe_allow_html=True)
            
        # (Asegúrate de dejar el resto de tus bloques elif para Comparativa, Evolución, Técnico y Top 10 identados correctamente bajo este nivel)
        # elif menu_seccion == "Comparativa": ...
        # elif menu_seccion == "Evolución Financiera": ...
        # elif menu_seccion == "Análisis Técnico": ...
        # elif menu_seccion == "Top 10 Elite": ...

    else:
        # PANTALLA DE INICIO PARA LAS DEMÁS SECCIONES
        st.info("👈 Ingresa los tickers y presiona 'Sincronizar Datos' para comenzar el análisis.")
