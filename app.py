import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v25", layout="wide")

# --- BOTÓN DE NAVEGACIÓN ---
with st.sidebar:
    # IMPORTANTE: La ruta debe incluir "pages/"
    if st.button("📦 IR A INVENTARIO", use_container_width=True):
        try:
            st.switch_page("pages/Inventario.py")
        except:
            st.error("No se encontró el archivo pages/Inventario.py")

    st.divider()

st.title("🚀 Control de Ventas")

conn = st.connection("gsheets", type=GSheetsConnection)

def lectura_segura():
    for i in range(3):
        try: 
            df = conn.read(ttl=0)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception: 
            time.sleep(1)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def obtener_tc():
    try: return round(requests.get("https://open.er-api.com/v6/latest/USD").json()["rates"]["MXN"], 2)
    except: return 18.50
tc_actual = obtener_tc()

# --- DATOS ACTUALES ---
df_nube = lectura_segura()
proximo_id = len(df_nube)

# --- RANGO SEMANAL ACTUAL ---
hoy = datetime.now()
inicio_semana = hoy - timedelta(days=hoy.weekday())
fin_semana = inicio_semana + timedelta(days=6)
rango_actual = f"{inicio_semana.strftime('%d/%m/%y')} al {fin_semana.strftime('%d/%m/%y')}"

# --- SIDEBAR: REGISTRO ---
with st.sidebar:
    st.header(f"📝 Registro (ID: {proximo_id})")
    nombre = st.text_input("PRODUCTO", placeholder="Nombre del producto")
    
    opciones_tienda = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
    tienda_sel = st.selectbox("TIENDA", opciones_tienda)
    tienda_final = st.text_input("Tienda custom:") if tienda_sel == "CUSTOM" else tienda_sel
    
    usd_bruto_txt = st.text_input("COSTO USD", placeholder="Ej: 50.00")
    tc_mercado_txt = st.text_input("TIPO DE CAMBIO", value=str(tc_actual))
    venta_mxn_txt = st.text_input("VENTA FINAL (MXN)", placeholder="Ej: 1500.00")
    
    def limpiar_num(t):
        if not t: return 0.0
        try: return float(str(t).replace(',', '').replace('$', ''))
        except: return 0.0

    usd_bruto = limpiar_num(usd_bruto_txt)
    tc_mercado = limpiar_num(tc_mercado_txt)
    venta_mxn = limpiar_num(venta_mxn_txt)

    usd_tax = usd_bruto * 1.0825
    comi_mxn = (usd_tax * 0.12) * 19
    costo_tot_mxn = (usd_tax * tc_mercado) + comi_mxn
    ganancia_mxn = venta_mxn - costo_tot_mxn
    usd_final_eq = costo_tot_mxn / tc_mercado if tc_mercado > 0 else 0

    if st.button("CALCULAR 🔍", use_container_width=True):
        st.info(f"Comisión: ${comi_mxn:,.2f}\n\nInversión: ${costo_tot_mxn:,.2f}\n\nGanancia: ${ganancia_mxn:,.2f}")

    btn_guardar = st.button("GUARDAR EN NUBE ✅", use_container_width=True, type="primary")

# --- ACCIÓN GUARDAR ---
if btn_guardar and nombre and usd_bruto > 0:
    nuevo = pd.DataFrame([{
        "FECHA_REGISTRO": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "PRODUCTO": nombre, "TIENDA": tienda_final, "USD_BRUTO": usd_bruto,
        "USD_CON_8.25": usd_tax, "USD_FINAL_EQ": usd_final_eq, "TC_MERCADO": tc_mercado,
        "COMISION_PAGADA_MXN": comi_mxn, "COSTO_TOTAL_MXN": costo_tot_mxn,
        "VENTA_MXN": venta_mxn, "GANANCIA_MXN": ganancia_mxn, "RANGO_SEMANA": rango_actual,
        "ESTADO_PAGO": "🔴 Debe", "MONTO_RECIBIDO": 0.0, "COMI_CHECK": False, "FECHA": datetime.now().strftime("%d/%m/%Y")
    }])
    conn.update(data=pd.concat([df_nube, nuevo], ignore_index=True))
    st.cache_data.clear()
    st.rerun()

# --- TABLA DE VENTAS ---
st.subheader("📋 Historial y Cobranza")
if not df_nube.empty:
    edited_df = st.data_editor(df_nube.sort_index(ascending=False), use_container_width=True)
    if st.button("💾 GUARDAR CAMBIOS"):
        conn.update(data=edited_df.sort_index())
        st.success("¡Ventas actualizadas!")
        st.rerun()