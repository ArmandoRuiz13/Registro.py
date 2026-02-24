import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Flash", layout="centered")

# --- CSS PARA DISEÑO MODERNO Y BOTONES ALARGADOS ---
st.markdown("""
    <style>
    /* Estilo general de botones */
    .stButton button {
        border-radius: 20px !important;
        height: 3rem !important;
        width: 100% !important;
        transition: 0.2s;
        font-weight: 600 !important;
    }

    /* Botones de navegación (Anterior/Siguiente) */
    div[data-testid="stColumn"] .stButton button {
        background-color: #1E1E1E !important;
        border: 1px solid #444 !important;
        color: white !important;
    }

    /* Imagen redondeada y responsiva */
    img {
        border-radius: 15px;
        max-height: 300px;
        object-fit: cover;
        margin-bottom: 5px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
    }

    /* Textos informativos */
    .prod-title { font-size: 1.1rem; font-weight: bold; margin-bottom: 0px; text-align: center; color: white; }
    .client-text { color: #AAAAAA; font-size: 0.9rem; margin-bottom: 2px; text-align: center; }
    .price-text { color: #00FFAA; font-size: 1.6rem; font-weight: bold; margin-top: 0px; text-align: center; }
    
    /* Contador centralizado */
    .contador-text {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 3rem;
        font-size: 14px;
        color: #888;
        font-weight: bold;
    }

    /* Ajuste de contenedor principal */
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    
    /* Popover (Botón de Pago) */
    .stPopover button {
        border-radius: 12px !important;
        background-color: #FF4B4B11 !important;
        border: 1px solid #FF4B4B !important;
        color: #FF4B4B !important;
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
        st.error("Error de conexión con Sheets.")
        st.stop()

# --- LÓGICA DE DATOS ---
df_nube = leer_datos()
pendientes = df_nube[df_nube["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if pendientes.empty:
    st.balloons()
    st.success("¡Todo cobrado! ✨")
    if st.button("🏠 Inicio"): st.switch_page("app.py")
    st.stop()

# Manejo de posición
if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ ---

# 1. Estatus visual
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
st.markdown(f"<p style='color:{color_st}; font-size: 12px; font-weight: bold; text-align: center; margin-bottom: 8px; letter-spacing: 2px;'>{reg['ESTADO_PAGO'].upper()}</p>", unsafe_allow_html=True)

# 2. Imagen
foto_url = reg.get("FOTO_URL", "")
st.image(foto_url if str(foto_url) != "nan" else "https://via.placeholder.com/400x300?text=Sin+Foto", use_container_width=True)

# 3. NAVEGACIÓN (Botones centrados y alargados)
# Usamos una proporción [1.5, 1, 1.5] para que los botones crezcan hacia el centro
c1, c2, c3 = st.columns([1.5, 1, 1.5])

with c1:
    if st.button("⬅️ Ant.", key="prev", use_container_width=True):
        st.session_state.idx_c = (st.session_state.idx_c - 1) % len(pendientes)
        st.rerun()

with c2:
    st.markdown(f"<div class='contador-text'>{st.session_state.idx_c + 1} / {len(pendientes)}</div>", unsafe_allow_html=True)

with c3:
    if st.button("Sig. ➡️", key="next", use_container_width=True):
        st.session_state.idx_c = (st.session_state.idx_c + 1) % len(pendientes)
        st.rerun()

# 4. Información del producto
cliente_display = reg['CLIENTE'] if str(reg['CLIENTE']) != "nan" else "Sin Nombre"
st.markdown(f"<p class='prod-title'>{reg['PRODUCTO']}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='client-text'>👤 {cliente_display}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='price-text'>${float(reg['VENTA_MXN']):,.2f}</p>", unsafe_allow_html=True)

if reg['ESTADO_PAGO'] == "🟡 Abonado":
    st.markdown(f"<p style='color:#FFCC00; text-align:center; font-size:12px; margin-top:-10px;'>Abono actual: ${float(reg['MONTO_RECIBIDO']):,.2f}</p>", unsafe_allow_html=True)

# 5. Acciones Finales
st.markdown("---")
with st.popover("✅ MARCAR COMO PAGADO", use_container_width=True):
    st.markdown("<p style='text-align:center;'>¿Confirmas el pago total de este artículo?</p>", unsafe_allow_html=True)
    if st.button("SÍ, CONFIRMAR PAGO", type="primary", use_container_width=True):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("Pago registrado correctamente")
        time.sleep(0.6)
        st.cache_data.clear()
        st.rerun()

if st.button("🏠 Volver al Menú Principal", use_container_width=True):
    st.switch_page("app.py")