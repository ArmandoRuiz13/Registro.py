import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Gestor de Importaciones", layout="centered")

st.title("🚀 Calculadora de Pedidos y Ganancias")

# --- Lógica de Tipo de Cambio ---
@st.cache_data(ttl=3600) # Se actualiza cada hora
def obtener_tc():
    try:
        tasa = requests.get("https://open.er-api.com/v6/latest/USD").json()["rates"]["MXN"]
        return round(tasa, 2)
    except:
        return 18.50

tc_actual = obtener_tc()

# --- Interfaz de Usuario ---
with st.form("formulario_ventas"):
    col1, col2 = st.columns(2)
    
    with col1:
        nombre = st.text_input("Nombre del Producto")
        tienda = st.selectbox("Tienda", ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "CUSTOM"])
        tienda_custom = st.text_input("Tienda Custom (si aplica)")
    
    with col2:
        usd_bruto = st.number_input("Costo USD (Antes de Tax)", min_value=0.0, step=0.01)
        tc_mercado = st.number_input("Tipo de Cambio Mercado", value=tc_actual, step=0.01)
        venta_mxn = st.number_input("Precio Venta (Pesos MXN)", min_value=0.0, step=0.01)

    submitted = st.form_submit_button("CALCULAR Y GUARDAR")

# --- Cálculos ---
usd_con_825 = usd_bruto * 1.0825
comision_mxn = (usd_con_825 * 0.12) * 19.5
costo_total_mxn = (usd_con_825 * tc_mercado) + comision_mxn
ganancia = venta_mxn - costo_total_mxn

# Lógica de Semana
hoy = datetime.now()
lunes = hoy - timedelta(days=hoy.weekday())
domingo = lunes + timedelta(days=6)
rango_semana = f"{lunes.strftime('%d/%m/%y')} al {domingo.strftime('%d/%m/%y')}"

# --- Mostrar Resumen ---
if usd_bruto > 0:
    st.info(f"**Comisión a pagar:** ${comision_mxn:,.2f} MXN")
    st.success(f"**Ganancia Real:** ${ganancia:,.2f} MXN")

# --- Conexión a Base de Datos (Google Sheets) ---
# Nota: Esto requiere configurar los 'Secrets' en Streamlit Cloud
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    if submitted:
        # Crear DataFrame con el nuevo registro
        nuevo_dato = pd.DataFrame([{
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Producto": nombre,
            "Tienda": tienda_custom if tienda == "CUSTOM" else tienda,
            "USD_Bruto": usd_bruto,
            "USD_Tax": usd_con_825,
            "Comision_MXN": comision_mxn,
            "Costo_Total_MXN": costo_total_mxn,
            "Venta_MXN": venta_mxn,
            "Ganancia_MXN": ganancia,
            "Semana": rango_semana
        }])
        
        # Leer datos actuales y agregar el nuevo
        data_existente = conn.read()
        updated_df = pd.concat([data_existente, nuevo_dato], ignore_index=True)
        conn.update(data=updated_df)
        st.balloons()
        st.write("✅ ¡Registro guardado en Google Sheets!")

    # Mostrar la tabla de registros siempre
    st.divider()
    st.subheader("Historial de Registros")
    df_historico = conn.read()
    st.dataframe(df_historico.tail(10)) # Muestra los últimos 10

except Exception as e:
    st.warning("Conecta tu Google Sheet para guardar los registros permanentemente.")