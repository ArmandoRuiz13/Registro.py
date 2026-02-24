import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Flash", layout="centered")

# --- CSS PARA BOTONES MODERNOS Y DISEÑO COMPACTO ---
st.markdown("""
    <style>
    /* Botones de navegación tipo 'pill' (cápsula) */
    .stButton button {
        border-radius: 25px !important;
        height: 2.8rem !important;
        border: 1px solid #444 !important;
        background-color: #262730 !important;
        color: white !important;
        font-size: 16px !important;
        transition: 0.2s;
        width: 100%;
    }
    
    .stButton button:active {
        background-color: #555 !important;
        transform: scale(0.95);
    }

    /* Imagen redondeada y compacta */
    img {
        border-radius: 12px;
        max-height: 280px;
        object-fit: contain;
        margin-bottom: 2px;
    }

    /* Estilo para los textos reducidos */
    .prod-title { font-size: 1rem; font-weight: bold; margin-bottom: 0px; text-align: center; }
    .client-text { color: #888; font-size: 0.85rem; margin-bottom: 2px; text-align: center; }
    .price-text { color: #00FFAA; font-size: 1.4rem; font-weight: bold; margin-top: 0px; text-align: center; }
    
    /* Ajuste de contenedor principal */
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    
    /* Popover compacto */
    .stPopover button {
        border-radius: 10px !important;
        height: 3rem !important;
        background-color: #FF4B4B11 !important;
        border: 1px solid #FF4B4B !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN (Mantenida del código anterior) ---
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
# Filtramos solo lo que está pendiente de pago
pendientes = df_nube[df_nube["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if pendientes.empty:
    st.balloons()
    st.success("¡Todo cobrado! ✨")
    if st.button("🏠 Inicio"): st.switch_page("app.py")
    st.stop()

# Manejo de posición en el carrusel
if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ ---

# 1. Estatus (Texto pequeño arriba)
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
st.markdown(f"<p style='color:{color_st}; font-size: 11px; font-weight: bold; text-align: center; margin-bottom: 5px; letter-spacing: 1px;'>{reg['ESTADO_PAGO'].upper()}</p>", unsafe_allow_html=True)

# 2. Imagen
foto_url = reg.get("FOTO_URL", "")
st.image(foto_url if str(foto_url) != "nan" else "https://via.placeholder.com/400x300?text=Sin+Foto", use_container_width=True)

# 3. NAVEGACIÓN (Botones bonitos justo debajo de la imagen)
c1, c2, c3 = st.columns([1, 1.2, 1])
with c1:
    if st.button("⬅️"):
        st.session_state.idx_c = (st.session_state.idx_c - 1) % len(pendientes)
        st.rerun()
with c2:
    st.markdown(f"<p style='text-align:center; font-size: 13px; margin-top: 8px; color: #666;'>{st.session_state.idx_c + 1} / {len(pendientes)}</p>", unsafe_allow_html=True)
with c3:
    if st.button("➡️"):
        st.session_state.idx_c = (st.session_state.idx_c + 1) % len(pendientes)
        st.rerun()

# 4. Información del producto (Centrada y compacta)
cliente_display = reg['CLIENTE'] if str(reg['CLIENTE']) != "nan" else "S/N"
st.markdown(f"<p class='prod-title'>{reg['PRODUCTO']}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='client-text'>👤 {cliente_display}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='price-text'>${float(reg['VENTA_MXN']):,.2f}</p>", unsafe_allow_html=True)

if reg['ESTADO_PAGO'] == "🟡 Abonado":
    st.markdown(f"<p style='color:#FFCC00; text-align:center; font-size:11px; margin-top:-10px;'>Abono actual: ${float(reg['MONTO_RECIBIDO']):,.2f}</p>", unsafe_allow_html=True)

# 5. Botón de Cobro y Menú
st.write("")
with st.popover("✅ MARCAR PAGADO", use_container_width=True):
    st.markdown("<p style='text-align:center; font-size:14px;'>¿Confirmas el pago total?</p>", unsafe_allow_html=True)
    if st.button("SÍ, CONFIRMAR", type="primary", use_container_width=True):
        # Actualizamos en el DF original usando el índice guardado
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("✅ Pago registrado")
        time.sleep(0.5)
        st.cache_data.clear()
        st.rerun()

if st.button("🏠 Menú Principal", use_container_width=True):
    st.switch_page("app.py")