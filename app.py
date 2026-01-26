import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v12.0", layout="wide")

# Estilo para inputs
st.markdown("<style>.stTextInput input { font-size: 18px; }</style>", unsafe_allow_html=True)

st.title("🚀 Calculadora y Control de Pagos Editable")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=3600)
def obtener_tc():
    try: return round(requests.get("https://open.er-api.com/v6/latest/USD").json()["rates"]["MXN"], 2)
    except: return 18.50
tc_actual = obtener_tc()

# --- SIDEBAR: REGISTRO ---
with st.sidebar:
    st.header("📝 Nuevo Registro")
    nombre = st.text_input("PRODUCTO", placeholder="Ej: Tenis Nike")
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

    # Botones separados como pediste
    btn_calcular = st.button("CALCULAR 🔍", use_container_width=True)
    btn_guardar = st.button("GUARDAR EN NUBE ✅", use_container_width=True, type="primary")

    st.divider()
    
    # --- SECCIÓN ELIMINAR ---
    st.header("🗑️ Borrar Registro")
    df_actual = conn.read(ttl=0)
    if not df_actual.empty:
        opciones = [f"{i} - {df_actual.loc[i, 'PRODUCTO']}" for i in reversed(df_actual.index)]
        seleccion = st.selectbox("Selecciona para eliminar:", opciones)
        if st.button("ELIMINAR SELECCIONADO", use_container_width=True):
            conn.update(data=df_actual.drop(int(seleccion.split(" - ")[0])))
            st.cache_data.clear()
            st.rerun()

# --- LÓGICA DE CÁLCULOS ---
usd_con_tax = usd_bruto * 1.0825
comision_mxn = (usd_con_tax * 0.12) * 19.5
costo_total_mxn = (usd_con_tax * tc_mercado) + comision_mxn
ganancia_mxn = venta_mxn - costo_total_mxn
usd_final_eq = costo_total_mxn / tc_mercado if tc_mercado > 0 else 0
rango_semanal = f"{(datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%d/%m/%y')} al {((datetime.now() - timedelta(days=datetime.now().weekday())) + timedelta(days=6)).strftime('%d/%m/%y')}"

# --- ACCIÓN: CALCULAR ---
if btn_calcular and usd_bruto > 0:
    st.info(f"### Análisis de: {nombre}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Comisión (12% @ 19.5)", f"${comision_mxn:,.2f} MXN")
    c2.metric("Inversión Total", f"${costo_total_mxn:,.2f} MXN")
    c3.metric("Ganancia Neta", f"${ganancia_mxn:,.2f} MXN")

# --- ACCIÓN: GUARDAR ---
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
        "ESTADO_PAGO": "Debe",  # Por defecto siempre debe
        "MONTO_RECIBIDO": 0.0
    }])
    conn.update(data=pd.concat([df_actual, nuevo_registro], ignore_index=True))
    st.success("✅ Guardado con éxito")
    st.cache_data.clear()
    st.rerun()

# --- HISTORIAL EDITABLE ---
st.divider()
st.subheader("📋 Historial Editable (Haz clic en las celdas para actualizar)")
df_editable = conn.read(ttl=0)

if not df_editable.empty:
    # Configuramos la tabla para que solo las columnas de pago sean editables
    edited_df = st.data_editor(
        df_editable,
        column_config={
            "ESTADO_PAGO": st.column_config.SelectboxColumn(
                "ESTADO_PAGO",
                options=["Debe", "Abonado", "Pagado"],
                required=True,
            ),
            "MONTO_RECIBIDO": st.column_config.NumberColumn(
                "MONTO_RECIBIDO",
                format="$%.2f",
            ),
        },
        disabled=["FECHA_REGISTRO", "PRODUCTO", "TIENDA", "USD_BRUTO", "USD_CON_8.25", "USD_FINAL_EQ", "TC_MERCADO", "COMISION_PAGADA_MXN", "COSTO_TOTAL_MXN", "VENTA_MXN", "GANANCIA_MXN", "RANGO_SEMANA"],
        use_container_width=True,
        hide_index=True,
    )

    if st.button("💾 GUARDAR CAMBIOS DE LA TABLA"):
        conn.update(data=edited_df)
        st.success("¡Base de datos actualizada!")
        st.cache_data.clear()
        st.rerun()