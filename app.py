import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro", layout="wide")
st.title("🚀 Calculadora de Pedidos y Ganancias")

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# Tipo de Cambio
@st.cache_data(ttl=3600)
def obtener_tc():
    try:
        return round(requests.get("https://open.er-api.com/v6/latest/USD").json()["rates"]["MXN"], 2)
    except: return 18.50
tc_actual = obtener_tc()

# --- Interfaz de Entrada ---
with st.sidebar:
    st.header("Entrada de Datos")
    nombre = st.text_input("PRODUCTO")
    tienda = st.selectbox("TIENDA", ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"])
    usd_bruto = st.number_input("COSTO USD (Sin Tax)", min_value=0.0)
    tc_mercado = st.number_input("TIPO DE CAMBIO", value=tc_actual)
    venta_mxn = st.number_input("VENTA FINAL (MXN)", min_value=0.0)
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        btn_calcular = st.button("CALCULAR")
    with col_btn2:
        btn_guardar = st.button("GUARDAR ✅")

# --- Lógica de Cálculos ---
usd_con_tax = usd_bruto * 1.0825
# Comisión: (Total USD con Tax * 12%) * 19.5
comision_pagada_mxn = (usd_con_tax * 0.12) * 19.5
costo_total_mxn = (usd_con_tax * tc_mercado) + comision_pagada_mxn
usd_final_eq = costo_total_mxn / tc_mercado
ganancia_mxn = venta_mxn - costo_total_mxn

hoy = datetime.now()
lunes = hoy - timedelta(days=hoy.weekday())
domingo = lunes + timedelta(days=6)
rango_semanal = f"{lunes.strftime('%d/%m/%y')} al {domingo.strftime('%d/%m/%y')}"

# --- Acción: Calcular ---
if btn_calcular or btn_guardar:
    if usd_bruto > 0:
        st.info("### Resumen de Cálculo")
        c1, c2, c3 = st.columns(3)
        c1.metric("Comisión (12% @ 19.5)", f"${comision_pagada_mxn:,.2f} MXN")
        c2.metric("Inversión Total", f"${costo_total_mxn:,.2f} MXN")
        c3.metric("Ganancia Neta", f"${ganancia_mxn:,.2f} MXN")
    else:
        st.warning("Ingresa un costo para calcular.")

# --- Acción: Guardar ---
if btn_guardar:
    if nombre and usd_bruto > 0:
        df_actual = conn.read(ttl=0)
        nuevo_registro = pd.DataFrame([{
            "FECHA_REGISTRO": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "PRODUCTO": nombre,
            "TIENDA": tienda,
            "USD_BRUTO": usd_bruto,
            "USD_CON_8.25": usd_con_tax,
            "USD_FINAL_EQ": usd_final_eq,
            "TC_MERCADO": tc_mercado,
            "COMISION_PAGADA_MXN": comision_pagada_mxn,
            "COSTO_TOTAL_MXN": costo_total_mxn,
            "VENTA_MXN": venta_mxn,
            "GANANCIA_MXN": ganancia_mxn,
            "RANGO_SEMANA": rango_semanal
        }])
        # Solo concatenamos las columnas que existen en el nuevo registro para evitar extras
        df_final = pd.concat([df_actual, nuevo_registro], ignore_index=True)
        conn.update(data=df_final)
        st.success("¡Registro guardado!")
        st.cache_data.clear()
        st.rerun()

# --- Visualización y Eliminación ---
st.divider()
st.subheader("📋 Historial de Registros")
df_vista = conn.read(ttl=0)

if not df_vista.empty:
    st.dataframe(df_vista.sort_index(ascending=False), use_container_width=True)
    
    # Botón para eliminar el último
    if st.button("⚠️ ELIMINAR ÚLTIMO REGISTRO"):
        df_menos_uno = df_vista.drop(df_vista.index[-1])
        conn.update(data=df_menos_uno)
        st.warning("Registro eliminado.")
        st.cache_data.clear()
        st.rerun()