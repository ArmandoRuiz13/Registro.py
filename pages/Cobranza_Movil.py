import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Cobranza Rápida 📱", layout="centered")

# Reutilizamos la conexión
conn = st.connection("gsheets", type=GSheetsConnection)

def leer_datos():
    st.cache_data.clear()
    df = conn.read(ttl=0)
    df.columns = [str(c).strip() for c in df.columns]
    return df

# --- ESTILOS MÓVIL ---
st.markdown("""
    <style>
    .stButton button {
        height: 3em;
        font-size: 20px !important;
    }
    .card {
        border: 1px solid #ddd;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        background-color: #f9f9f9;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💸 Cobranza Móvil")

# --- LÓGICA DE DATOS ---
df_completo = leer_datos()

# Filtramos solo lo que NO está pagado
df_pendientes = df_completo[df_completo["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if df_pendientes.empty:
    st.balloons()
    st.success("¡Felicidades! No hay ventas pendientes de cobro. 🎉")
    if st.button("Volver al Inicio"):
        st.switch_page("app.py")
    st.stop()

# --- NAVEGACIÓN DINÁMICA (CARRUSEL) ---
if 'index_cobro' not in st.session_state:
    st.session_state.index_cobro = 0

# Asegurar que el índice no se pase si borras algo
if st.session_state.index_cobro >= len(df_pendientes):
    st.session_state.index_cobro = 0

# Obtener el registro actual
total_pendientes = len(df_pendientes)
registro = df_pendientes.iloc[st.session_state.index_cobro]
original_idx = registro.name # Índice real en el Excel original

# --- DISEÑO DE TARJETA ---
st.write(f"Venta {st.session_state.index_cobro + 1} de {total_pendientes}")
progress = (st.session_state.index_cobro + 1) / total_pendientes
st.progress(progress)

with st.container():
    # Mostrar Foto
    foto = registro.get("FOTO_URL", "")
    if foto and str(foto) != "nan":
        st.image(foto, use_container_width=True)
    else:
        st.warning("Sin foto disponible")

    # Datos clave
    st.subheader(f"📦 {registro['PRODUCTO']}")
    c1, c2 = st.columns(2)
    c1.metric("Cliente", registro['CLIENTE'])
    c2.metric("Venta", f"${registro['VENTA_MXN']:,.2f}")

    st.info(f"Estado actual: {registro['ESTADO_PAGO']}")

# --- ACCIONES ---
st.divider()

col_izq, col_der = st.columns(2)

with col_izq:
    if st.button("⬅️ Anterior", use_container_width=True):
        if st.session_state.index_cobro > 0:
            st.session_state.index_cobro -= 1
            st.rerun()

with col_der:
    if st.button("Siguiente ➡️", use_container_width=True):
        if st.session_state.index_cobro < total_pendientes - 1:
            st.session_state.index_cobro += 1
            st.rerun()

# BOTÓN DE ACCIÓN RÁPIDA (PAGADO)
if st.button("✅ MARCAR COMO PAGADO TOTAL", type="primary", use_container_width=True):
    with st.spinner("Actualizando cobro..."):
        # Actualizamos el registro en el dataframe completo
        df_completo.at[original_idx, "ESTADO_PAGO"] = "🟢 Pagado"
        df_completo.at[original_idx, "MONTO_RECIBIDO"] = registro["VENTA_MXN"]
        
        # Guardar en GSheets
        conn.update(data=df_completo)
        
        st.toast(f"¡{registro['PRODUCTO']} cobrado!")
        time.sleep(1)
        st.cache_data.clear()
        st.rerun()

if st.button("🏠 Inicio", use_container_width=True):
    st.switch_page("app.py")