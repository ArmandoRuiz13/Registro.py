import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cobranza Flash", layout="centered")

# Inyectar CSS para compactar la vista en móvil
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    .stButton button { height: 3.5rem; border-radius: 12px; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    img { border-radius: 15px; object-fit: cover; max-height: 250px; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def leer_datos():
    try:
        st.cache_data.clear()
        # Intentamos leer la primera pestaña. Si tu pestaña tiene nombre, ponlo en worksheet="Nombre"
        df = conn.read(ttl=0) 
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error("⚠️ Error de conexión con Google Sheets. Revisa tus credenciales.")
        st.stop()

# --- CARGA Y FILTRADO ---
df_nube = leer_datos()
# Filtramos solo pendientes
pendientes = df_nube[df_nube["ESTADO_PAGO"].isin(["🔴 Debe", "🟡 Abonado"])].copy()

if pendientes.empty:
    st.balloons()
    st.success("¡Todo cobrado! 😎")
    if st.button("🏠 Volver"): st.switch_page("app.py")
    st.stop()

# Manejo de índice en sesión
if 'idx_c' not in st.session_state: st.session_state.idx_c = 0
if st.session_state.idx_c >= len(pendientes): st.session_state.idx_c = 0

reg = pendientes.iloc[st.session_state.idx_c]
idx_original = reg.name

# --- INTERFAZ SUPERIOR (ESTATUS) ---
# Mostramos el estatus de forma llamativa arriba
status_color = "orange" if reg['ESTADO_PAGO'] == "🟡 Abonado" else "red"
st.markdown(f"""
    <div style="text-align: center; padding: 10px; border-radius: 10px; background-color: {status_color}22; border: 2px solid {status_color};">
        <h3 style="margin:0; color: {status_color};">{reg['ESTADO_PAGO']}</h3>
    </div>
    """, unsafe_allow_html=True)

if reg['ESTADO_PAGO'] == "🟡 Abonado":
    st.write(f"💰 **Ya abonó:** ${reg['MONTO_RECIBIDO']:,.2f}")

# --- CUERPO (IMAGEN COMPACTA) ---
if reg.get("FOTO_URL") and str(reg["FOTO_URL"]) != "nan":
    st.image(reg["FOTO_URL"], use_container_width=True)
else:
    st.info("🖼️ Producto sin foto")

# --- DATOS RELEVANTES (UNA SOLA LÍNEA) ---
st.markdown(f"**{reg['PRODUCTO']}** | 👤 {reg['CLIENTE']}")
st.subheader(f"${reg['VENTA_MXN']:,.2f}")

# --- BOTONES DE ACCIÓN (DEBAJO DE LA INFO) ---
# Botón principal de cobro
if st.button("✅ MARCAR COMO PAGADO", type="primary", use_container_width=True):
    with st.spinner("Actualizando..."):
        df_nube.at[idx_original, "ESTADO_PAGO"] = "🟢 Pagado"
        df_nube.at[idx_original, "MONTO_RECIBIDO"] = reg["VENTA_MXN"]
        conn.update(data=df_nube)
        st.toast("¡Cobrado con éxito!")
        time.sleep(1)
        st.cache_data.clear()
        st.rerun()

# Navegación compacta
c1, c2, c3 = st.columns([1, 2, 1])
with c1:
    if st.button("⬅️"):
        st.session_state.idx_c = max(0, st.session_state.idx_c - 1)
        st.rerun()
with c2:
    st.write(f"Item {st.session_state.idx_c + 1} de {len(pendientes)}")
with c3:
    if st.button("➡️"):
        st.session_state.idx_c = min(len(pendientes)-1, st.session_state.idx_c + 1)
        st.rerun()

st.button("🏠 Menú Principal", on_click=lambda: st.switch_page("app.py"), use_container_width=True)