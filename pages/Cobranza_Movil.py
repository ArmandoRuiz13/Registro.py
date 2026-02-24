import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Flash", layout="centered")

# --- CSS DE ALTO NIVEL (BOTONES Y ESTATUS) ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; }
    
    /* Contenedor de Imagen Estilizado */
    .img-container {
        display: flex; justify-content: center;
        background: radial-gradient(circle, #222, #000);
        border-radius: 20px;
        height: 220px;
        margin-bottom: 15px;
        border: 1px solid #333;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
    }
    .img-container img { height: 100%; object-fit: contain; }

    /* BOTONES DE NAVEGACIÓN ESTILO NEUMÓRFICO/MODERNO */
    .stButton button {
        border-radius: 15px !important;
        height: 3.8rem !important;
        border: none !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }

    /* Estilo específico para Anterior/Siguiente */
    div[data-testid="stColumn"] .stButton button {
        background: linear-gradient(145deg, #2e313a, #1a1c23) !important;
        color: #00FFAA !important;
        font-size: 18px !important;
        box-shadow: 5px 5px 10px #0e0f13, -2px -2px 5px #3a3f4b !important;
    }

    div[data-testid="stColumn"] .stButton button:active {
        box-shadow: inset 2px 2px 5px #0e0f13 !important;
        transform: translateY(2px);
    }

    /* Estatus y Textos */
    .status-badge {
        padding: 4px 12px;
        border-radius: 10px;
        font-size: 10px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    .prod-title { font-size: 1.2rem; font-weight: bold; text-align: center; color: #fff; margin:0; }
    .client-text { color: #888; font-size: 0.9rem; text-align: center; margin-bottom: 2px; }
    .price-text { color: #00FFAA; font-size: 1.8rem; font-weight: 900; text-align: center; margin-bottom: 0px; }
    
    /* Info de Abono */
    .abono-info {
        background-color: rgba(255, 204, 0, 0.1);
        color: #FFCC00;
        padding: 5px;
        border-radius: 8px;
        font-size: 13px;
        text-align: center;
        margin-top: 5px;
        border: 1px dashed #FFCC00;
    }

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
    except:
        st.error("Error de conexión.")
        st.stop()

# --- LÓGICA ---
df_nube = leer_datos()
pendientes = df_nube[df_nube["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if pendientes.empty:
    st.balloons()
    st.success("¡Todo cobrado! ✨")
    if st.button("🏠 Inicio"): st.switch_page("app.py")
    st.stop()

if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ ---

# 1. Indicador de Estatus
color_st = "#FFCC00" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "#FF4B4B"
st.markdown(f"""<div style='text-align:center;'>
    <span class='status-badge' style='background:{color_st}22; color:{color_st}; border: 1px solid {color_st};'>
    {reg['ESTADO_PAGO'].replace('🔴 ', '').replace('🟡 ', '').upper()}</span>
    </div>""", unsafe_allow_html=True)

# 2. Imagen
foto_url = reg.get("FOTO_URL", "")
url_f = foto_url if str(foto_url) != "nan" else "https://via.placeholder.com/400x300?text=Sin+Foto"
st.markdown(f"<div class='img-container'><img src='{url_f}'></div>", unsafe_allow_html=True)

# 3. Navegación Profesional
c1, c2, c3 = st.columns([1.5, 1, 1.5])
with c1:
    if st.button("❮", use_container_width=True):
        st.session_state.idx_c = (st.session_state.idx_c - 1) % len(pendientes)
        st.rerun()
with c2:
    st.markdown(f"<div style='text-align:center; padding-top:15px; font-weight:bold; color:#555;'>{st.session_state.idx_c + 1}/{len(pendientes)}</div>", unsafe_allow_html=True)
with c3:
    if st.button("❯", use_container_width=True):
        st.session_state.idx_c = (st.session_state.idx_c + 1) % len(pendientes)
        st.rerun()

# 4. Información
st.markdown(f"<p class='prod-title'>{reg['PRODUCTO']}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='client-text'>👤 {reg['CLIENTE'] if str(reg['CLIENTE']) != 'nan' else 'S/N'}</p>", unsafe_allow_html=True)
st.markdown(f"<p class='price-text'>${float(reg['VENTA_MXN']):,.2f}</p>", unsafe_allow_html=True)

# Aquí aparece la información de abonos si aplica
if reg['ESTADO_PAGO'] == "🟡 Abonado":
    st.markdown(f"<div class='abono-info'>Abonado: ${float(reg['MONTO_RECIBIDO']):,.2f} | Resta: ${float(reg['VENTA_MXN'])-float(reg['MONTO_RECIBIDO']):,.2f}</div>", unsafe_allow_html=True)
else:
    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)

# 5. Registro de Pago
st.write("")
with st.popover("💰 REGISTRAR PAGO TOTAL", use_container_width=True):
    if st.button("CONFIRMAR RECEPCIÓN DE DINERO", type="primary", use_container_width=True):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("✅ Pago guardado")
        time.sleep(0.4)
        st.cache_data.clear()
        st.rerun()

# 6. Precarga inteligente
pre_indices = [(st.session_state.idx_c + i) % len(pendientes) for i in [-1, 1, 2]]
preload_html = "".join([f"<img src='{pendientes.iloc[i].get('FOTO_URL','')}' class='preload'>" for i in pre_indices if str(pendientes.iloc[i].get('FOTO_URL','')) != 'nan'])
st.markdown(preload_html, unsafe_allow_html=True)

if st.button("🏠 Menú", use_container_width=True):
    st.switch_page("app.py")