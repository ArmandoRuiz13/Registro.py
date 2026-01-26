import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v20.0", layout="wide")

st.title("🚀 Control de Cobranza y Reportes Detallados")

conn = st.connection("gsheets", type=GSheetsConnection)

def lectura_segura():
    for i in range(3):
        try:
            return conn.read(ttl=0)
        except Exception:
            time.sleep(1)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def obtener_tc():
    try: return round(requests.get("https://open.er-api.com/v6/latest/USD").json()["rates"]["MXN"], 2)
    except: return 18.50
tc_actual = obtener_tc()

# --- RANGO SEMANAL ACTUAL ---
hoy = datetime.now()
inicio_semana = hoy - timedelta(days=hoy.weekday())
fin_semana = inicio_semana + timedelta(days=6)
rango_actual = f"{inicio_semana.strftime('%d/%m/%y')} al {fin_semana.strftime('%d/%m/%y')}"

# --- SIDEBAR: REGISTRO ---
with st.sidebar:
    st.header("📝 Nuevo Registro")
    nombre = st.text_input("PRODUCTO")
    opciones_tienda = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
    tienda_sel = st.selectbox("TIENDA", opciones_tienda)
    tienda_final = st.text_input("Nombre de tienda:") if tienda_sel == "CUSTOM" else tienda_sel
    
    usd_bruto_txt = st.text_input("COSTO USD", value="0.00")
    tc_mercado_txt = st.text_input("TIPO DE CAMBIO", value=str(tc_actual))
    venta_mxn_txt = st.text_input("VENTA FINAL (MXN)", value="0.00")
    
    def limpiar_num(t):
        try: return float(t.replace(',', ''))
        except: return 0.0

    usd_bruto = limpiar_num(usd_bruto_txt)
    tc_mercado = limpiar_num(tc_mercado_txt)
    venta_mxn = limpiar_num(venta_mxn_txt)

    btn_calcular = st.button("CALCULAR 🔍", use_container_width=True)
    btn_guardar = st.button("GUARDAR EN NUBE ✅", use_container_width=True, type="primary")

    st.divider()
    st.header("🗑️ Borrar Registro")
    df_nube = lectura_segura()
    if not df_nube.empty:
        opciones = [f"{i} - {df_nube.loc[i, 'PRODUCTO']}" for i in reversed(df_nube.index)]
        seleccion = st.selectbox("Selecciona para eliminar:", opciones)
        if st.button("ELIMINAR SELECCIONADO", use_container_width=True):
            st.session_state.confirm_delete = True
        if st.session_state.get('confirm_delete', False):
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("SÍ, BORRAR", type="primary"):
                conn.update(data=df_nube.drop(int(seleccion.split(" - ")[0])))
                st.session_state.confirm_delete = False
                st.cache_data.clear()
                st.rerun()
            if col_b2.button("CANCELAR"):
                st.session_state.confirm_delete = False
                st.rerun()

# --- LÓGICA GUARDADO ---
if btn_guardar and nombre and usd_bruto > 0:
    usd_tax = usd_bruto * 1.0825
    comi = (usd_tax * 0.12) * 19.5
    costo_mxn = (usd_tax * tc_mercado) + comi
    nuevo = pd.DataFrame([{
        "FECHA_REGISTRO": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "PRODUCTO": nombre, "TIENDA": tienda_final, "USD_BRUTO": usd_bruto,
        "COMISION_PAGADA_MXN": comi, "COSTO_TOTAL_MXN": costo_mxn, 
        "VENTA_MXN": venta_mxn, "GANANCIA_MXN": venta_mxn - costo_mxn, 
        "RANGO_SEMANA": rango_actual, "ESTADO_PAGO": "🔴 Debe", "MONTO_RECIBIDO": 0.0
    }])
    conn.update(data=pd.concat([df_nube, nuevo], ignore_index=True))
    st.cache_data.clear()
    st.rerun()

# --- TABLA DE COBRANZA ---
st.subheader("📋 Historial y Cobranza")
if not df_nube.empty:
    if "editor_c" in st.session_state and st.session_state["editor_c"]["edited_rows"]:
        for idx, edits in st.session_state["editor_c"]["edited_rows"].items():
            if edits.get("ESTADO_PAGO") == "🟢 Pagado":
                df_nube.at[idx, "MONTO_RECIBIDO"] = df_nube.at[idx, "VENTA_MXN"]

    df_editado = st.data_editor(
        df_nube.sort_index(ascending=False),
        column_config={
            "ESTADO_PAGO": st.column_config.SelectboxColumn("ESTADO", options=["🔴 Debe", "🟡 Abonado", "🟢 Pagado"]),
            "MONTO_RECIBIDO": st.column_config.NumberColumn("RECIBIDO", format="$%.2f")
        },
        disabled=[c for c in df_nube.columns if c not in ["ESTADO_PAGO", "MONTO_RECIBIDO"]],
        use_container_width=True, key="editor_c", hide_index=True
    )
    if st.button("💾 GUARDAR CAMBIOS DE TABLA"):
        conn.update(data=df_editado.sort_index())
        st.cache_data.clear()
        st.rerun()

# --- REPORTE SEMANAL COMPACTO ---
st.divider()
st.subheader("💰 Reporte Semanal Detallado")

if not df_nube.empty:
    semanas_disponibles = df_nube["RANGO_SEMANA"].unique().tolist()
    
    # Fila de controles compacta
    c_sel, c_b1, c_b2 = st.columns([2, 1, 1])
    with c_sel:
        semana_sel = st.selectbox("Seleccionar semana:", semanas_disponibles, label_visibility="collapsed")
    with c_b1:
        consultar_especifica = st.button("Consultar Selección", use_container_width=True)
    with c_b2:
        consultar_actual = st.button("SEMANA ACTUAL", type="primary", use_container_width=True)

    # Función para mostrar métricas
    def mostrar_metricas(df_filtrado, titulo):
        st.markdown(f"#### Resultados: {titulo}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Vendido", f"${df_filtrado['VENTA_MXN'].sum():,.2f}")
        m2.metric("Comisiones Pagadas", f"${df_filtrado['COMISION_PAGADA_MXN'].sum():,.2f}")
        m3.metric("Ganancia Neta", f"${df_filtrado['GANANCIA_MXN'].sum():,.2f}")

    if consultar_especifica:
        df_res = df_nube[df_nube["RANGO_SEMANA"] == semana_sel]
        mostrar_metricas(df_res, semana_sel)
    
    if consultar_actual:
        df_res = df_nube[df_nube["RANGO_SEMANA"] == rango_actual]
        if not df_res.empty:
            mostrar_metricas(df_res, "Semana Actual")
        else:
            st.warning("No hay registros para la semana actual.")