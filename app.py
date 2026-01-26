import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v6.0", layout="wide")
st.title("🚀 Calculadora y Gestor de Registros")

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# Tipo de Cambio
@st.cache_data(ttl=3600)
def obtener_tc():
    try:
        return round(requests.get("https://open.er-api.com/v6/latest/USD").json()["rates"]["MXN"], 2)
    except: return 18.50
tc_actual = obtener_tc()

# --- Sidebar: Entrada de Datos ---
with st.sidebar:
    st.header("📝 Nuevo Registro")
    nombre = st.text_input("PRODUCTO")
    tienda = st.selectbox("TIENDA", ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"])
    usd_bruto = st.number_input("COSTO USD (Sin Tax)", min_value=0.0, step=0.01)
    tc_mercado = st.number_input("TIPO DE CAMBIO", value=tc_actual, step=0.01)
    venta_mxn = st.number_input("VENTA FINAL (MXN)", min_value=0.0, step=0.01)
    
    col1, col2 = st.columns(2)
    btn_calcular = col1.button("CALCULAR")
    btn_guardar = col2.button("GUARDAR ✅")

# --- Lógica de Cálculos ---
usd_con_tax = usd_bruto * 1.0825
# Lógica pedida: (Total USD con Tax * 12%) * 19.5
comision_pagada_mxn = (usd_con_tax * 0.12) * 19.5
costo_total_mxn = (usd_con_tax * tc_mercado) + comision_pagada_mxn
usd_final_eq = costo_total_mxn / tc_mercado
ganancia_mxn = venta_mxn - costo_total_mxn

hoy = datetime.now()
lunes = hoy - timedelta(days=hoy.weekday())
domingo = lunes + timedelta(days=6)
rango_semanal = f"{lunes.strftime('%d/%m/%y')} al {domingo.strftime('%d/%m/%y')}"

# --- Acción: Mostrar Cálculo ---
if btn_calcular or btn_guardar:
    if usd_bruto > 0:
        st.info("### Resumen de Valores")
        c1, c2, c3 = st.columns(3)
        c1.metric("Comisión (12% @ 19.5)", f"${comision_pagada_mxn:,.2f} MXN")
        c2.metric("Inversión Total", f"${costo_total_mxn:,.2f} MXN")
        c3.metric("Ganancia Neta", f"${ganancia_mxn:,.2f} MXN")

# --- Acción: Guardar ---
if btn_guardar and nombre and usd_bruto > 0:
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
    # Forzamos que solo use las columnas definidas para evitar columnas extra
    df_final = pd.concat([df_actual, nuevo_registro], ignore_index=True)[nuevo_registro.columns]
    conn.update(data=df_final)
    st.success(f"✅ {nombre} guardado correctamente.")
    st.cache_data.clear()
    st.rerun()

# --- Sección de Historial y Eliminación ---
st.divider()
df_vista = conn.read(ttl=0)

if not df_vista.empty:
    col_h, col_e = st.columns([3, 1])
    
    with col_h:
        st.subheader("📋 Historial de Registros")
        st.dataframe(df_vista.sort_index(ascending=False), use_container_width=True)

    with col_e:
        st.subheader("🗑️ Borrar Registro")
        # Creamos una lista de opciones combinando índice y nombre del producto
        opciones_borrar = [f"{i} - {df_vista.loc[i, 'PRODUCTO']}" for i in df_vista.index]
        seleccion = st.selectbox("Selecciona cuál eliminar:", opciones_borrar)
        
        if st.button("ELIMINAR SELECCIONADO", fg_color="red"):
            indice_a_borrar = int(seleccion.split(" - ")[0])
            nombre_borrado = seleccion.split(" - ")[1]
            
            df_nuevo = df_vista.drop(indice_a_borrar)
            conn.update(data=df_nuevo)
            st.warning(f"Registro '{nombre_borrado}' eliminado.")
            st.cache_data.clear()
            st.rerun()