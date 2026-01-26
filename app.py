import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v13.0", layout="wide")

# Estilos de color para la tabla (CSS)
st.markdown("""
    <style>
    .stTextInput input { font-size: 18px; }
    /* Colores para las filas según estado */
    .pagado { background-color: #d4edda !important; }
    .abonado { background-color: #fff3cd !important; }
    .debe { background-color: #f8d7da !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Calculadora y Control de Pagos Inteligente")

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

# --- HISTORIAL CON LÓGICA DE COLOR Y AUTO-PAGO ---
st.divider()
st.subheader("📋 Control de Cobranza")

if not df_nube.empty:
    # 1. Función para aplicar colores a la tabla visual
    def highlight_estado(row):
        if row['ESTADO_PAGO'] == 'Pagado':
            return ['background-color: #28a745; color: white'] * len(row)
        elif row['ESTADO_PAGO'] == 'Abonado':
            return ['background-color: #ffc107; color: black'] * len(row)
        else:
            return ['background-color: #dc3545; color: white'] * len(row)

    # 2. Editor de datos
    edited_df = st.data_editor(
        df_nube,
        column_config={
            "ESTADO_PAGO": st.column_config.SelectboxColumn("ESTADO", options=["Debe", "Abonado", "Pagado"]),
            "MONTO_RECIBIDO": st.column_config.NumberColumn("MONTO RECIBIDO", format="$%.2f"),
        },
        disabled=[col for col in df_nube.columns if col not in ["ESTADO_PAGO", "MONTO_RECIBIDO"]],
        use_container_width=True,
        hide_index=True,
        key="data_editor"
    )

    # 3. Lógica Automática: Si cambió a 'Pagado', igualar monto al costo total
    # Comparamos el original con el editado para aplicar la regla
    for i in edited_df.index:
        if edited_df.at[i, 'ESTADO_PAGO'] == 'Pagado' and df_nube.at[i, 'ESTADO_PAGO'] != 'Pagado':
            edited_df.at[i, 'MONTO_RECIBIDO'] = edited_df.at[i, 'COSTO_TOTAL_MXN']

    if st.button("💾 CONFIRMAR Y GUARDAR CAMBIOS"):
        conn.update(data=edited_df)
        st.success("¡Datos sincronizados con Google Sheets!")
        st.cache_data.clear()
        st.rerun()

    # 4. Vista previa con colores (Solo lectura para ver los colores aplicados)
    st.caption("Vista de colores actual:")
    st.dataframe(edited_df.style.apply(highlight_estado, axis=1), use_container_width=True)