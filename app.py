import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="S&R Lolis | Registro", page_icon="🛍️", layout="wide", initial_sidebar_state="expanded")

# =========================================================
# CONFIGURACIÓN
# =========================================================
SHEET_VENTAS = "Sheet1"
SHEET_COMPRADORAS = "CompradoraV"

VENTAS_COLUMNS = [
    "FECHA_REGISTRO", "PRODUCTO", "TIENDA", "USD_BRUTO", "USD_CON_8.25",
    "USD_FINAL_EQ", "TC_MERCADO", "COMISION_PAGADA_MXN", "COSTO_TOTAL_MXN",
    "VENTA_MXN", "GANANCIA_MXN", "RANGO_SEMANA", "ESTADO_PAGO",
    "MONTO_RECIBIDO", "COMI_CHECK", "FECHA", "CLIENTE", "FOTO_URL"
]

COMPRADORA_COLUMNS = [
    "ID", "Fecha_Registro", "Producto", "Cliente", "Foto_URL", "Costo_USD",
    "Costo_MXN", "Abono", "Saldo", "Entregado", "Liquidado",
    "Fecha_Liquidacion", "Venta_Directa_MXN"
]

TIENDAS = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
TIPOS_ARTICULO = ["👕 Ropa", "👟 Tenis", "👜 Accesorio", "⚙️ Custom"]

# Cloudinary unsigned upload: no API secret is needed here.
# Configure CLOUDINARY_CLOUD_NAME and CLOUDINARY_UPLOAD_PRESET in Streamlit secrets/env.
CLOUD_NAME = st.secrets.get("CLOUDINARY_CLOUD_NAME", os.getenv("CLOUDINARY_CLOUD_NAME", "doi81tooh"))
UPLOAD_PRESET = st.secrets.get("CLOUDINARY_UPLOAD_PRESET", os.getenv("CLOUDINARY_UPLOAD_PRESET", "ml_default"))

# =========================================================
# ESTILO RESPONSIVO
# =========================================================
st.markdown("""
<style>
/* Oculta SOLO la navegación automática de Streamlit (app + pages).
   No afecta el menú personalizado que se construye más abajo. */
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {
    display: none !important;
}
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
.main-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 800; margin-bottom: .2rem; }
.subtle { color: #6b7280; margin-bottom: 1rem; }
.mode-card { border: 1px solid rgba(128,128,128,.22); border-radius: 18px; padding: 18px; margin-bottom: 12px; }
.success-card { border-radius: 16px; padding: 18px; background: rgba(46,125,50,.08); border: 1px solid rgba(46,125,50,.25); }
div.stButton > button { min-height: 48px; border-radius: 12px; font-weight: 700; }
[data-testid="stFileUploaderDropzone"] { border-radius: 14px; }
.calc-card { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:12px 0 16px; padding:14px; border:2px solid rgba(46,125,50,.35); border-radius:16px; background:rgba(46,125,50,.07); }
.calc-card div { text-align:center; }
.calc-card span { display:block; font-size:.72rem; font-weight:800; opacity:.72; letter-spacing:.03em; }
.calc-card strong { display:block; font-size:1.18rem; margin-top:3px; }
@media (max-width: 768px) {
    .block-container { padding: .65rem .65rem 1.2rem .65rem; max-width: 100%; }
    section[data-testid="stSidebar"] { width: min(88vw, 360px) !important; }
    .main-title { font-size: 1.55rem; line-height: 1.15; }
    div.stButton > button { min-height: 54px; font-size: 1rem; }
    div[data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: .35rem; }
    div[data-testid="stHorizontalBlock"] > div { min-width: 100% !important; }
    div[data-testid="stRadio"] { margin-bottom: .35rem; }
    div[data-testid="stRadio"] label { padding: 7px 0; }
    .stNumberInput input, .stTextInput input { font-size: 16px !important; }
    div[data-testid="stFileUploaderDropzone"] { padding: 10px; }
    .calc-card { grid-template-columns:1fr; gap:8px; padding:12px; }
    .calc-card div { display:flex; justify-content:space-between; align-items:center; text-align:left; gap:10px; }
    .calc-card span { font-size:.7rem; }
    .calc-card strong { font-size:1.08rem; }
}
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# =========================================================
# UTILIDADES
# =========================================================
def limpiar_num(value):
    try:
        if value is None or str(value).strip() == "":
            return 0.0
        return float(str(value).replace(",", "").replace("$", "").strip())
    except Exception:
        return 0.0

@st.cache_data(ttl=3600)
def obtener_tc():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
        res.raise_for_status()
        return round(float(res.json()["rates"]["MXN"]), 2)
    except Exception:
        return 18.50


def leer_hoja(worksheet, columns):
    try:
        df = conn.read(worksheet=worksheet, ttl=0)
        if df is None:
            return pd.DataFrame(columns=columns)
        df.columns = [str(c).strip() for c in df.columns]
        for col in columns:
            if col not in df.columns:
                if col in ["COMI_CHECK"]:
                    df[col] = False
                elif col in ["CLIENTE", "FOTO_URL", "Fecha_Liquidacion"]:
                    df[col] = ""
                else:
                    df[col] = 0
        return df[columns].copy()
    except Exception:
        return pd.DataFrame(columns=columns)


def subir_a_nube(archivo_imagen):
    if not archivo_imagen:
        return ""
    try:
        url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
        data = {"upload_preset": UPLOAD_PRESET, "quality": "auto", "fetch_format": "auto"}
        files = {"file": archivo_imagen.getvalue()}
        res = requests.post(url, data=data, files=files, timeout=30)
        if res.status_code == 200:
            return res.json().get("secure_url", "")
        try:
            msg = res.json().get("error", {}).get("message", "Error desconocido")
        except Exception:
            msg = res.text[:200]
        st.error(f"No se pudo subir la foto: {msg}")
        return ""
    except Exception as exc:
        st.error(f"Error al subir la foto: {exc}")
        return ""


def rango_semana_actual():
    hoy = datetime.now()
    inicio = hoy - timedelta(days=hoy.weekday())
    fin = inicio + timedelta(days=6)
    return f"{inicio.strftime('%d/%m/%y')} al {fin.strftime('%d/%m/%y')}"


def guardar_ventas(df):
    conn.update(worksheet=SHEET_VENTAS, data=df[VENTAS_COLUMNS])
    st.cache_data.clear()


def guardar_compradoras(df):
    conn.update(worksheet=SHEET_COMPRADORAS, data=df[COMPRADORA_COLUMNS])
    st.cache_data.clear()

# =========================================================
# ESTADO
# =========================================================
if "section" not in st.session_state:
    st.session_state.section = "registrar"
if "registro_ok" not in st.session_state:
    st.session_state.registro_ok = None

# =========================================================
# DATOS (carga diferida para que los controles del formulario respondan rápido)
# =========================================================
tc_actual = obtener_tc()

def cargar_ventas():
    df = leer_hoja(SHEET_VENTAS, VENTAS_COLUMNS)
    for col in ["USD_BRUTO", "USD_CON_8.25", "USD_FINAL_EQ", "TC_MERCADO", "COMISION_PAGADA_MXN", "COSTO_TOTAL_MXN", "VENTA_MXN", "GANANCIA_MXN", "MONTO_RECIBIDO"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["COMI_CHECK"] = df["COMI_CHECK"].fillna(False).astype(bool)
    return df

def cargar_compradoras():
    df = leer_hoja(SHEET_COMPRADORAS, COMPRADORA_COLUMNS)
    for col in ["ID", "Costo_USD", "Costo_MXN", "Abono", "Saldo", "Venta_Directa_MXN"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

# =========================================================
# SIDEBAR ESCRITORIO
# =========================================================
with st.sidebar:
    st.markdown("## 🛍️ S&R Lolis")
    st.caption("Registro rápido")
    if st.button("➕ Registrar", use_container_width=True, type="primary" if st.session_state.section == "registrar" else "secondary"):
        st.session_state.section = "registrar"
        st.rerun()
    if st.button("📋 Ver registros", use_container_width=True, type="primary" if st.session_state.section == "ventas" else "secondary"):
        st.session_state.section = "ventas"
        st.rerun()
    if st.button("📦 Compras vendedoras", use_container_width=True, type="primary" if st.session_state.section == "compradoras" else "secondary"):
        st.session_state.section = "compradoras"
        st.rerun()
    if st.button("💰 Cobranza", use_container_width=True):
        st.switch_page("pages/Cobranza_Movil.py")
    st.divider()
    st.caption(f"Tipo de cambio actual: ${tc_actual:.2f} MXN")

# =========================================================
# REGISTRO PRINCIPAL
# =========================================================
def registro_venta_online():
    st.markdown('<div class="main-title">🛍️ Registrar artículo</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle">Registra una venta en pocos pasos. Los cálculos existentes se hacen automáticamente.</div>', unsafe_allow_html=True)

    if st.session_state.registro_ok:
        st.markdown(f'<div class="success-card">{st.session_state.registro_ok}</div>', unsafe_allow_html=True)
        st.session_state.registro_ok = None
        st.write("")

    st.markdown("### 1. ¿Qué quieres registrar?")
    modalidad = st.radio("Modalidad", ["🛒 Venta Online", "📦 Compra Vendedora"], horizontal=True, label_visibility="collapsed")

    if modalidad == "📦 Compra Vendedora":
        registro_compradora_rapido()
        return

    st.markdown("### 2. Tipo de artículo")
    tipo = st.radio("Tipo", TIPOS_ARTICULO, horizontal=True, label_visibility="collapsed")

    st.markdown("### 3. Datos mínimos")
    nombre = st.text_input("PRODUCTO", placeholder="Ej. Tenis New Balance 550", key="venta_producto")

    foto = st.file_uploader("📷 FOTO (opcional)", type=["jpg", "jpeg", "png"], key="venta_foto")
    if foto:
        st.image(foto, caption="Vista previa", width=180)

    cliente = st.text_input("CLIENTE (opcional)", placeholder="Nombre del cliente", key="venta_cliente")

    c1, c2 = st.columns(2)
    with c1:
        tienda_sel = st.selectbox("TIENDA", TIENDAS, index=0, key="venta_tienda")
    with c2:
        porcentaje_comision = st.radio("COMISIÓN", [12, 15], index=0, horizontal=True, key="venta_comision")

    tienda_final = tienda_sel
    if tienda_sel == "CUSTOM":
        tienda_final = st.text_input("Nombre de la tienda", placeholder="Escribe la tienda")

    c3, c4 = st.columns(2)
    with c3:
        usd_bruto = st.number_input("COSTO USD", min_value=0.0, value=None, placeholder="0.00", step=0.01, format="%.2f", key="venta_usd") or 0.0
    with c4:
        tc_mercado = st.number_input("TIPO DE CAMBIO", min_value=0.0, value=float(tc_actual), step=0.01, format="%.2f", key="venta_tc")

    venta_mxn = st.number_input("VENTA FINAL (MXN)", min_value=0.0, value=None, placeholder="0.00", step=10.0, format="%.2f", key="venta_final") or 0.0

    # Mismos cálculos de la aplicación original.
    usd_tax = usd_bruto * 1.0825
    comi_mxn = (usd_tax * (porcentaje_comision / 100)) * 19
    costo_tot_mxn = (usd_tax * tc_mercado) + comi_mxn
    ganancia_mxn = venta_mxn - costo_tot_mxn
    usd_final_eq = costo_tot_mxn / tc_mercado if tc_mercado > 0 else 0

    if usd_bruto > 0:
        st.markdown(
            f'<div class="calc-card"><div><span>COSTO CALCULADO</span><strong>${costo_tot_mxn:,.2f} MXN</strong></div><div><span>GANANCIA</span><strong>${ganancia_mxn:,.2f}</strong></div><div><span>TIPO DE CAMBIO</span><strong>${tc_mercado:.2f}</strong></div></div>',
            unsafe_allow_html=True,
        )

    guardar = st.button("✅ GUARDAR VENTA", use_container_width=True, type="primary")

    if guardar:
        errores = []
        if not nombre.strip(): errores.append("Escribe el producto.")
        if usd_bruto <= 0: errores.append("Ingresa el costo USD.")
        if venta_mxn <= 0: errores.append("Ingresa la venta final.")
        if tienda_sel == "CUSTOM" and not tienda_final.strip(): errores.append("Escribe la tienda.")

        if errores:
            for e in errores:
                st.error(e)
            return

        with st.spinner("Guardando..."):
            url_foto = subir_a_nube(foto) if foto else ""
            if foto and not url_foto:
                return

            df_fresco = leer_hoja(SHEET_VENTAS, VENTAS_COLUMNS)
            nuevo = {
                "FECHA_REGISTRO": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "PRODUCTO": nombre.strip(),
                "TIENDA": tienda_final,
                "USD_BRUTO": usd_bruto,
                "USD_CON_8.25": usd_tax,
                "USD_FINAL_EQ": usd_final_eq,
                "TC_MERCADO": tc_mercado,
                "COMISION_PAGADA_MXN": comi_mxn,
                "COSTO_TOTAL_MXN": costo_tot_mxn,
                "VENTA_MXN": venta_mxn,
                "GANANCIA_MXN": ganancia_mxn,
                "RANGO_SEMANA": rango_semana_actual(),
                "ESTADO_PAGO": "🔴 Debe",
                "MONTO_RECIBIDO": 0.0,
                "COMI_CHECK": False,
                "FECHA": datetime.now().strftime("%d/%m/%Y"),
                "CLIENTE": cliente.strip() if cliente.strip() else "N/A",
                "FOTO_URL": url_foto,
            }
            df_final = pd.concat([df_fresco, pd.DataFrame([nuevo])], ignore_index=True)
            guardar_ventas(df_final)
            st.session_state.registro_ok = f"<b>✅ Artículo registrado</b><br>{nombre.strip()} · ${venta_mxn:,.2f} MXN"
            time.sleep(.5)
            st.rerun()


def registro_compradora_rapido():
    st.markdown("### 📦 Compra vendedora")
    st.caption("Los datos se guardan exclusivamente en la hoja CompradoraV; no se mezclan con Ventas Online.")

    producto = st.text_input("PRODUCTO", placeholder="Ej. Tenis MK Cafés", key="cv_producto")
    cliente = st.text_input("COMPRADORA", placeholder="Nombre de la compradora", key="cv_cliente")
    foto = st.file_uploader("📷 FOTO (opcional)", type=["jpg", "jpeg", "png"], key="cv_foto")

    c1, c2 = st.columns(2)
    with c1:
        usd = st.number_input("COSTO USD", min_value=0.0, value=None, placeholder="0.00", step=0.01, format="%.2f", key="cv_usd") or 0.0
    with c2:
        directo = st.number_input("VENTA DIRECTA MXN", min_value=0.0, value=None, placeholder="0.00", step=10.0, format="%.2f", key="cv_directo") or 0.0
    abono = st.number_input("ABONO MXN", min_value=0.0, value=None, placeholder="0.00", step=10.0, format="%.2f", key="cv_abono") or 0.0

    costo_final = directo if directo > 0 else round(((usd * 1.0825) * tc_actual) + (((usd * 1.0825) * 0.12) * 19), 2)
    if costo_final > 0:
        st.info(f"Total: **${costo_final:,.2f} MXN** · Saldo: **${max(costo_final - abono, 0):,.2f}**")

    if st.button("✅ GUARDAR COMPRA VENDEDORA", use_container_width=True, type="primary"):
        if not producto.strip() or not cliente.strip() or costo_final <= 0:
            st.error("Producto, compradora y un costo (USD o Venta Directa MXN) son necesarios.")
            return
        if abono > costo_final:
            st.error("El abono no puede ser mayor al total.")
            return
        with st.spinner("Guardando..."):
            url_foto = subir_a_nube(foto) if foto else ""
            if foto and not url_foto:
                return
            df_fresco = leer_hoja(SHEET_COMPRADORAS, COMPRADORA_COLUMNS)
            ids = pd.to_numeric(df_fresco["ID"], errors="coerce") if not df_fresco.empty else pd.Series(dtype=float)
            next_id = int(ids.max()) + 1 if not ids.dropna().empty else 1
            nuevo = {
                "ID": next_id,
                "Fecha_Registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Producto": producto.strip(),
                "Cliente": cliente.strip(),
                "Foto_URL": url_foto,
                "Costo_USD": usd,
                "Costo_MXN": costo_final,
                "Abono": abono,
                "Saldo": costo_final - abono,
                "Entregado": "NO",
                "Liquidado": "NO",
                "Fecha_Liquidacion": "Pendiente",
                "Venta_Directa_MXN": directo,
            }
            guardar_compradoras(pd.concat([df_fresco, pd.DataFrame([nuevo])], ignore_index=True))
            st.session_state.registro_ok = f"<b>✅ Compra vendedora registrada</b><br>{producto.strip()} · {cliente.strip()}"
            time.sleep(.5)
            st.rerun()

# =========================================================
# VENTAS / HISTORIAL
# =========================================================
def vista_ventas():
    df_ventas = cargar_ventas()
    st.markdown('<div class="main-title">📋 Ver registros</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle">Historial de Venta Online. Los datos históricos permanecen en Sheet1.</div>', unsafe_allow_html=True)
    if df_ventas.empty:
        st.info("Todavía no hay ventas registradas.")
        return

    busqueda = st.text_input("🔎 Buscar", placeholder="Producto, cliente o tienda")
    estado = st.multiselect("Estado de pago", ["🔴 Debe", "🟡 Abonado", "🟢 Pagado"], default=[])
    vista = df_ventas.copy()
    if busqueda.strip():
        q = busqueda.strip().lower()
        mask = vista.astype(str).apply(lambda col: col.str.lower().str.contains(q, na=False)).any(axis=1)
        vista = vista[mask]
    if estado:
        vista = vista[vista["ESTADO_PAGO"].isin(estado)]

    vista = vista.sort_index(ascending=False)
    edited = st.data_editor(
        vista,
        column_config={
            "FOTO_URL": st.column_config.ImageColumn("🖼️ FOTO"),
            "CLIENTE": st.column_config.TextColumn("👤 CLIENTE"),
            "ESTADO_PAGO": st.column_config.SelectboxColumn("ESTADO", options=["🔴 Debe", "🟡 Abonado", "🟢 Pagado"]),
            "MONTO_RECIBIDO": st.column_config.NumberColumn("RECIBIDO", format="$%.2f"),
            "COMI_CHECK": st.column_config.CheckboxColumn("COMI. PAGADA"),
            "VENTA_MXN": st.column_config.NumberColumn("VENTA", format="$%.2f"),
            "GANANCIA_MXN": st.column_config.NumberColumn("GANANCIA", format="$%.2f"),
        },
        disabled=[c for c in VENTAS_COLUMNS if c not in ["ESTADO_PAGO", "MONTO_RECIBIDO", "COMI_CHECK", "CLIENTE"]],
        use_container_width=True,
        hide_index=True,
        key="ventas_editor",
    )

    if st.button("💾 GUARDAR CAMBIOS", use_container_width=True):
        for idx in edited.index:
            if edited.at[idx, "ESTADO_PAGO"] == "🟢 Pagado":
                edited.at[idx, "MONTO_RECIBIDO"] = edited.at[idx, "VENTA_MXN"]
        # Reemplaza solo el contenido visible si hay filtro; para evitar pérdida, mezclamos por índice.
        full = df_ventas.copy()
        for idx in edited.index:
            full.loc[idx, VENTAS_COLUMNS] = edited.loc[idx, VENTAS_COLUMNS]
        guardar_ventas(full.sort_index())
        st.success("Cambios guardados.")
        st.rerun()

    st.divider()
    st.subheader("💰 Reporte semanal")
    semanas = [s for s in vista["RANGO_SEMANA"].dropna().unique().tolist() if str(s).strip()]
    if semanas:
        semana = st.selectbox("Semana", semanas)
        d = df_ventas[df_ventas["RANGO_SEMANA"] == semana]
        a, b, c = st.columns(3)
        a.metric("Venta total", f"${d['VENTA_MXN'].sum():,.2f}")
        b.metric("Comisiones", f"${d['COMISION_PAGADA_MXN'].sum():,.2f}")
        c.metric("Ganancia", f"${d['GANANCIA_MXN'].sum():,.2f}")

# =========================================================
# COMPRADORAS / GESTIÓN
# =========================================================
def vista_compradoras():
    df_compradoras = cargar_compradoras()
    st.markdown('<div class="main-title">📦 Compras vendedoras</div>', unsafe_allow_html=True)
    st.caption("Fuente de datos independiente: CompradoraV")
    if df_compradoras.empty:
        st.info("No hay compras vendedoras registradas.")
        return

    edited = st.data_editor(
        df_compradoras.sort_index(ascending=False),
        column_config={
            "ID": st.column_config.NumberColumn("ID", disabled=True),
            "Foto_URL": st.column_config.ImageColumn("🖼️ FOTO"),
            "Costo_MXN": st.column_config.NumberColumn("TOTAL", format="$%.2f"),
            "Venta_Directa_MXN": st.column_config.NumberColumn("VENTA MXN", format="$%.2f"),
            "Abono": st.column_config.NumberColumn("ABONO", format="$%.2f"),
            "Saldo": st.column_config.NumberColumn("SALDO", format="$%.2f", disabled=True),
            "Liquidado": st.column_config.SelectboxColumn("LIQ.", options=["SÍ", "NO"]),
            "Entregado": st.column_config.SelectboxColumn("ENTR.", options=["SÍ", "NO"]),
            "Fecha_Registro": None,
            "Fecha_Liquidacion": None,
        },
        use_container_width=True,
        hide_index=True,
        key="compradoras_editor",
    )
    if st.button("💾 GUARDAR CAMBIOS DE COMPRADORAS", use_container_width=True):
        for i in edited.index:
            if edited.at[i, "Liquidado"] == "SÍ":
                edited.at[i, "Saldo"] = 0.0
                edited.at[i, "Entregado"] = "SÍ"
                edited.at[i, "Fecha_Liquidacion"] = datetime.now().strftime("%d/%m/%Y")
            else:
                edited.at[i, "Saldo"] = max(float(edited.at[i, "Costo_MXN"]) - float(edited.at[i, "Abono"]), 0.0)
        guardar_compradoras(edited.sort_index())
        st.success("Compradoras actualizadas.")
        st.rerun()

# =========================================================
# PANTALLA
# =========================================================
if st.session_state.section == "registrar":
    registro_venta_online()
elif st.session_state.section == "ventas":
    vista_ventas()
else:
    vista_compradoras()
