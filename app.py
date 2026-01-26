import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Configuración de página
st.set_page_config(page_title="Gestor de Ventas Pro", layout="wide", initial_sidebar_state="expanded")

# Título Principal
st.title("🚀 Sistema de Control de Ventas y Cobranza")

# --- CONEXIÓN Y LECTURA SEGURA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def lectura_segura():
    """Intenta leer la base de datos 3 veces antes de dar error."""
    for i in range(3):
        try:
            return conn.read(ttl=0)
        except Exception:
            time.sleep(1.5)
    return pd.DataFrame()

# Obtener Tipo de Cambio
@st.cache_data(ttl=3600)
def obtener_tc():
    try: 
        data = requests.get("https://open.er-api.com/v6/latest/USD").json()
        return round(data["rates"]["MXN"], 2)
    except: 
        return 18.50

tc_actual = obtener_tc()

# --- CÁLCULO DE SEMANA ACTUAL ---
hoy = datetime.now()
inicio_semana = hoy - timedelta(days=hoy.weekday())
fin_semana = inicio_semana + timedelta(days=6)
rango_actual = f"{inicio_semana.strftime('%d/%m/%y')} al {fin_semana.strftime('%d/%m/%y')}"

# --- SIDEBAR: REGISTRO Y CALCULADORA ---
with st.sidebar:
    st.header("📝 Nuevo Registro")
    
    # Inputs con Placeholder (se borran al escribir)
    nombre = st.text_input("PRODUCTO", placeholder="Ej: Tenis Nike")
    
    opciones_tienda = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
    tienda_sel = st.selectbox("TIENDA", opciones_tienda)
    tienda_final = st.text_input("Nombre de la tienda custom:", placeholder="Escribe aquí...") if tienda_sel == "CUSTOM" else tienda_sel
    
    usd_bruto_txt = st.text_input("COSTO USD (Sin Tax)", placeholder="Ej: 45.00")
    tc_mercado_txt = st.text_input("TIPO DE CAMBIO", value=str(tc_actual))
    venta_mxn_txt = st.text_input("VENTA FINAL (MXN)", placeholder="Ej: 1800.00")
    
    def limpiar_num(t):
        if not t: return 0.0
        try: return float(t.replace(',', '').replace('$', ''))
        except: return 0.0

    usd_bruto = limpiar_num(usd_bruto_txt)
    tc_mercado = limpiar_num(tc_mercado_txt)
    venta_mxn = limpiar_num(venta_mxn_txt)

    # Lógica de costos
    usd_tax = usd_bruto * 1.0825
    comision_mxn = (usd_tax * 0.12) * 19.5
    costo_total_mxn = (usd_tax * tc_mercado) + comision_mxn
    ganancia_neta = venta_mxn - costo_total_mxn

    # --- BOTÓN CALCULAR ---
    if st.button("CALCULAR 🔍", use_container_width=True):
        st.info(f"**Comisión:** ${comision_mxn:,.2f} MXN\n\n**Inversión:** ${costo_total_mxn:,.2f} MXN\n\n**Ganancia:** ${ganancia_neta:,.2f} MXN")

    # --- BOTÓN GUARDAR ---
    btn_guardar = st.button("GUARDAR EN NUBE ✅", use_container_width=True, type="primary")

    st.divider()
    
    # --- BORRAR CON CONFIRMACIÓN ---
    st.header("🗑️ Borrar Registro")
    df_nube = lectura_segura()
    if not df_nube.empty:
        opciones = [f"{i} - {df_nube.loc[i, 'PRODUCTO']}" for i in reversed(df_nube.index)]
        seleccion = st.selectbox("Seleccionar para borrar:", opciones)
        
        if st.button("ELIMINAR SELECCIONADO", use_container_width=True):
            st.session_state.confirm_delete = True
        
        if st.session_state.get('confirm_delete', False):
            st.error(f"¿Borrar '{seleccion.split(' - ')[1]}'?")
            col_si, col_no = st.columns(2)
            if col_si.button("SÍ", type="primary", use_container_width=True):
                idx = int(seleccion.split(" - ")[0])
                conn.update(data=df_nube.drop(idx))
                st.session_state.confirm_delete = False
                st.cache_data.clear()
                st.rerun()
            if col_no.button("NO", use_container_width=True):
                st.session_state.confirm_delete = False
                st.rerun()

# --- ACCIÓN DE GUARDADO ---
if btn_guardar and nombre and usd_bruto > 0:
    nuevo_reg = pd.DataFrame([{
        "FECHA": datetime.now().strftime("%d/%m/%Y"),
        "PRODUCTO": nombre,
        "TIENDA": tienda_final,
        "USD_BRUTO": usd_bruto,
        "COMISION_PAGADA_MXN": comision_mxn,
        "COSTO_TOTAL_MXN": costo_total_mxn,
        "VENTA_MXN": venta_mxn,
        "GANANCIA_MXN": ganancia_neta,
        "RANGO_SEMANA": rango_actual,
        "ESTADO_PAGO": "🔴 Debe",
        "MONTO_RECIBIDO": 0.0
    }])
    conn.update(data=pd.concat([df_nube, nuevo_reg], ignore_index=True))
    st.cache_data.clear()
    st.rerun()

# --- TABLA DE COBRANZA EDITABLE ---
st.subheader("📋 Historial y Cobranza")
if not df_nube.empty:
    # Lógica de Auto-Pago: Si se cambia a '🟢 Pagado', MONTO_RECIBIDO = VENTA_MXN
    if "editor_final" in st.session_state and st.session_state["editor_final"]["edited_rows"]:
        for idx, edits in st.session_state["editor_final"]["edited_rows"].items():
            if edits.get("ESTADO_PAGO") == "🟢 Pagado":
                df_nube.at[idx, "MONTO_RECIBIDO"] = df_nube.at[idx, "VENTA_MXN"]

    df_editable = st.data_editor(
        df_nube.sort_index(ascending=False),
        column_config={
            "ESTADO_PAGO": st.column_config.SelectboxColumn("ESTADO", options=["🔴 Debe", "🟡 Abonado", "🟢 Pagado"]),
            "MONTO_RECIBIDO": st.column_config.NumberColumn("RECIBIDO ($)", format="$%.2f"),
            "VENTA_MXN": st.column_config.NumberColumn("VENTA ($)", format="$%.2f", disabled=True),
        },
        disabled=[c for c in df_nube.columns if c not in ["ESTADO_PAGO", "MONTO_RECIBIDO"]],
        use_container_width=True, hide_index=True, key="editor_final"
    )

    if st.button("💾 ACTUALIZAR COBRANZA (GUARDAR CAMBIOS)"):
        conn.update(data=df_editable.sort_index())
        st.success("¡Sincronizado con Google Sheets!")
        st.cache_data.clear()
        st.rerun()

# --- REPORTES SEMANALES ---
st.divider()
st.subheader("💰 Resumen de Ganancias")
if not df_nube.empty:
    semanas = df_nube["RANGO_SEMANA"].unique().tolist()
    c_sel, c_b1, c_b2 = st.columns([2, 1, 1])
    
    with c_sel:
        sem_sel = st.selectbox("Elegir semana:", semanas, label_visibility="collapsed")
    with c_b1:
        btn_sel = st.button("Consultar Selección", use_container_width=True)
    with c_b2:
        btn_act = st.button("SEMANA ACTUAL", type="primary", use_container_width=True)

    def mostrar_metricas(df_filtro, titulo):
        st.markdown(f"#### Resultados: {titulo}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Vendido", f"${df_filtro['VENTA_MXN'].sum():,.2f}")
        m2.metric("Comisiones Pagadas", f"${df_filtro['COMISION_PAGADA_MXN'].sum():,.2f}")
        m3.metric("Ganancia Neta", f"${df_filtro['GANANCIA_MXN'].sum():,.2f}")

    if btn_sel:
        mostrar_metricas(df_nube[df_nube["RANGO_SEMANA"] == sem_sel], sem_sel)
    if btn_act:
        mostrar_metricas(df_nube[df_nube["RANGO_SEMANA"] == rango_actual], "Semana Actual")