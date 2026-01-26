import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v10.0", layout="wide")

# Estilo visual
st.markdown("""
    <style>
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
    nombre = st.text_input("PRODUCTO", placeholder="Ej: Playera Hollister")
    tienda = st.selectbox("TIENDA", ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"])
    
    usd_bruto_txt = st.text_input("COSTO USD (Sin Tax)", placeholder="0.00")
    tc_mercado_txt = st.text_input("TIPO DE CAMBIO", value=str(tc_actual))
    venta_mxn_txt = st.text_input("VENTA FINAL (MXN)", placeholder="0.00")
    
    def limpiar_numero(texto):
        if not texto: return 0.0
        try: return float(texto.replace(',', '').replace('$', ''))
        except: return 0.0

    usd_bruto = limpiar_numero(usd_bruto_txt)
    tc_mercado = limpiar_numero(tc_mercado_txt)
    venta_mxn = limpiar_numero(venta_mxn_txt)

    btn_calcular = st.button("CALCULAR 🔍", use_container_width=True)
    btn_guardar = st.button("GUARDAR EN NUBE ✅", use_container_width=True, type="primary")

    st.divider()
    
    # --- SECCIÓN ELIMINAR CON CONFIRMACIÓN ---
    st.header("🗑️ Borrar Registro")
    try:
        df_borrar = conn.read(ttl=0)
        if not df_borrar.empty:
            opciones = [f"{i} - {df_borrar.loc[i, 'PRODUCTO']}" for i in reversed(df_borrar.index)]
            seleccion = st.selectbox("Selecciona para eliminar:", opciones)
            
            # Al dar clic, activamos el modo confirmación en la sesión
            if st.button("ELIMINAR SELECCIONADO", use_container_width=True):
                st.session_state.confirmar_borrado = True

            # Si el modo confirmación está activo, mostramos los botones extra
            if st.session_state.get('confirmar_borrado', False):
                st.warning(f"¿Estás seguro de eliminar '{seleccion.split(' - ')[1]}'? Esta acción no se puede deshacer.")
                col_c1, col_c2 = st.columns(2)
                
                if col_c1.button("SÍ, BORRAR", type="primary", use_container_width=True):
                    indice = int(seleccion.split(" - ")[0])
                    df_nuevo = df_borrar.drop(indice)
                    conn.update(data=df_nuevo)
                    st.session_state.confirmar_borrado = False # Resetear estado
                    st.cache_data.clear()
                    st.rerun()
                
                if col_c2.button("CANCELAR", use_container_width=True):
                    st.session_state.confirmar_borrado = False
                    st.rerun()
    except:
        st.write("Sin registros.")

# --- LÓGICA DE CÁLCULOS ---
usd_con_tax = usd_bruto * 1.0825
comision_pagada_mxn = (usd_con_tax * 0.12) * 19.5
costo_total_mxn = (usd_con_tax * tc_mercado) + comision_pagada_mxn
ganancia_mxn = venta_mxn - costo_total_mxn
usd_final_eq = costo_total_mxn / tc_mercado if tc_mercado > 0 else 0

hoy = datetime.now()
lunes = hoy - timedelta(days=hoy.weekday())
domingo = lunes + timedelta(days=6)
rango_semanal = f"{lunes.strftime('%d/%m/%y')} al {domingo.strftime('%d/%m/%y')}"

# --- MOSTRAR RESULTADOS ---
if (btn_calcular or btn_guardar) and usd_bruto > 0:
    st.info(f"### Análisis de: {nombre if nombre else 'Producto Nuevo'}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Comisión (12% @ 19.5)", f"${comision_pagada_mxn:,.2f} MXN")
    c2.metric("Inversión Total", f"${costo_total_mxn:,.2f} MXN")
    color_ganancia = "normal" if ganancia_mxn >= 0 else "inverse"
    c3.metric("Ganancia Neta", f"${ganancia_mxn:,.2f} MXN", 
              delta=f"{((ganancia_mxn/costo_total_mxn)*100 if costo_total_mxn > 0 else 0):.1f}%",
              delta_color=color_ganancia)

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
        st.success("✅ Guardado exitosamente.")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- HISTORIAL ---
st.divider()
st.subheader("📋 Historial de Registros")
try:
    df_historial = conn.read(ttl=0)
    if not df_historial.empty:
        st.dataframe(df_historial.sort_index(ascending=False), use_container_width=True)
except:
    st.info("No hay datos.")