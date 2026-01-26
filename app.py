import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Gestor de Importaciones", layout="wide")

st.title("🚀 Calculadora de Pedidos y Ganancias")

# --- Lógica de Tipo de Cambio ---
@st.cache_data(ttl=3600) 
def obtener_tc():
    try:
        tasa = requests.get("https://open.er-api.com/v6/latest/USD").json()["rates"]["MXN"]
        return round(tasa, 2)
    except:
        return 18.50

tc_actual = obtener_tc()

# --- Interfaz de Usuario ---
with st.sidebar:
    st.header("Nuevo Registro")
    with st.form("formulario_ventas", clear_on_submit=True):
        nombre = st.text_input("Nombre del Producto")
        tienda = st.selectbox("Tienda", ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "GuessFactory", "Ashford", "Nike", "Aeropostale", "JDSports", "CUSTOM"])
        tienda_custom = st.text_input("Tienda Custom (si aplica)")
        
        usd_bruto = st.number_input("Costo USD (Antes de Tax)", min_value=0.0, step=0.01)
        tc_mercado = st.number_input("Tipo de Cambio Mercado", value=tc_actual, step=0.01)
        venta_mxn = st.number_input("Precio Venta (Pesos MXN)", min_value=0.0, step=0.01)

        submitted = st.form_submit_button("CALCULAR Y GUARDAR")

# --- Cálculos y Lógica de Negocio ---
usd_con_825 = usd_bruto * 1.0825
comision_mxn = (usd_con_825 * 0.12) * 19.5
costo_total_mxn = (usd_con_825 * tc_mercado) + comision_mxn
ganancia = venta_mxn - costo_total_mxn

# Rango de semana limpio (Lunes a Domingo)
hoy = datetime.now()
lunes = hoy - timedelta(days=hoy.weekday())
domingo = lunes + timedelta(days=6)
rango_semana = f"{lunes.strftime('%d/%m/%y')} al {domingo.strftime('%d/%m/%y')}"

# --- Panel Central: Resumen ---
if usd_bruto > 0:
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.metric("Comisión a Pagar", f"${comision_mxn:,.2f} MXN")
        st.write(f"**USD Bruto:** ${usd_bruto:.2f}")
        st.write(f"**USD + 8.25%:** ${usd_con_825:.2f}")
    with col_res2:
        st.metric("Ganancia Real", f"${ganancia:,.2f} MXN", delta_color="normal")
        st.write(f"**Inversión Total:** ${costo_total_mxn:,.2f} MXN")
        st.write(f"**Rango:** {rango_semana}")

# --- Conexión a Base de Datos (Google Sheets) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    if submitted:
        if nombre and usd_bruto > 0:
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
            st.success("✅ ¡Registro guardado en la nube!")
        else:
            st.error("Faltan datos obligatorios (Nombre o Costo).")

    # --- Mostrar el Historial ---
    st.divider()
    st.subheader("📋 Historial Completo de Registros")
    df_historico = conn.read()
    
    # Invertimos el orden para ver lo más reciente arriba
    st.dataframe(df_historico.sort_index(ascending=False), use_container_width=True)

except Exception as e:
    st.warning("Configura los 'Secrets' en Streamlit con tu URL de Google Sheets para activar la base de datos.")