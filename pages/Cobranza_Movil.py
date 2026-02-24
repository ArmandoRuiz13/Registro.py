import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN PARA iPHONE 16 PRO ---
st.set_page_config(page_title="Cobranza Pro", layout="centered")

# CSS Avanzado para Interfaz Móvil Premium
st.markdown("""
    <style>
    /* Ajuste para evitar el notch y la barra inferior del iPhone */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
    }
    
    /* Tarjeta contenedora */
    .stColumn {
        padding: 0px !important;
    }
    
    /* Imagen con proporción optimizada para 16 Pro */
    img {
        border-radius: 24px;
        object-fit: cover;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
        margin-bottom: 10px;
    }

    /* Botones de navegación laterales */
    .nav-btn button {
        background-color: #262626 !important;
        border: 1px solid #404040 !important;
        border-radius: 50% !important;
        width: 50px !important;
        height: 50px !important;
    }

    /* Botón de pago principal */
    div[data-testid="stPopover"] > button {
        background-color: #007AFF !important; /* Azul iOS */
        color: white !important;
        border-radius: 14px !important;
        height: 3.5rem !important;
        font-weight: bold !important;
    }

    /* Ocultar elementos innecesarios en móvil */
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def leer_datos():
    try:
        st.cache_data.clear()
        df = conn.read(ttl=0) 
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        st.error("Error de conexión con la sábana de datos.")
        st.stop()

# --- PROCESAMIENTO ---
df_nube = leer_datos()
# Filtramos solo lo pendiente (Debe o Abonado)
pendientes = df_nube[df_nube["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if pendientes.empty:
    st.balloons()
    st.success("¡Todo cobrado! ✨")
    if st.button("Regresar al Menú"): st.switch_page("app.py")
    st.stop()

if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ DINÁMICA ---

# 1. Estatus (Header minimalista)
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
        <span style="background: {color_st}33; color: {color_st}; padding: 4px 12px; border-radius: 20px; font-weight: bold; border: 1px solid {color_st};">
            {reg['ESTADO_PAGO']}
        </span>
        <span style="color: #888;">{st.session_state.idx_c + 1} de {len(pendientes)}</span>
    </div>
    """, unsafe_allow_html=True)

# 2. Área Visual
if reg.get("FOTO_URL") and str(reg["FOTO_URL"]) != "nan":
    st.image(reg["FOTO_URL"], use_container_width=True)

# 3. Información del Producto
if reg['ESTADO_PAGO'] == "🟡 Abonado":
    st.caption(f"💰 Ya abonó: ${float(reg['MONTO_RECIBIDO']):,.2f}")

st.subheader(reg['PRODUCTO'])
cliente = reg['CLIENTE'] if str(reg['CLIENTE']) != "nan" else "Cliente General"
st.markdown(f"👤 **{cliente}**")
st.markdown(f"<h1 style='margin:0; color: #FFFFFF;'>${float(reg['VENTA_MXN']):,.2f}</h1>", unsafe_allow_html=True)

st.write("")

# 4. Acción de Cobro (Con Popover de confirmación para evitar errores)
with st.popover("确认 ✅ PAGAR TOTAL", use_container_width=True):
    st.markdown("### ¿Recibiste el pago total?")
    st.write("Esta acción marcará el producto como pagado y actualizará el monto recibido.")
    if st.button("SÍ, CONFIRMAR", type="primary", use_container_width=True):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("Actualizando...")
        time.sleep(1)
        st.cache_data.clear()
        st.rerun()

st.write("")

# 5. Navegación Inferior (Diseño de flechas laterales separadas)
nav_col1, nav_col2, nav_col3 = st.columns([1, 0.5, 1])

with nav_col1:
    if st.button("⬅️", use_container_width=True, key="prev"):
        st.session_state.idx_c = max(0, st.session_state.idx_c - 1)
        st.rerun()

with nav_col3:
    if st.button("➡️", use_container_width=True, key="next"):
        st.session_state.idx_c = min(len(pendientes)-1, st.session_state.idx_c + 1)
        st.rerun()

st.markdown("---")
if st.button("🏠 Inicio", use_container_width=True):
    st.switch_page("app.py")