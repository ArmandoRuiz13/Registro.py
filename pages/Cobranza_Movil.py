import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Express", layout="centered")

# --- CSS PARA DISEÑO "MOBILE-FRIENDLY" ESTABLE ---
st.markdown("""
    <style>
    /* Tarjeta contenedora de datos */
    .data-card {
        background-color: #1e1e1e;
        border-radius: 15px;
        padding: 15px;
        border: 1px solid #333;
        margin-bottom: 10px;
    }
    
    /* Botones grandes y estilizados */
    .stButton button {
        border-radius: 12px !important;
        height: 3.8rem !important;
        font-size: 18px !important;
        font-weight: bold !important;
        width: 80% !important; /* No ocupan todo el ancho */
        margin: 0 auto !important;
        display: block !important;
    }

    /* Imagen con límite de altura para evitar scroll infinito */
    img {
        border-radius: 15px;
        margin-bottom: 10px;
        max-height: 280px;
        object-fit: contain;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }

    /* Badge de estatus */
    .status-badge {
        text-align: center;
        font-weight: bold;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 15px;
        font-size: 20px;
    }
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
        st.error("⚠️ Error de conexión con la base de datos.")
        st.stop()

# --- LÓGICA DE DATOS ---
df_nube = leer_datos()
# Filtramos lo pendiente (Debe o Abonado)
pendientes = df_nube[df_nube["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if pendientes.empty:
    st.balloons()
    st.success("¡Excelente! No hay cuentas pendientes. 🥂")
    if st.button("🏠 Menú Inicio"): st.switch_page("app.py")
    st.stop()

# Índice de sesión
if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ VISUAL ---

# 1. Indicador de Estatus Superior
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
st.markdown(f"""
    <div class="status-badge" style="background-color: {color_st}22; border: 2px solid {color_st}; color: {color_st};">
        {reg['ESTADO_PAGO']}
    </div>
    """, unsafe_allow_html=True)

if reg['ESTADO_PAGO'] == "🟡 Abonado":
    st.markdown(f"<p style='text-align:center;'>💰 <b>Abonado:</b> ${float(reg['MONTO_RECIBIDO']):,.2f}</p>", unsafe_allow_html=True)

# 2. Imagen
if reg.get("FOTO_URL") and str(reg["FOTO_URL"]) != "nan":
    st.image(reg["FOTO_URL"])

# 3. Información del Producto
cliente_display = reg['CLIENTE'] if str(reg['CLIENTE']) != "nan" else "N/A"
st.markdown(f"""
    <div style="text-align: center;">
        <h2 style="margin-bottom:0;">{reg['PRODUCTO']}</h2>
        <p style="color: #aaa; font-size: 18px;">👤 Cliente: {cliente_display}</p>
        <h1 style="color: #00FFAA; margin-top:0;">${float(reg['VENTA_MXN']):,.2f}</h1>
    </div>
    """, unsafe_allow_html=True)

# 4. Botón de Cobro (Con confirmación Popover)
st.write("")
with st.popover("✅ REGISTRAR PAGO TOTAL", use_container_width=True):
    st.markdown("### ¿Confirmas el pago?")
    st.write("Esta acción marcará el producto como pagado y actualizará el monto recibido.")
    if st.button("SÍ, CONFIRMAR", type="primary", use_container_width=True):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("✅ ¡Pago registrado!")
        time.sleep(1)
        st.cache_data.clear()
        st.rerun()

st.divider()

# 5. Navegación (Botones apilados, grandes y bonitos)
st.markdown(f"<p style='text-align:center;'>Registro {st.session_state.idx_c + 1} de {len(pendientes)}</p>", unsafe_allow_html=True)

if st.button("Siguiente ➡️", use_container_width=True):
    if st.session_state.idx_c < len(pendientes) - 1:
        st.session_state.idx_c += 1
    else:
        st.session_state.idx_c = 0 # Reinicia el carrusel
    st.rerun()

if st.button("⬅️ Anterior", use_container_width=True):
    if st.session_state.idx_c > 0:
        st.session_state.idx_c -= 1
    st.rerun()

st.write("")
if st.button("🏠 Menú Principal", use_container_width=True):
    st.switch_page("app.py")