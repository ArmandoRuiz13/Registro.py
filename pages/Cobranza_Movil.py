import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Pro", layout="centered")

# --- CSS MEJORADO PARA BOTONES LARGOS Y CENTRADOS ---
st.markdown("""
    <style>
    /* Contenedor principal */
    .block-container { padding-top: 1rem; }
    
    /* Botones de Navegación: Largos y centrados */
    .stButton button {
        width: 100% !important;
        height: 4rem !important;
        font-size: 20px !important;
        border-radius: 15px !important;
        margin-bottom: 10px;
    }
    
    /* Imagen con precarga visual */
    .stImage img {
        border-radius: 20px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
        max-height: 350px;
        object-fit: cover;
    }

    /* Badge de estatus */
    .stBadge {
        display: block;
        text-align: center;
        padding: 10px;
        font-size: 18px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600) # Caché de 10 min para velocidad de carga
def leer_datos():
    try:
        df = conn.read(ttl=0) 
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        st.error("Error de conexión.")
        st.stop()

# --- LÓGICA DE NAVEGACIÓN ---
df_nube = leer_datos()
pendientes = df_nube[df_nube["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if pendientes.empty:
    st.success("¡Todo pagado! 🎉")
    if st.button("🏠 Inicio"): st.switch_page("app.py")
    st.stop()

if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ ---

# 1. Estatus Superior
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
st.markdown(f"""
    <div style="background-color:{color_st}22; border:2px solid {color_st}; color:{color_st}; 
    text-align:center; padding:10px; border-radius:15px; font-weight:bold; margin-bottom:15px;">
        {reg['ESTADO_PAGO']}
    </div>
    """, unsafe_allow_html=True)

# 2. Imagen y Datos (Precargados)
if reg.get("FOTO_URL") and str(reg["FOTO_URL"]) != "nan":
    st.image(reg["FOTO_URL"], use_container_width=True)
else:
    st.info("Sin foto")

st.markdown(f"### {reg['PRODUCTO']}")
cliente = reg['CLIENTE'] if str(reg['CLIENTE']) != "nan" else "Sin nombre"
st.write(f"👤 **Cliente:** {cliente}")
if reg['ESTADO_PAGO'] == "🟡 Abonado":
    st.write(f"💰 **Abonado:** ${float(reg['MONTO_RECIBIDO']):,.2f}")
st.markdown(f"<h1 style='text-align:center; color:#00FFAA;'>${float(reg['VENTA_MXN']):,.2f}</h1>", unsafe_allow_html=True)

st.divider()

# 3. Botón de Pago con Doble Confirmación
with st.popover("✅ MARCAR COMO PAGADO", use_container_width=True):
    st.markdown("### ¿Recibiste el pago total?")
    if st.button("SÍ, CONFIRMAR", type="primary", use_container_width=True):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("Actualizado!")
        time.sleep(1)
        st.cache_data.clear()
        st.rerun()

# 4. Navegación: Botones Largos Izquierda/Derecha
col1, col2 = st.columns(2)
with col1:
    if st.button("⬅️ ANTERIOR", use_container_width=True):
        st.session_state.idx_c = (st.session_state.idx_c - 1) % len(pendientes)
        st.rerun()

with col2:
    if st.button("SIGUIENTE ➡️", use_container_width=True):
        st.session_state.idx_c = (st.session_state.idx_c + 1) % len(pendientes)
        st.rerun()

st.markdown(f"<p style='text-align:center;'>{st.session_state.idx_c + 1} de {len(pendientes)}</p>", unsafe_allow_html=True)

if st.button("🏠 MENÚ PRINCIPAL", use_container_width=True):
    st.switch_page("app.py")