import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v8.0", layout="wide")

# Estilo para mejorar la visualización de los inputs
st.markdown("""
    <style>
    .stNumberInput input { font-size: 18px; }
    .stTextInput input { font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

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

# --- SIDEBAR: REGISTRO Y ELIMINACIÓN ---
with st.sidebar:
    st.header("📝 Nuevo Registro")
    nombre = st.text_input("PRODUCTO")
    tienda = st.selectbox("TIENDA", ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"])
    
    # Inputs manuales (ahora aceptan escritura directa más cómoda)
    usd_bruto_txt = st.text_input("COSTO USD (Sin Tax)", value="0.00")
    tc_mercado_txt = st.text_input("TIPO DE CAMBIO", value=str(tc_actual))
    venta_mxn_txt = st.text_input("VENTA FINAL (MXN)", value="0.00")
    
    # Conversión segura de texto a número
    try:
        usd_bruto = float(usd_bruto_txt.replace(',', ''))
        tc_mercado = float(tc_mercado_txt.replace(',', ''))
        venta_mxn = float(venta_mxn_txt.replace(',', ''))
    except ValueError:
        usd_bruto = tc_mercado = venta_mxn = 0.0

    col1, col2 = st.columns(2)
    btn_calcular = col1.button("CALCULAR 🔍", use_container_width=True)
    btn_guardar = col2.button("GUARDAR ✅", use_container_width=True, type="primary")

    st.divider()
    
    # --- SECCIÓN ELIMINAR (AHORA AQUÍ ABAJO) ---
    st.header("🗑️ Borrar Registro")
    try:
        df_borrar = conn.read(ttl=0)
        if not df_borrar.empty:
            opciones = [f"{i} - {df_borrar.loc[i, 'PRODUCTO']}" for i in df_borrar.index]
            seleccion = st.selectbox("Selecciona para eliminar:", opciones)
            if st.button("ELIMINAR SELECCIONADO", use_container_width=True):
                indice = int(seleccion.split(" - ")[0])
                df_nuevo = df_borrar.drop(indice)
                conn.update(data=df_nuevo)
                st.warning("Registro eliminado.")
                st.cache_data.clear()
                st.rerun()
    except:
        st.write("Sin registros para eliminar.")

# --- LÓGICA DE CÁLCULOS ---
usd_con_tax = usd_bruto * 1.0825
# Comisión: (USD con Tax * 12%) * 19.5
comision_pagada_mxn = (usd_con_tax * 0.12) * 19.5
costo_total_mxn = (usd_con_tax * tc_mercado) + comision_pagada_mxn
usd_final_eq = costo_total_mxn / tc_mercado
ganancia_mxn = venta_mxn - costo_total_mxn

hoy = datetime.now()
lunes = hoy - timedelta(days=hoy.weekday())
domingo = lunes + timedelta(days=6)
rango_semanal = f"{lunes.strftime('%d/%m/%y')} al {domingo.strftime('%d/%m/%y')}"

# --- MOSTRAR RESULTADOS (Calculado y convertido a moneda) ---
if btn_calcular or (btn_guardar and nombre):
    if usd_bruto > 0:
        st.info(f"### Análisis de: {nombre}")
        c1, c2, c3 = st.columns(3)
        # Formateo a moneda visual
        c1.metric("Comisión (12% @ 19.5)", f"${comision_pagada_mxn:,.2f} MXN")
        c2.metric("Inversión Total", f"${costo_total_mxn:,.2f} MXN")
        c3.metric("Ganancia Neta", f"${ganancia_mxn:,.2f} MXN", 
                  delta=f"{((ganancia_mxn/costo_total_mxn)*100 if costo_total_mxn > 0 else 0):.1f}% Rentabilidad")

# --- GUARDAR EN NUBE ---
if btn_guardar and nombre and usd_bruto > 0:
    try:
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
        
        df_final = pd.concat([df_actual, nuevo_registro], ignore_index=True)
        conn.update(data=df_final)
        st.success(f"✅ ¡{nombre} guardado!")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- HISTORIAL COMPLETO ---
st.divider()
st.subheader("📋 Historial de Registros")
try:
    df_historial = conn.read(ttl=0)
    if not df_historial.empty:
        # Mostramos la tabla formateada para que los números se vean como moneda
        st.dataframe(df_historial.sort_index(ascending=False).style.format({
            "USD_BRUTO": "{:.2f}",
            "USD_CON_8.25": "{:.2f}",
            "USD_FINAL_EQ": "{:.2f}",
            "COMISION_PAGADA_MXN": "${:,.2f}",
            "COSTO_TOTAL_MXN": "${:,.2f}",
            "VENTA_MXN": "${:,.2f}",
            "GANANCIA_MXN": "${:,.2f}"
        }), use_container_width=True)
except:
    st.info("No hay datos para mostrar.")