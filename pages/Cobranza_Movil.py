import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Flash", layout="centered")

# --- CSS MEJORADO (DISEÑO FIJO Y COMPACTO) ---
st.markdown("""
    <style>
    /* Contenedor principal sin tanto margen */
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    
    /* Imagen con tamaño fijo para que no mueva el contenido */
    .img-container {
        display: flex;
        justify-content: center;
        background-color: #111;
        border-radius: 15px;
        overflow: hidden;
        height: 220px; /* Tamaño fijo */
        margin-bottom: 10px;
    }
    .img-container img {
        height: 100%;
        object-fit: contain;
    }

    /* Estilo de los botones de navegación */
    .nav-btn button {
        background-color: #262730 !important;
        border: 1px solid #444 !important;
        color: #ddd !important;
        border-radius: 12px !important;
        height: 3.5rem !important;
        font-weight: bold !important;
    }
    
    .nav-btn button:hover {
        border-color: #00FFAA !important;
        color: white !important;
    }

    /* Textos compactos */
    .status-text { font-size: 11px; font-weight: bold; text-align: center; margin-bottom: 5px; letter-spacing: 2px; }
    .prod-title { font-size: 1.1rem; font-weight: bold; text-align: center; margin: 0; }
    .client-text { color: #888; font-size: 0.85rem; text-align: center; margin-bottom: 5px; }
    .price-text { color: #00FFAA; font-size: 1.5rem; font-weight: bold; text-align: center; margin: 0; }
    
    /* Contador central */
    .contador {
        display: flex;
        align-items: center;
        justify-content: center;
        color: #666;
        font-size: 0.9rem;
        height: 3.5rem;
    }

    /* Precarga invisible */
    .preload { display: none; }
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
    if st.button("🏠 Inicio"): st.switch_page("app.py")
    st.stop()

if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ ---

# 1. Estatus (Fijo arriba)
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
st.markdown(f"<p class='status-text' style='color:{color_st};'>{reg['ESTADO_PAGO'].upper()}</p>", unsafe_allow_html=True)

# 2. Imagen (Con tamaño controlado)
foto_url = reg.get("FOTO_URL", "")
url_final = foto_url if str(foto_url) != "nan" else "https://via.placeholder.com/400x300?text=Sin+Foto"
st.markdown(f"<div class='img-container'><img src='{url_final}'></div>", unsafe_allow_html=True)

# 3. Navegación (Botones largos y elegantes)
c1, c2, c3 = st.columns([1.5, 1, 1.5])
with c1:
    st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
    if st.button("⬅️ Ant.", use_container_width=True):
        st.session_state.idx_c = (st.session_state.idx_c - 1) % len(pendientes)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown(f"<div class='contador'>{st.session_state.idx_c + 1} / {len(pendientes)}</div>", unsafe_allow_html=True)

with c3:
    st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
    if st.button("Sig. ➡️", use_container_width=True):
        st.session_state.idx_c = (st.session_state.idx_c + 1) % len(pendientes)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 4. Info Producto
st.markdown(f"<p class='prod-title'>{reg['PRODUCTO']}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='client-text'>👤 {reg['CLIENTE'] if str(reg['CLIENTE']) != 'nan' else 'S/N'}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='price-text'>${float(reg['VENTA_MXN']):,.2f}</p>", unsafe_allow_html=True)

# 5. Botón de Cobro
st.write("")
with st.popover("✅ REGISTRAR PAGO", use_container_width=True):
    if st.button("CONFIRMAR PAGO TOTAL", type="primary", use_container_width=True):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("¡Pagado!")
        time.sleep(0.5)
        st.cache_data.clear()
        st.rerun()

# 6. Precarga de imágenes (Truco de velocidad)
# Cargamos la imagen anterior y las 2 siguientes de forma invisible
pre_indices = [(st.session_state.idx_c - 1) % len(pendientes), 
               (st.session_state.idx_c + 1) % len(pendientes),
               (st.session_state.idx_c + 2) % len(pendientes)]

preload_html = ""
for i in pre_indices:
    url = pendientes.iloc[i].get("FOTO_URL", "")
    if str(url) != "nan":
        preload_html += f"<img src='{url}' class='preload'>"

st.markdown(preload_html, unsafe_allow_html=True)

if st.button("🏠 Menú", use_container_width=True):
    st.switch_page("app.py")