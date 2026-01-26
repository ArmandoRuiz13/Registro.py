import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v11.0", layout="wide")

# Estilo visual
st.markdown("<style>.stTextInput input { font-size: 18px; }</style>", unsafe_allow_html=True)

st.title("🚀 Calculadora y Control de Pagos")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=3600)
def obtener_tc():
    try: return round(requests.get("https://open.er-api.com/v6/latest/USD").json()["rates"]["MXN"], 2)
    except: return 18.50
tc_actual = obtener_tc()

# --- SIDEBAR: REGISTRO Y ACTUALIZACIÓN ---
with st.sidebar:
    st.header("📝 Nuevo Registro")
    nombre = st.text_input("PRODUCTO", placeholder="Ej: Tenis Nike")
    tienda = st.selectbox("TIENDA", ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"])
    
    usd_bruto_txt = st.text_input("COSTO USD (Sin Tax)", placeholder="0.00")
    tc_mercado_txt = st.text_input("TIPO DE CAMBIO", value=str(tc_actual))
    venta_mxn_txt = st.text_input("VENTA FINAL (MXN)", placeholder="0.00")
    
    # Nuevos campos de pago
    estado_pago = st.selectbox("ESTADO DE PAGO", ["Debe", "Abonado", "Pagado"])
    
    def limpiar_numero(texto):
        if not texto: return 0.0
        try: return float(texto.replace(',', '').replace('$', ''))
        except: return 0.0

    usd_bruto = limpiar_numero(usd_bruto_txt)
    tc_mercado = limpiar_numero(tc_mercado_txt)
    venta_mxn = limpiar_numero(venta_mxn_txt)

    # Lógica de Monto Recibido
    usd_con_tax = usd_bruto * 1.0825
    comision_mxn = (usd_con_tax * 0.12) * 19.5
    costo_total_mxn = (usd_con_tax * tc_mercado) + comision_mxn
    
    if estado_pago == "Pagado":
        monto_recibido = costo_total_mxn
        st.caption(f"Se registrará pago total: ${monto_recibido:,.2f}")
    elif estado_pago == "Abonado":
        monto_recibido = st.number_input("¿Cuánto abonó?", min_value=0.0, step=100.0)
    else:
        monto_recibido = 0.0

    btn_guardar = st.button("GUARDAR EN NUBE ✅", use_container_width=True, type="primary")

    st.divider()
    
    # --- SECCIÓN ELIMINAR ---
    st.header("🗑️ Borrar Registro")
    df_actual = conn.read(ttl=0)
    if not df_actual.empty:
        opciones = [f"{i} - {df_actual.loc[i, 'PRODUCTO']}" for i in reversed(df_actual.index)]
        seleccion = st.selectbox("Selecciona para eliminar:", opciones)
        if st.button("ELIMINAR SELECCIONADO", use_container_width=True):
            indice = int(seleccion.split(" - ")[0])
            conn.update(data=df_actual.drop(indice))
            st.cache_data.clear()
            st.rerun()

# --- CÁLCULOS ADICIONALES ---
ganancia_mxn = venta_mxn - costo_total_mxn
usd_final_eq = costo_total_mxn / tc_mercado if tc_mercado > 0 else 0
rango_semanal = f"{(datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%d/%m/%y')} al {((datetime.now() - timedelta(days=datetime.now().weekday())) + timedelta(days=6)).strftime('%d/%m/%y')}"

# --- GUARDAR ---
if btn_guardar and nombre and usd_bruto > 0:
    nuevo_registro = pd.DataFrame([{
        "FECHA_REGISTRO": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "PRODUCTO": nombre,
        "TIENDA": tienda,
        "USD_BRUTO": usd_bruto,
        "USD_CON_8.25": usd_con_tax,
        "USD_FINAL_EQ": usd_final_eq,
        "TC_MERCADO": tc_mercado,
        "COMISION_PAGADA_MXN": comision_mxn,
        "COSTO_TOTAL_MXN": costo_total_mxn,
        "VENTA_MXN": venta_mxn,
        "GANANCIA_MXN": ganancia_mxn,
        "RANGO_SEMANA": rango_semanal,
        "ESTADO_PAGO": estado_pago,
        "MONTO_RECIBIDO": monto_recibido
    }])
    conn.update(data=pd.concat([df_actual, nuevo_registro], ignore_index=True))
    st.success("✅ Guardado con éxito")
    st.cache_data.clear()
    st.rerun()

# --- HISTORIAL ---
st.divider()
st.subheader("📋 Historial de Registros y Cobranza")
df_historial = conn.read(ttl=0)
if not df_historial.empty:
    # Formatear la tabla para resaltar los estados
    def color_estado(val):
        color = '#ff4b4b' if val == 'Debe' else '#f9d71c' if val == 'Abonado' else '#09ab3b'
        return f'color: {color}; font-weight: bold'
    
    st.dataframe(df_historial.sort_index(ascending=False).style.applymap(color_estado, subset=['ESTADO_PAGO']), use_container_width=True)