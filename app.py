if submitted:
        if nombre and usd_bruto > 0:
            try:
                # 1. Leer datos ignorando el caché para evitar conflictos
                df_actual = conn.read(ttl=0) 
                
                # 2. Crear la fila con tus columnas en MAYÚSCULAS
                nuevo_dato = pd.DataFrame([{
                    "FECHA_REGISTRO": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "PRODUCTO": nombre,
                    "TIENDA": tienda_custom if tienda == "CUSTOM" else tienda,
                    "USD_BRUTO": usd_bruto,
                    "USD_CON_8.25": usd_con_825,
                    "USD_FINAL_EQ": costo_total_mxn / tc_mercado,
                    "TC_MERCADO": tc_mercado,
                    "COMISION_PAGADA_MXN": comision_mxn,
                    "COSTO_TOTAL_MXN": costo_total_mxn,
                    "VENTA_MXN": venta_mxn,
                    "GANANCIA_MXN": ganancia,
                    "RANGO_SEMANA": rango_semana
                }])
                
                # 3. Concatenar y Subir
                df_final = pd.concat([df_actual, nuevo_dato], ignore_index=True)
                conn.update(data=df_final)
                
                st.balloons()
                st.success("✅ ¡Guardado exitosamente en la nube!")
                st.cache_data.clear() # Limpia la vista para mostrar lo nuevo
                
            except Exception as error_detallado:
                st.error(f"Error específico: {error_detallado}")
        else:
            st.warning("Escribe el nombre del producto y el costo.")