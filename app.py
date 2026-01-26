import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v15.0", layout="wide")

st.title("🚀 Control de Cobranza Inteligente")

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
            st.session_state.confirmar_borrado = True
        
        if st.session_state.get('confirmar_borrado', False):
            st.warning(f"¿Borrar '{seleccion.split(' - ')[1]}'? ")
            if st.button("SÍ, BORRAR DEFINITIVAMENTE", type="primary"):
                conn.update(data=df_nube.drop(int(seleccion.split(" - ")[0])))
                st.session_state.confirmar_borrado = False
                st.cache_data.clear()
                st.rerun()

# --- CÁLCULOS ---
usd_con_tax = usd_bruto * 1.0825
comision_mxn = (usd_con_tax * 0.12) * 19.5
costo_total_mxn = (usd_con_tax * tc_mercado) + comision_mxn
ganancia_mxn = venta_mxn - costo_total_mxn
rango_semanal = f"{(datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%d/%m/%y')} al {((datetime.now() - timedelta(days=datetime.now().weekday())) + timedelta(days=6)).strftime('%d/%m/%y')}"

if btn_calcular and usd_bruto > 0:
    st.info(f"### Análisis: {nombre}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Comisión MXN", f"${comision_mxn:,.2f}")
    c2.metric("Inversión Total", f"${costo_total_mxn:,.2f}")
    c3.metric("Ganancia Neta", f"${ganancia_mxn:,.2f}")

# --- GUARDAR NUEVO ---
if btn_guardar and nombre and usd_bruto > 0:
    nuevo = pd.DataFrame([{
        "FECHA_REGISTRO": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "PRODUCTO": nombre, "TIENDA": tienda, "USD_BRUTO": usd_bruto,
        "USD_CON_8.25": usd_con_tax, "USD_FINAL_EQ": costo_total_mxn/tc_mercado,
        "TC_MERCADO": tc_mercado, "COMISION_PAGADA_MXN": comision_mxn,
        "COSTO_TOTAL_MXN": costo_total_mxn, "VENTA_MXN": venta_mxn,
        "GANANCIA_MXN": ganancia_mxn, "RANGO_SEMANA": rango_semanal,
        "ESTADO": "Debe", "MONTO_RECIBIDO": 0.0
    }])
    conn.update(data=pd.concat([df_nube, nuevo], ignore_index=True))
    st.cache_data.clear()
    st.rerun()

# --- HISTORIAL EDITABLE CON COLORES ---
st.divider()
st.subheader("📋 Historial y Cobranza")

if not df_nube.empty:
    # Procesar lógica de auto-pago antes de mostrar el editor
    # Si detectamos que alguien marcó 'Pagado' en el editor (vía session_state)
    if "main_editor" in st.session_state and st.session_state["main_editor"]["edited_rows"]:
        for idx, edits in st.session_state["main_editor"]["edited_rows"].items():
            if "ESTADO" in edits and edits["ESTADO"] == "Pagado":
                # Si cambia a Pagado, el monto recibido es igual a VENTA_MXN
                df_nube.at[idx, "MONTO_RECIBIDO"] = df_nube.at[idx, "VENTA_MXN"]

    # Definimos los colores para la columna ESTADO usando mapeo visual
    # Nota: Los colores de fondo en celdas st.data_editor se gestionan mejor con iconos y texto descriptivo
    edited_df = st.data_editor(
        df_nube.sort_index(ascending=False),
        column_config={
            "ESTADO": st.column_config.SelectboxColumn(
                "ESTADO",
                options=["🔴 Debe", "🟡 Abonado", "🟢 Pagado"],
                required=True,
                help="Selecciona el estado actual del pago"
            ),
            "MONTO_RECIBIDO": st.column_config.NumberColumn(
                "MONTO RECIBIDO", 
                format="$%.2f",
                help="Si seleccionas Pagado, este valor se actualizará al valor de VENTA_MXN"
            ),
            "VENTA_MXN": st.column_config.NumberColumn("VENTA_MXN", format="$%.2f"),
        },
        disabled=[col for col in df_nube.columns if col not in ["ESTADO", "MONTO_RECIBIDO"]],
        use_container_width=True,
        hide_index=True,
        key="main_editor"
    )

    if st.button("💾 GUARDAR CAMBIOS EN LA NUBE", type="primary"):
        # Limpiar emojis para guardar texto limpio en Excel
        final_save_df = edited_df.copy()
        final_save_df['ESTADO'] = final_save_df['ESTADO'].str.replace('🔴 ', '').str.replace('🟡 ', '').str.replace('🟢 ', '')
        
        conn.update(data=final_save_df.sort_index())
        st.success("¡Sincronización completa con Google Sheets!")
        st.cache_data.clear()
        st.rerun()