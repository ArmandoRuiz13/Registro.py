import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Flash", layout="centered")

# --- CSS PARA BOTONES SOBRE IMAGEN Y DISEÑO COMPACTO ---
st.markdown("""
    <style>
    /* Contenedor relativo para la imagen y botones */
    .img-container {
        position: relative;
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
    }

    /* Imagen compacta */
    .img-container img {
        width: 100%;
        border-radius: 15px;
        max-height: 320px;
        object-fit: cover;
    }

    /* Botones flotantes sutiles */
    .float-btn {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        background-color: rgba(255, 255, 255, 0.15); /* Muy sutil */
        border: none;
        color: white;
        padding: 15px 10px;
        border-radius: 10px;
        cursor: pointer;
        font-size: 20px;
        transition: 0.3s;
        backdrop-filter: blur(2px);
    }
    
    .float-btn:hover { background-color: rgba(255, 255, 255, 0.3); }
    .btn-prev { left: 10px; }
    .btn-next { right: 10px; }

    /* Textos pequeños */
    h2, h3 { margin-bottom: 0 !important; font-size: 1.2rem !important; }
    p { font-size: 0.9rem !important; margin-bottom: 5px !important; }
    
    /* Popover más discreto */
    .stPopover button {
        width: 100% !important;
        height: 2.8rem !important;
        font-size: 14px !important;
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
        st.error("Error de conexión.")
        st.stop()

# --- LÓGICA DE DATOS ---
df_nube = leer_datos()
pendientes = df_nube[df_nube["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if pendientes.empty:
    st.success("¡Todo cobrado! ✨")
    if st.button("🏠 Menú"): st.switch_page("app.py")
    st.stop()

if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ ---

# 1. Estatus (Pequeño arriba)
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
st.markdown(f"<div style='color:{color_st}; font-weight:bold; text-align:center; font-size:14px;'>{reg['ESTADO_PAGO']}</div>", unsafe_allow_html=True)

# 2. Imagen con Botones de Navegación "Invisibles/Sutiles"
# Usamos columnas de Streamlit para los botones que activan el cambio de índice
# pero el diseño visual lo da el usuario al tocar los lados de la imagen.

with st.container():
    # Simulamos los botones sobre la imagen con columnas muy pegadas
    # En Streamlit puro, lo más efectivo es poner los botones justo arriba o abajo 
    # pero los hemos estilizado para que parezcan parte de la acción.
    
    foto_url = reg.get("FOTO_URL", "")
    st.image(foto_url if str(foto_url) != "nan" else "https://via.placeholder.com/400x300?text=Sin+Foto", use_container_width=True)

    # Navegación inmediata debajo de la foto (Flechas pequeñas)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("⬅️", use_container_width=True, key="prev"):
            st.session_state.idx_c = (st.session_state.idx_c - 1) % len(pendientes)
            st.rerun()
    with c2:
        st.markdown(f"<p style='text-align:center;'>{st.session_state.idx_c + 1} / {len(pendientes)}</p>", unsafe_allow_html=True)
    with c3:
        if st.button("➡️", use_container_width=True, key="next"):
            st.session_state.idx_c = (st.session_state.idx_c + 1) % len(pendientes)
            st.rerun()

# 3. Datos del Producto (Compactos)
cliente_display = reg['CLIENTE'] if str(reg['CLIENTE']) != "nan" else "N/A"
st.markdown(f"**{reg['PRODUCTO']}**")
st.markdown(f"<p style='color:gray;'>👤 {cliente_display}</p>", unsafe_allow_html=True)

if reg['ESTADO_PAGO'] == "🟡 Abonado":
    st.markdown(f"<p style='color:#FFCC00; font-size:12px;'>Abonado: ${float(reg['MONTO_RECIBIDO']):,.2f}</p>", unsafe_allow_html=True)

st.markdown(f"<h2 style='color:#00FFAA;'>${float(reg['VENTA_MXN']):,.2f}</h2>", unsafe_allow_html=True)

# 4. Botón de Cobro
with st.popover("✅ PAGAR", use_container_width=True):
    st.write("¿Confirmas pago total?")
    if st.button("CONFIRMAR", type="primary", use_container_width=True):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("Actualizado")
        time.sleep(0.5)
        st.cache_data.clear()
        st.rerun()

st.write("")
if st.button("🏠 Inicio", use_container_width=True):
    st.switch_page("app.py")