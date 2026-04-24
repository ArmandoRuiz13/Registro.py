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

# --- ESTADO DE SESIÓN PARA NAVEGACIÓN ---
if "view_mode" not in st.session_state:
    st.session_state.view_mode = False
if "idx_carousel" not in st.session_state:
    st.session_state.idx_carousel = 0

# --- FUNCIONES DE APOYO ---
@st.cache_data(ttl=3600)
def obtener_tc():
    try: 
        res = requests.get("https://open.er-api.com/v6/latest/USD").json()
        return round(res["rates"]["MXN"], 2)
    except: return 18.50

def subir_a_nube(archivo_imagen):
    try:
        url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
        data = {"upload_preset": "ml_default", "api_key": API_KEY}
        files = {"file": archivo_imagen.getvalue()}
        res = requests.post(url, data=data, files=files)
        return res.json().get("secure_url") if res.status_code == 200 else None
    except: return None

# --- CONEXIÓN Y LECTURA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def lectura_compradora():
    try: 
        df = conn.read(worksheet="CompradoraV", ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return pd.DataFrame()

# --- LÓGICA DE ACTUALIZACIÓN RÁPIDA ---
def actualizar_estado(df, idx, campo, valor):
    """Actualiza un campo específico y sincroniza con Google Sheets."""
    df.at[idx, campo] = valor
    if campo == "Liquidado" and valor == "SÍ":
        df.at[idx, "Fecha_Liquidacion"] = datetime.now().strftime("%d/%m/%Y")
        df.at[idx, "Saldo"] = 0.0
    elif campo == "Liquidado" and valor == "NO":
        df.at[idx, "Fecha_Liquidacion"] = "Pendiente"
        df.at[idx, "Saldo"] = df.at[idx, "Costo_MXN"] - df.at[idx, "Abono"]
    
    conn.update(worksheet="CompradoraV", data=df)
    st.cache_data.clear()
    st.toast(f"✅ {campo} actualizado correctamente")
    time.sleep(1)

# --- INICIO ---
tc_actual = obtener_tc()
df_cv = lectura_compradora()

# Header Estilo iPhone
st.title("🛍️ Compra Vendedora")

c1, c2 = st.columns(2)
with c1:
    if st.button("⬅️ Menú Principal", use_container_width=True):
        st.switch_page("app.py")
with c2:
    # BOTÓN PARA ACTIVAR MODO CARRUSEL
    label_boton = "📱 Ver Pedidos" if not st.session_state.view_mode else "📝 Volver a Lista"
    if st.button(label_boton, use_container_width=True, type="primary"):
        st.session_state.view_mode = not st.session_state.view_mode
        st.rerun()

st.divider()

# ---------------------------------------------------------
# MODO CARRUSEL (UI/UX IPHONE 16 PRO)
# ---------------------------------------------------------
if st.session_state.view_mode:
    if df_cv.empty:
        st.info("No hay pedidos para mostrar.")
    else:
        # Filtrar solo los no liquidados para que el carrusel sea útil
        df_pendientes = df_cv[df_cv["Liquidado"] == "NO"].copy()
        
        if df_pendientes.empty:
            st.success("¡Felicidades! Todo está liquidado. 🟢")
            if st.button("Ver Historial Completo"):
                st.session_state.view_mode = False
                st.rerun()
        else:
            total_p = len(df_pendientes)
            # Asegurar que el índice no se pase
            if st.session_state.idx_carousel >= total_p:
                st.session_state.idx_carousel = 0
            
            item = df_pendientes.iloc[st.session_state.idx_carousel]
            real_idx = df_pendientes.index[st.session_state.idx_carousel]

            # --- CARD UI ---
            st.markdown(f"### Pedido {st.session_state.idx_carousel + 1} de {total_p}")
            
            with st.container(border=True):
                st.image(item["Foto_URL"], use_container_width=True)
                st.subheader(item["Producto"])
                st.write(f"👤 **Cliente:** {item['Cliente']}")
                
                col_a, col_b = st.columns(2)
                col_a.metric("Costo MXN", f"${item['Costo_MXN']:,.2f}")
                col_b.metric("Saldo", f"${item['Saldo']:,.2f}", delta="-Abono", delta_color="inverse")
                
                st.divider()
                
                # BOTONES DE ACCIÓN RÁPIDA CON CONFIRMACIÓN
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if item["Entregado"] == "NO":
                        with st.popover("📦 Entregar", use_container_width=True):
                            st.write("¿Confirmas que ya entregaste el producto?")
                            if st.button("SÍ, CONFIRMAR", key=f"ent_{real_idx}"):
                                actualizar_estado(df_cv, real_idx, "Entregado", "SÍ")
                                st.rerun()
                    else:
                        st.button("✅ ENTREGADO", disabled=True, use_container_width=True)

                with col_btn2:
                    with st.popover("💰 Liquidar", use_container_width=True):
                        st.write("¿Confirmas que ya recibiste el pago total?")
                        if st.button("SÍ, LIQUIDADO", key=f"liq_{real_idx}"):
                            actualizar_estado(df_cv, real_idx, "Liquidado", "SÍ")
                            st.rerun()

            # NAVEGACIÓN INFERIOR (SWIPE SIMULADO)
            st.markdown("<br>", unsafe_allow_html=True)
            nav1, nav2 = st.columns(2)
            with nav1:
                if st.button("⬅️ Anterior", use_container_width=True) and st.session_state.idx_carousel > 0:
                    st.session_state.idx_carousel -= 1
                    st.rerun()
            with nav2:
                if st.button("Siguiente ➡️", use_container_width=True) and st.session_state.idx_carousel < total_p - 1:
                    st.session_state.idx_carousel += 1
                    st.rerun()

# ---------------------------------------------------------
# MODO LISTA / REGISTRO (VISTA NORMAL)
# ---------------------------------------------------------
else:
    # Formulario de registro (igual que el anterior)
    with st.expander("🚀 NUEVO REGISTRO RÁPIDO", expanded=False):
        with st.form("form_registro_express"):
            f_producto = st.text_input("Producto")
            f_cliente = st.text_input("Cliente")
            f_foto = st.file_uploader("📷 Foto", type=["jpg", "png", "jpeg"])
            c1, c2 = st.columns(2)
            with c1: f_usd = st.number_input("Costo USD", min_value=0.0)
            with c2: f_abono = st.number_input("Abono inicial (MXN)", min_value=0.0)
            
            if st.form_submit_button("✅ GUARDAR", use_container_width=True):
                if f_producto and f_usd > 0:
                    with st.spinner("Subiendo..."):
                        url_foto = subir_a_nube(f_foto) if f_foto else "https://via.placeholder.com/150"
                        f_usd_tax = f_usd * 1.0825
                        f_comi_mxn = (f_usd_tax * 0.12) * 19
                        costo_mxn = round((f_usd_tax * tc_actual) + f_comi_mxn, 2)
                        
                        nuevo_reg = {
                            "ID": len(df_cv) + 1,
                            "Fecha_Registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Producto": f_producto,
                            "Cliente": f_cliente if f_cliente else "N/A",
                            "Foto_URL": url_foto, "Costo_USD": f_usd, "Costo_MXN": costo_mxn,
                            "Abono": f_abono, "Saldo": costo_mxn - f_abono,
                            "Entregado": "NO", "Liquidado": "NO", "Fecha_Liquidacion": "Pendiente"
                        }
                        df_final = pd.concat([df_cv, pd.DataFrame([nuevo_reg])], ignore_index=True)
                        conn.update(worksheet="CompradoraV", data=df_final)
                        st.cache_data.clear()
                        st.success("¡Registrado!")
                        time.sleep(1)
                        st.rerun()

    # Tabla normal de abajo
    st.subheader("📋 Lista de Control")
    if not df_cv.empty:
        st.data_editor(
            df_cv.sort_index(ascending=False),
            column_config={
                "Foto_URL": st.column_config.ImageColumn("🖼️"),
                "Saldo": st.column_config.NumberColumn("Debe", format="$%.2f"),
                "Liquidado": st.column_config.SelectboxColumn("Liq.", options=["SÍ", "NO"]),
                "Entregado": st.column_config.SelectboxColumn("Entr.", options=["SÍ", "NO"]),
                "ID": None, "Costo_USD": None, "Fecha_Liquidacion": None
            },
            use_container_width=True, hide_index=True
        )