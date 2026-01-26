import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Gestor de Ventas Web", layout="wide")

st.title("🚀 Calculadora de Pedidos y Ganancias")

# 2. CONEXIÓN A GOOGLE SHEETS
# Este bloque es el que lee y escribe en tu nube
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error de conexión. Revisa los Secrets en Streamlit Cloud.")

# --- Lógica de Tipo de Cambio ---
@st.cache_data(ttl=3600)
def obtener_tc():
    try:
        tasa = requests.get("https://open.er-api.com/v6/latest/USD").json()["rates"]["MXN"]
        return round(tasa, 2)
    except:
        return 18.50

tc_actual = obtener_tc()

# 3. INTERFAZ (FORMULARIO)
with st.sidebar:
    st.header("Nuevo Registro")
    with st.form("formulario_ventas", clear_on_submit=True):
        nombre = st.text_input("Nombre del Producto")
        tienda = st.selectbox("Tienda", ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"])
        tienda_custom = st.text_input("Tienda Custom (si aplica)")
        
        # Entrada de datos
        usd_bruto = st.number_input("Costo USD (Antes de Tax)", min_value=0.0, step=0.01)
        tc_mercado = st.number_input("Tipo de Cambio Mercado", value=tc_actual, step=0.01)
        venta_mxn = st.number_input("Precio Venta (Pesos MXN)", min_value=0.0, step=0.01)

        submitted = st.form_submit_button("CALCULAR Y GUARDAR")

# 4. CÁLCULOS (IGUAL QUE EN TU PC)
usd_con_825 = usd_bruto * 1.0825
comision_mxn = (usd_con_825 * 0.12) * 19.5
costo_total_mxn = (usd_con_825 * tc_mercado) + comision_mxn
ganancia = venta_mxn - costo_total_mxn

# Lógica de Semana (Solo fechas)
hoy = datetime.now()
lunes = hoy - timedelta(days=hoy.weekday())
domingo = lunes + timedelta(days=6)
rango_semana = f"{lunes.strftime('%d/%m/%y')} al {domingo.strftime('%d/%m/%y')}"

# 5. MOSTRAR RESULTADOS ANTES DE GUARDAR
if usd_bruto > 0:
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Inversión Total", f"${costo_total_mxn:,.2f} MXN")
    with col_m2:
        st.metric("Comisión a Pagar", f"${comision_mxn:,.2f} MXN")
    with col_m3:
        st.metric("Ganancia Neta", f"${ganancia:,.2f} MXN")

# 6. GUARDADO EN LA NUBE
if submitted:
    if nombre and usd_bruto > 0:
        try:
            # Leer datos actuales sin caché para no perder registros
            data_existente = conn.read(ttl=0)
            
            # Crear nueva fila con tus especificaciones
            nuevo_dato = pd.DataFrame([{
                "FECHA": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "PRODUCTO": nombre,
                "TIENDA": tienda_custom if tienda == "CUSTOM" else tienda,
                "USD_BRUTO": usd_bruto, # Tu precio antes de tax
                "USD_TAX": usd_con_825,
                "COMISION_MXN": comision_mxn,
                "COSTO_TOTAL_MXN": costo_total_mxn,
                "VENTA_MXN": venta_mxn,
                "GANANCIA_MXN": ganancia,
                "RANGO_SEMANA": rango_semana # Última casilla
            }])
            
            # Unir y subir
            updated_df = pd.concat([data_existente, nuevo_dato], ignore_index=True)
            conn.update(data=updated_df)
            
            st.balloons()
            st.success("✅ ¡Registro guardado en Google Sheets!")
            st.cache_data.clear() # Limpiar vista para ver el nuevo dato
        except Exception as e:
            st.error(f"Error al guardar: {e}")
    else:
        st.warning("Por favor rellena el nombre y el costo.")

# 7. HISTORIAL SIEMPRE VISIBLE
st.divider()
st.subheader("📋 Historial de Registros (Nube)")
try:
    # Mostramos todo el historial cargado desde Google Sheets
    df_ver = conn.read(ttl=0)
    st.dataframe(df_ver.sort_index(ascending=False), use_container_width=True)
except:
    st.info("Aún no hay registros cargados.")