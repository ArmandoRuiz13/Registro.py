import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Flash", layout="centered")

# --- CSS RADICAL PARA PANTALLA ÚNICA ---
st.markdown("""
    <style>
    /* Eliminar márgenes de Streamlit */
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; max-width: 400px !important; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Contenedor de Imagen con Estatus Flotante */
    .img-wrapper {
        position: relative;
        width: 100%;
        height: 200px; /* Reducido para ganar espacio */
        background-color: #000;
        border-radius: 15px;
        overflow: hidden;
        margin-bottom: 5px;
    }
    .img-wrapper img {
        width: 100%; height: 100%; object-fit: contain;
    }
    
    /* Estatus flotando sobre la imagen */
    .floating-status {
        position: absolute;
        top: 10px;
        right: 10px;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: bold;
        z-index: 10;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.5);
    }

    /* Botones de Navegación Compactos */
    .stButton button {
        border-radius: 12px !important;
        height: 3rem !important; /* Más bajos para ahorrar espacio */
        transition: 0.2s;
        font-weight: bold !important;
    }
    
    /* Estilo flechas */
    .nav-col button {
        background: #262730 !important;
        border: 1px solid #444 !important;
        color: #00FFAA !important;
        font-size: 20px !important;
    }

    /* Textos Ultra-Compactos */
    .prod-title { font-size: 1rem; font-weight: bold; text-align: center; margin: 0; line-height: 1.1; }
    .client-text { color: #888; font-size: 0.8rem; text-align: center; margin: 0; }
    .price-text { color: #00FFAA; font-size: 1.4rem; font-weight: bold; text-align: center; margin: 0; }
    
    .abono-text {
        color: #FFCC00; font-size: 0.8rem; text-align: center; 
        background: rgba(255,204,0,0.1); border-radius: 5px; margin: 2px 0;
    }

    /* Ocultar elementos de precarga */
    .preload-img { display: none; }
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
    except:
        st.error("Error de conexión.")
        st.stop()

# --- LÓGICA ---
df_nube = leer_datos()
pendientes = df_nube[df_nube["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if pendientes.empty:
    st.success("¡Todo cobrado! ✨")
    st.stop()

if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ DE UN SOLO VISTAZO ---

# 1. Imagen + Estatus Flotante
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
label_st = "ABONADO" if "Abonado" in reg['ESTADO_PAGO'] else "DEBE"
foto_url = reg.get("FOTO_URL", "")
url_f = foto_url if str(foto_url) != "nan" else "https://via.placeholder.com/400x300?text=Sin+Foto"

st.markdown(f"""
    <div class="img-wrapper">
        <div class="floating-status" style="background: {color_st}; color: black;">{label_st}</div>
        <img src="{url_f}">
    </div>
    """, unsafe_allow_html=True)

# 2. Navegación (Más pegada a la imagen)
c1, c2, c3 = st.columns([1, 0.8, 1])
with c1:
    st.markdown('<div class="nav-col">', unsafe_allow_html=True)
    if st.button("❮", key="btn_prev", use_container_width=True):
        st.session_state.idx_c = (st.session_state.idx_c - 1) % len(pendientes)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown(f"<p style='text-align:center; font-size:12px; margin-top:12px; font-weight:bold;'>{st.session_state.idx_c + 1}/{len(pendientes)}</p>", unsafe_allow_html=True)
with c3:
    st.markdown('<div class="nav-col">', unsafe_allow_html=True)
    if st.button("❯", key="btn_next", use_container_width=True):
        st.session_state.idx_c = (st.session_state.idx_c + 1) % len(pendientes)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 3. Datos del Producto
st.markdown(f"<p class='prod-title'>{reg['PRODUCTO']}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='client-text'>👤 {reg['CLIENTE'] if str(reg['CLIENTE']) != 'nan' else 'S/N'}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='price-text'>${float(reg['VENTA_MXN']):,.2f}</p>", unsafe_allow_html=True)

if label_st == "ABONADO":
    st.markdown(f"<p class='abono-text'>Abonó: ${float(reg['MONTO_RECIBIDO']):,.2f} | Falta: ${float(reg['VENTA_MXN'])-float(reg['MONTO_RECIBIDO']):,.2f}</p>", unsafe_allow_html=True)
else:
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

# 4. Acción Principal (Popover más pequeño)
with st.popover("✅ PAGAR TODO", use_container_width=True):
    if st.button("CONFIRMAR PAGO", type="primary", use_container_width=True):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("✅ ¡Listo!")
        time.sleep(0.3)
        st.cache_data.clear()
        st.rerun()

# --- PRECARGA DE IMÁGENES MEJORADA ---
# Precargamos las siguientes 3 imágenes para que al dar "Sig" ya estén en caché
preload_html = ""
for i in range(1, 4):
    next_idx = (st.session_state.idx_c + i) % len(pendientes)
    next_url = pendientes.iloc[next_idx].get("FOTO_URL", "")
    if str(next_url) != "nan":
        preload_html += f"<img src='{next_url}' class='preload-img'>"

st.markdown(preload_html, unsafe_allow_html=True)

if st.button("🏠 Menú Principal", use_container_width=True):
    st.switch_page("app.py")