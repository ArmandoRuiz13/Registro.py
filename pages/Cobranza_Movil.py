import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Flash", layout="centered")

# --- CSS RADICAL PARA PANTALLA ÚNICA ---
st.markdown("""
    <style>
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; max-width: 400px !important; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .img-wrapper {
        position: relative;
        width: 100%;
        height: 200px;
        background-color: #000;
        border-radius: 15px;
        overflow: hidden;
        margin-bottom: 5px;
    }
    .img-wrapper img { width: 100%; height: 100%; object-fit: contain; }
    
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

    .stButton button {
        border-radius: 12px !important;
        height: 3rem !important;
        font-weight: bold !important;
    }
    
    .nav-col button {
        background: #262730 !important;
        border: 1px solid #444 !important;
        color: #00FFAA !important;
        font-size: 20px !important;
    }

    .prod-title { font-size: 1rem; font-weight: bold; text-align: center; margin: 0; line-height: 1.1; }
    .client-text { color: #888; font-size: 0.8rem; text-align: center; margin: 0; }
    .price-text { color: #00FFAA; font-size: 1.4rem; font-weight: bold; text-align: center; margin: 0; }
    
    .abono-text {
        color: #FFCC00; font-size: 0.8rem; text-align: center; 
        background: rgba(255,204,0,0.1); border-radius: 5px; margin: 2px 0;
    }

    .preload-img { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def leer_datos():
    try:
        # TTL de 10 segundos para balancear frescura y velocidad de navegación
        df = conn.read(ttl=10) 
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except:
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

# 1. Imagen + Estatus Flotante con KEY ROTATION
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
label_st = "ABONADO" if "Abonado" in reg['ESTADO_PAGO'] else "DEBE"
foto_url = reg.get("FOTO_URL", "")
url_f = foto_url if str(foto_url) != "nan" and str(foto_url) != "" else "https://via.placeholder.com/400x300?text=Sin+Foto"

# La "key" dinámica obliga a refrescar la imagen correctamente en el salto de página
st.markdown(f"""
    <div class="img-wrapper" key="wrapper_{st.session_state.idx_c}">
        <div class="floating-status" style="background: {color_st}; color: black;">{label_st}</div>
        <img src="{url_f}?v={st.session_state.idx_c}">
    </div>
    """, unsafe_allow_html=True)

# 2. Navegación con Bloqueo de Colapso
c1, c2, c3 = st.columns([1, 0.8, 1])

def cambiar_indice(delta):
    nueva_pos = (st.session_state.idx_c + delta) % len(pendientes)
    st.session_state.idx_c = nueva_pos
    time.sleep(0.05) # Pausa mínima técnica
    st.rerun()

with c1:
    st.markdown('<div class="nav-col">', unsafe_allow_html=True)
    if st.button("❮", key=f"prev_{st.session_state.idx_c}", use_container_width=True):
        cambiar_indice(-1)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown(f"<p style='text-align:center; font-size:12px; margin-top:12px; font-weight:bold;'>{st.session_state.idx_c + 1}/{len(pendientes)}</p>", unsafe_allow_html=True)

with c3:
    st.markdown('<div class="nav-col">', unsafe_allow_html=True)
    if st.button("❯", key=f"next_{st.session_state.idx_c}", use_container_width=True):
        cambiar_indice(1)
    st.markdown('</div>', unsafe_allow_html=True)

# 3. Datos del Producto
st.markdown(f"<p class='prod-title'>{reg['PRODUCTO']}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='client-text'>👤 {reg['CLIENTE'] if str(reg['CLIENTE']) != 'nan' else 'S/N'}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='price-text'>${float(reg['VENTA_MXN']):,.2f}</p>", unsafe_allow_html=True)

if label_st == "ABONADO":
    monto_rec = float(reg['MONTO_RECIBIDO']) if str(reg['MONTO_RECIBIDO']) != 'nan' else 0.0
    st.markdown(f"<p class='abono-text'>Abonó: ${monto_rec:,.2f} | Falta: ${float(reg['VENTA_MXN'])-monto_rec:,.2f}</p>", unsafe_allow_html=True)
else:
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

# 4. Acción de Pago
with st.popover("✅ PAGAR TODO", use_container_width=True):
    if st.button("CONFIRMAR PAGO", type="primary", use_container_width=True, key=f"pay_{idx_original}"):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("✅ ¡Registrado!")
        time.sleep(0.5)
        st.cache_data.clear()
        st.rerun()

# --- PRECARGA MÁS INTELIGENTE ---
# Precargamos tanto la anterior como la siguiente para saltos rápidos en ambos sentidos
preload_indices = [
    (st.session_state.idx_c - 1) % len(pendientes),
    (st.session_state.idx_c + 1) % len(pendientes)
]
preload_html = ""
for i in preload_indices:
    url = pendientes.iloc[i].get("FOTO_URL", "")
    if str(url) != "nan" and url != "":
        preload_html += f'<img src="{url}" class="preload-img">'
st.markdown(preload_html, unsafe_allow_html=True)

if st.button("🏠 Menú", use_container_width=True):
    st.switch_page("app.py")