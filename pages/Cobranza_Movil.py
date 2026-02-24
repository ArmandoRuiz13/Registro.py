import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Express", layout="centered")

# --- CSS PARA FORZAR BOTONES LATERALES Y DISEÑO MÓVIL ---
st.markdown("""
    <style>
    /* Forzar que las columnas de navegación no se apilen en móvil */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 calc(33.33% - 1rem) !important;
        min-width: 0px !important;
    }
    
    /* Contenedor de la fila de navegación */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
    }

    .main-card {
        background-color: #1e1e1e;
        border-radius: 20px;
        padding: 15px;
        border: 1px solid #333;
    }
    
    .stButton button {
        border-radius: 12px !important;
        height: 3.5rem !important;
        width: 100%;
    }

    img {
        border-radius: 15px;
        margin-bottom: 10px;
        max-height: 300px;
        object-fit: contain;
    }

    .status-badge {
        text-align: center;
        font-weight: bold;
        padding: 8px;
        border-radius: 10px;
        margin-bottom: 10px;
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
        st.error("⚠️ Error de conexión.")
        st.stop()

# --- LÓGICA DE DATOS ---
df_nube = leer_datos()
pendientes = df_nube[df_nube["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if pendientes.empty:
    st.balloons()
    st.success("¡Todo cobrado! 🍻")
    if st.button("🏠 Volver al Menú"): st.switch_page("app.py")
    st.stop()

if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ ---

# 1. Estatus
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
st.markdown(f"""
    <div class="status-badge" style="background-color: {color_st}22; border: 1px solid {color_st}; color: {color_st};">
        {reg['ESTADO_PAGO']}
    </div>
    """, unsafe_allow_html=True)

if reg['ESTADO_PAGO'] == "🟡 Abonado":
    st.write(f"💰 **Abono previo:** ${float(reg['MONTO_RECIBIDO']):,.2f}")

# 2. Imagen y Datos
if reg.get("FOTO_URL") and str(reg["FOTO_URL"]) != "nan":
    st.image(reg["FOTO_URL"], use_container_width=True)

cliente_display = reg['CLIENTE'] if str(reg['CLIENTE']) != "nan" else "Sin nombre"
st.markdown(f"### {reg['PRODUCTO']}")
st.markdown(f"👤 **Cliente:** {cliente_display}")
st.markdown(f"<h2 style='color:#00FFAA; margin-top:0;'>${float(reg['VENTA_MXN']):,.2f}</h2>", unsafe_allow_html=True)

# 3. Botón de Cobro con Confirmación (Popover)
with st.popover("✅ MARCAR COMO PAGADO", use_container_width=True):
    st.warning("¿Confirmas el pago total?")
    if st.button("SÍ, CONFIRMAR", type="primary", use_container_width=True):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("✅ ¡Actualizado!")
        time.sleep(1)
        st.cache_data.clear()
        st.rerun()

st.write("") 

# 4. NAVEGACIÓN (FORZADA EN UNA FILA)
# Usamos columnas pero el CSS de arriba evita que se apilen
col_nav_izq, col_nav_txt, col_nav_der = st.columns([1, 1.5, 1])

with col_nav_izq:
    if st.button("⬅️"):
        st.session_state.idx_c = max(0, st.session_state.idx_c - 1)
        st.rerun()

with col_nav_txt:
    # Centramos el texto verticalmente para que alinee con los botones
    st.markdown(f"<p style='text-align:center; font-weight:bold; margin-top:15px;'>{st.session_state.idx_c + 1} / {len(pendientes)}</p>", unsafe_allow_html=True)

with col_nav_der:
    if st.button("➡️"):
        st.session_state.idx_c = min(len(pendientes)-1, st.session_state.idx_c + 1)
        st.rerun()

st.divider()
if st.button("🏠 Menú Principal", use_container_width=True):
    st.switch_page("app.py")