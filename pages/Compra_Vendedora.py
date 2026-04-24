import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="S&R Lolis - Gestión Móvil", layout="centered")

# 🔑 CONFIGURACIÓN DE CLOUDINARY
CLOUD_NAME = "doi81tooh"
API_KEY = "245491997239959"
API_SECRET = "8Hgvfh6amI8vd0W_rG43HnSb2OI"

# --- CSS PARA IPHONE 16 PRO (Imagen y Botones) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stImage"] img {
        max-height: 350px;
        object-fit: cover;
        border-radius: 15px;
    }
    .stButton button {
        border-radius: 12px;
        height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ESTADO DE SESIÓN ---
if "view_mode" not in st.session_state: st.session_state.view_mode = False
if "idx_carousel" not in st.session_state: st.session_state.idx_carousel = 0

# --- FUNCIONES ---
@st.cache_data(ttl=3600)
def obtener_tc():
    try: 
        res = requests.get("https://open.er-api.com/v6/latest/USD").json()
        return round(res["rates"]["MXN"], 2)
    except: return 18.50

def limpiar_num(val):
    try: return float(str(val).replace(',', '').replace('$', '')) if val else 0.0
    except: return 0.0

def subir_a_nube(archivo_imagen):
    try:
        url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
        data = {"upload_preset": "ml_default", "api_key": API_KEY}
        files = {"file": archivo_imagen.getvalue()}
        res = requests.post(url, data=data, files=files)
        return res.json().get("secure_url") if res.status_code == 200 else None
    except: return None

conn = st.connection("gsheets", type=GSheetsConnection)

def lectura_compradora():
    try: 
        df = conn.read(worksheet="CompradoraV", ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [str(c).strip() for c in df.columns]
        # Asegurar tipos numéricos
        for col in ["Costo_MXN", "Abono", "Saldo"]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def actualizar_estado(df, idx, campo, valor):
    df.at[idx, campo] = valor
    if campo == "Liquidado" and valor == "SÍ":
        df.at[idx, "Fecha_Liquidacion"] = datetime.now().strftime("%d/%m/%Y")
        df.at[idx, "Saldo"] = 0.0
    elif campo == "Liquidado" and valor == "NO":
        df.at[idx, "Fecha_Liquidacion"] = "Pendiente"
        df.at[idx, "Saldo"] = df.at[idx, "Costo_MXN"] - df.at[idx, "Abono"]
    
    conn.update(worksheet="CompradoraV", data=df)
    st.cache_data.clear()
    st.toast(f"✅ {campo} actualizado")
    time.sleep(0.5)

# --- INICIO ---
tc_actual = obtener_tc()
df_cv = lectura_compradora()

st.title("🛍️ Compra Vendedora")

# --- NAVEGACIÓN SUPERIOR ---
nav_c1, nav_c2 = st.columns(2)
with nav_c1:
    if st.button("⬅️ Menú", use_container_width=True): st.switch_page("app.py")
with nav_c2:
    label = "📱 Ver Pedidos" if not st.session_state.view_mode else "📝 Registro"
    if st.button(label, use_container_width=True, type="primary"):
        st.session_state.view_mode = not st.session_state.view_mode
        st.rerun()

st.divider()

# ---------------------------------------------------------
# MODO REGISTRO (POR DEFECTO Y DESPLEGADO)
# ---------------------------------------------------------
if not st.session_state.view_mode:
    with st.expander("🚀 NUEVO REGISTRO", expanded=True):
        with st.form("form_fast", clear_on_submit=True):
            f_prod = st.text_input("Nombre del Producto")
            f_cli = st.text_input("Cliente")
            f_foto = st.file_uploader("📷 Foto", type=["jpg", "png", "jpeg"])
            
            # Inputs de texto directo para evitar el +/-
            col_u, col_a = st.columns(2)
            f_usd_txt = col_u.text_input("Costo USD", placeholder="0.00")
            f_abono_txt = col_a.text_input("Abono MXN", placeholder="0.00")
            
            if st.form_submit_button("✅ GUARDAR REGISTRO", use_container_width=True):
                v_usd = limpiar_num(f_usd_txt)
                v_abono = limpiar_num(f_abono_txt)
                
                if f_prod and v_usd > 0:
                    with st.spinner("Subiendo..."):
                        url_foto = subir_a_nube(f_foto) if f_foto else "https://via.placeholder.com/150"
                        costo_mxn = round(((v_usd * 1.0825) * tc_actual) + (((v_usd * 1.0825) * 0.12) * 19), 2)
                        
                        nuevo_reg = {
                            "ID": len(df_cv) + 1,
                            "Fecha_Registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Producto": f_prod, "Cliente": f_cli if f_cli else "N/A",
                            "Foto_URL": url_foto, "Costo_USD": v_usd, "Costo_MXN": costo_mxn,
                            "Abono": v_abono, "Saldo": costo_mxn - v_abono,
                            "Entregado": "NO", "Liquidado": "NO", "Fecha_Liquidacion": "Pendiente"
                        }
                        df_f = pd.concat([df_cv, pd.DataFrame([nuevo_reg])], ignore_index=True)
                        conn.update(worksheet="CompradoraV", data=df_f)
                        st.cache_data.clear()
                        st.success("¡Registrado!")
                        time.sleep(1)
                        st.rerun()

    # Mini lista rápida debajo del registro
    if not df_cv.empty:
        st.subheader("📋 Últimos movimientos")
        st.dataframe(
            df_cv.tail(5).sort_index(ascending=False),
            column_config={"Foto_URL": st.column_config.ImageColumn("🖼️"), "ID": None},
            use_container_width=True, hide_index=True
        )

# ---------------------------------------------------------
# MODO CARRUSEL (OPTIMIZADO IPHONE 16 PRO)
# ---------------------------------------------------------
else:
    df_p = df_cv[df_cv["Liquidado"] == "NO"].copy()
    
    if df_p.empty:
        st.success("¡Todo liquidado! 🟢")
    else:
        if st.session_state.idx_carousel >= len(df_p): st.session_state.idx_carousel = 0
        
        item = df_p.iloc[st.session_state.idx_carousel]
        real_idx = df_p.index[st.session_state.idx_carousel]

        # Card Visual
        with st.container(border=True):
            st.image(item["Foto_URL"], use_container_width=True)
            st.subheader(item["Producto"])
            st.caption(f"👤 Cliente: {item['Cliente']}")
            
            # MÉTRICAS DE PAGO CLARAS
            m1, m2, m3 = st.columns(3)
            m1.metric("Total", f"${item['Costo_MXN']:,.0f}")
            m2.metric("Abono", f"${item['Abono']:,.0f}")
            m3.metric("Saldo", f"${item['Saldo']:,.0f}", delta_color="inverse")
            
            st.divider()
            
            # ACCIONES CON CONFIRMACIÓN
            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if item["Entregado"] == "NO":
                    with st.popover("📦 Entregar", use_container_width=True):
                        if st.button("CONFIRMAR ENTREGA", key=f"e_{real_idx}"):
                            actualizar_estado(df_cv, real_idx, "Entregado", "SÍ")
                            st.rerun()
                else:
                    st.button("✅ ENTREGADO", disabled=True, use_container_width=True)

            with btn_c2:
                with st.popover("💰 Liquidar", use_container_width=True):
                    if st.button("CONFIRMAR PAGO TOTAL", key=f"l_{real_idx}"):
                        actualizar_estado(df_cv, real_idx, "Liquidado", "SÍ")
                        st.rerun()

        # NAVEGACIÓN ESTILO SWIPE
        st.write("")
        nav_b1, nav_b2 = st.columns(2)
        if nav_b1.button("⬅️ Anterior", use_container_width=True) and st.session_state.idx_carousel > 0:
            st.session_state.idx_carousel -= 1
            st.rerun()
        if nav_b2.button("Siguiente ➡️", use_container_width=True) and st.session_state.idx_carousel < len(df_p) - 1:
            st.session_state.idx_carousel += 1
            st.rerun()