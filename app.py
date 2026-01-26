import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Configuración
st.set_page_config(page_title="Calculadora Pro", layout="wide")
st.title("🚀 Calculadora de Pedidos y Ganancias")

# Conexión
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Formulario
    with st.sidebar:
        st.header("Nuevo Registro")
        with st.form("registro_form", clear_on_submit=True):
            nombre = st.text_input("Nombre del Producto")
            tienda = st.selectbox("Tienda", ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "CUSTOM"])
            usd_bruto = st.number_input("Costo USD (Antes de Tax)", min_value=0.0)
            tc_mercado = st.number_input("Tipo de Cambio", value=18.50)
            venta_mxn = st.number_input("Precio Venta (MXN)", min_value=0.0)
            submitted = st.form_submit_button("CALCULAR Y GUARDAR")

    # Cálculos
    usd_con_825 = usd_bruto * 1.0825
    comision_mxn = (usd_con_825 * 0.12) * 19.5
    costo_total_mxn = (usd_con_825 * tc_mercado) + comision_mxn
    ganancia = venta_mxn - costo_total_mxn
    
    hoy = datetime.now()
    lunes = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)
    rango_semana = f"{lunes.strftime('%d/%m/%y')} al {domingo.strftime('%d/%m/%y')}"

    if submitted:
        df_actual = conn.read(ttl=0) # ttl=0 para forzar lectura fresca
        nuevo_dato = pd.DataFrame([{
            "FECHA_REGISTRO": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "PRODUCTO": nombre,
            "TIENDA": tienda,
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
        
        df_final = pd.concat([df_actual, nuevo_dato], ignore_index=True)
        conn.update(data=df_final)
        st.balloons()
        st.success("¡Guardado!")

    # Mostrar Historial
    st.subheader("Historial de Registros")
    df_historico = conn.read(ttl=0)
    st.dataframe(df_historico.sort_index(ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Error de conexión: Verifica que el Sheet sea 'Editor' y el Secret esté bien pegado.")