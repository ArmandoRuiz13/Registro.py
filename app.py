import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v14.0", layout="wide")

st.title("🚀 Control de Ventas y Pagos")

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

    btn_calcular = st.button("CALCULAR 🔍", use_container_width=True)
    btn_guardar = st.button("GUARDAR EN NUBE ✅", use_container_width=True, type="primary")

    st.divider()
    
    # --- SECCIÓN ELIMINAR ---
    st.header("🗑️ Borrar Registro")
    df_nube = conn.read(ttl=0)
    if not df_nube.empty:
        opciones = [f"{i} - {df_nube.loc[i, 'PRODUCTO']}" for i in reversed(df_nube.index)]
        seleccion = st.selectbox("Selecciona para eliminar:", opciones)
        if st.button("ELIMINAR SELECCIONADO", use_container_width=True):
            conn.update(data=df_nube.drop(int(seleccion.split(" - ")[0])))
            st.cache_data.clear()
            st.rerun()

# --- CÁLCULOS ---
usd_con_tax = usd_bruto * 1.0825
comision_mxn = (usd_con_tax * 0.12) * 19.5
costo_total_mxn = (usd_con_tax * tc_mercado) + comision_mxn
ganancia_mxn = venta_mxn - costo_total_mxn
rango_semanal = f"{(datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%d/%m/%y')} al {((datetime.now() - timedelta(days=datetime.now().weekday())) + timedelta(days=6)).strftime('%d/%m/%y')}"

if btn_calcular and usd_bruto > 0:
    st.info(f"### Análisis de: {nombre}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Comisión (12% @ 19.5)", f"${comision_mxn:,.2f} MXN")
    c2.metric("Inversión Total", f"${costo_total_mxn:,.2f} MXN")
    c3.metric("Ganancia Neta", f"${ganancia_mxn:,.2f} MXN")

# --- ACCIÓN: GUARDAR ---
if btn_guardar and nombre and usd_bruto > 0:
    nuevo = pd.DataFrame([{
        "FECHA_REGISTRO": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "PRODUCTO": nombre, "TIENDA": tienda, "USD_BRUTO": usd_bruto,
        "USD_CON_8.25": usd_con_tax, "USD_FINAL_EQ": costo_total_mxn/tc_mercado,
        "TC_MERCADO": tc_mercado, "COMISION_PAGADA_MXN": comision_mxn,
        "COSTO_TOTAL_MXN": costo_total_mxn, "VENTA_MXN": venta_mxn,
        "GANANCIA_MXN": ganancia_mxn, "RANGO_SEMANA": rango_semanal,
        "ESTADO_PAGO": "Debe", "MONTO_RECIBIDO": 0.0
    }])
    conn.update(data=pd.concat([df_nube, nuevo], ignore_index=True))
    st.cache_data.clear()
    st.rerun()

# --- HISTORIAL UNIFICADO Y EDITABLE ---
st.divider()
st.subheader("📋 Historial y Cobranza")

if not df_nube.empty:
    # 1. Editor de datos principal
    edited_df = st.data_editor(
        df_nube.sort_index(ascending=False),
        column_config={
            "ESTADO_PAGO": st.column_config.SelectboxColumn(
                "ESTADO", 
                options=["Debe", "Abonado", "Pagado"],
                # Aquí definimos los colores para la casilla
                help="Rojo: Debe | Amarillo: Abonado | Verde: Pagado"
            ),
            "MONTO_RECIBIDO": st.column_config.NumberColumn("MONTO RECIBIDO", format="$%.2f"),
        },
        disabled=[col for col in df_nube.columns if col not in ["ESTADO_PAGO", "MONTO_RECIBIDO"]],
        use_container_width=True,
        hide_index=True,
        key="main_editor"
    )

    # 2. Lógica Automática de Pago
    # Si el usuario cambió a 'Pagado' en el editor, actualizamos el monto recibido
    for i in edited_df.index:
        # Detectamos si el estado es Pagado para igualar el monto
        if edited_df.at[i, 'ESTADO_PAGO'] == 'Pagado':
             # Solo actualizamos si el monto actual es distinto al costo total
             if edited_df.at[i, 'MONTO_RECIBIDO'] != edited_df.at[i, 'COSTO_TOTAL_MXN']:
                edited_df.at[i, 'MONTO_RECIBIDO'] = edited_df.at[i, 'COSTO_TOTAL_MXN']

    # 3. Aplicar colores a la columna ESTADO (Solo lectura visual mediante Style)
    def style_estado(val):
        if val == 'Pagado': return 'background-color: #28a745; color: white'
        if val == 'Abonado': return 'background-color: #ffc107; color: black'
        return 'background-color: #dc3545; color: white'

    # Mostramos el botón para guardar los cambios hechos en la tabla
    if st.button("💾 GUARDAR CAMBIOS EN LA NUBE"):
        conn.update(data=edited_df.sort_index()) # Guardamos manteniendo el orden original
        st.success("¡Base de Datos Actualizada!")
        st.cache_data.clear()
        st.rerun()