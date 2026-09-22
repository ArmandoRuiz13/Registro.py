import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestor Pro v25 - Cloudinary", layout="wide", initial_sidebar_state="expanded")

CLOUD_NAME = "doi81tooh"
API_KEY = "245491997239959"
TIPOS_ARTICULO = ["Tenis", "Ropa", "Accesorio", "Otro"]
TIENDAS = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]

st.markdown("""
<style>
header {visibility:hidden;}
footer {visibility:hidden;}
[data-testid="stSidebar"] {min-width: 300px; max-width: 360px;}
[data-testid="stSidebarContent"] {padding: 1rem .85rem 1.5rem .85rem;}
[data-testid="stSidebar"] button {min-height: 44px; border-radius: 12px !important; font-weight: 700 !important;}
@media (max-width: 700px) {
  [data-testid="stSidebar"] {min-width: 86vw; max-width: 88vw;}
  [data-testid="stSidebarContent"] {padding: .8rem .7rem 1rem .7rem;}
  .block-container {padding: .8rem .8rem 1.5rem !important;}
  h1 {font-size: 1.55rem !important;}
  h2 {font-size: 1.25rem !important;}
  [data-testid="stFileUploaderDropzone"] {padding: .65rem !important;}
}
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)


def limpiar_num(val):
    if not val:
        return 0.0
    try:
        return float(str(val).replace(',', '').replace('$', ''))
    except Exception:
        return 0.0


@st.cache_data(ttl=3600)
def obtener_tc():
    try:
        return round(requests.get("https://open.er-api.com/v6/latest/USD", timeout=8).json()["rates"]["MXN"], 2)
    except Exception:
        return 18.50


def subir_a_nube(archivo_imagen):
    try:
        url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
        data = {"upload_preset": "ml_default", "api_key": API_KEY, "quality": "auto", "fetch_format": "auto"}
        res = requests.post(url, data=data, files={"file": archivo_imagen.getvalue()}, timeout=30)
        return res.json().get("secure_url") if res.status_code == 200 else None
    except Exception:
        return None


def lectura_segura(worksheet=None):
    for _ in range(3):
        try:
            df = conn.read(worksheet=worksheet, ttl=0) if worksheet else conn.read(ttl=0)
            if df is not None:
                df.columns = [str(c).strip() for c in df.columns]
                return df
        except Exception:
            time.sleep(.5)
    return pd.DataFrame()


def nav_sidebar():
    with st.sidebar:
        st.markdown("# 🛍️ Lolis")
        st.caption("Menú")
        if st.button("📝 Registro", use_container_width=True):
            st.switch_page("app.py")
        if st.button("📋 Registros Online", use_container_width=True):
            st.switch_page("pages/Registros_Online.py")
        if st.button("👩‍💼 Registros Compradoras", use_container_width=True):
            st.switch_page("pages/Registros_Compradoras.py")
        if st.button("💰 Cobranza", use_container_width=True):
            st.switch_page("pages/Cobranza_Movil.py")
        st.divider()


def guardar_online(nombre, cliente, foto_archivo, tienda_final, tipo_articulo, usd_bruto, tc_mercado, venta_mxn, porcentaje_comision):
    url_final_foto = ""
    if foto_archivo:
        url_final_foto = subir_a_nube(foto_archivo)
        if not url_final_foto:
            st.error("❌ Falló la subida a Cloudinary. Verifica el Upload Preset.")
            return False

    ahora = datetime.now()
    inicio_semana = ahora - timedelta(days=ahora.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    usd_tax = usd_bruto * 1.0825
    comi_mxn = (usd_tax * (porcentaje_comision / 100)) * 19
    costo_tot_mxn = (usd_tax * tc_mercado) + comi_mxn
    usd_final_eq = costo_tot_mxn / tc_mercado if tc_mercado > 0 else 0
    ganancia_mxn = venta_mxn - costo_tot_mxn

    df_fresco = lectura_segura()
    nuevo = {
        "FECHA_REGISTRO": ahora.strftime("%d/%m/%Y %H:%M"),
        "TIPO_ARTICULO": tipo_articulo,
        "PRODUCTO": nombre,
        "TIENDA": tienda_final,
        "USD_BRUTO": usd_bruto,
        "USD_CON_8.25": usd_tax,
        "USD_FINAL_EQ": usd_final_eq,
        "TC_MERCADO": tc_mercado,
        "COMISION_PAGADA_MXN": comi_mxn,
        "COSTO_TOTAL_MXN": costo_tot_mxn,
        "VENTA_MXN": venta_mxn,
        "GANANCIA_MXN": ganancia_mxn,
        "RANGO_SEMANA": f"{inicio_semana.strftime('%d/%m/%y')} al {fin_semana.strftime('%d/%m/%y')}",
        "ESTADO_PAGO": "🔴 Debe",
        "MONTO_RECIBIDO": 0.0,
        "COMI_CHECK": False,
        "FECHA": ahora.strftime("%d/%m/%Y"),
        "CLIENTE": cliente if cliente else "N/A",
        "FOTO_URL": url_final_foto,
    }
    columnas = ["FECHA_REGISTRO", "TIPO_ARTICULO", "PRODUCTO", "TIENDA", "USD_BRUTO", "USD_CON_8.25", "USD_FINAL_EQ", "TC_MERCADO", "COMISION_PAGADA_MXN", "COSTO_TOTAL_MXN", "VENTA_MXN", "GANANCIA_MXN", "RANGO_SEMANA", "ESTADO_PAGO", "MONTO_RECIBIDO", "COMI_CHECK", "FECHA", "CLIENTE", "FOTO_URL"]
    nuevo_df = pd.DataFrame([nuevo])
    if df_fresco.empty:
        df_final = nuevo_df[columnas]
    else:
        for col in columnas:
            if col not in df_fresco.columns:
                df_fresco[col] = ""
        df_final = pd.concat([df_fresco, nuevo_df[columnas]], ignore_index=True)[columnas]
    conn.update(data=df_final)
    return True


def guardar_compradora(prod, cliente, foto, usd, venta_mxn, abono, tipo_articulo):
    df = lectura_segura("CompradoraV")
    if df.empty:
        df = pd.DataFrame(columns=["ID", "Fecha_Registro", "TIPO_ARTICULO", "Producto", "Cliente", "Foto_URL", "Costo_USD", "Costo_MXN", "Abono", "Saldo", "Entregado", "Liquidado", "Fecha_Liquidacion", "Venta_Directa_MXN"])
    if "ID" not in df.columns:
        df["ID"] = range(1, len(df) + 1)
    for c, default in [("Foto_URL", ""), ("Venta_Directa_MXN", 0.0), ("TIPO_ARTICULO", "Otro")]:
        if c not in df.columns:
            df[c] = default
    if foto:
        foto_url = subir_a_nube(foto)
        if not foto_url:
            st.error("❌ No se pudo subir la foto.")
            return False
    else:
        foto_url = ""
    if usd > 0:
        tc = obtener_tc()
        costo_final = round(((usd * 1.0825) * tc) + (((usd * 1.0825) * 0.12) * 19), 2)
    else:
        costo_final = venta_mxn
    now = datetime.now()
    nuevo = {
        "ID": int(pd.to_numeric(df["ID"], errors="coerce").fillna(0).max()) + 1,
        "Fecha_Registro": now.strftime("%d/%m/%Y %H:%M"),
        "TIPO_ARTICULO": tipo_articulo,
        "Producto": prod,
        "Cliente": cliente or "N/A",
        "Foto_URL": foto_url,
        "Costo_USD": usd,
        "Costo_MXN": costo_final,
        "Abono": abono,
        "Saldo": max(costo_final - abono, 0),
        "Entregado": "NO",
        "Liquidado": "SÍ" if abono >= costo_final else "NO",
        "Fecha_Liquidacion": now.strftime("%d/%m/%Y") if abono >= costo_final else "Pendiente",
        "Venta_Directa_MXN": venta_mxn,
    }
    cols = ["ID", "Fecha_Registro", "TIPO_ARTICULO", "Producto", "Cliente", "Foto_URL", "Costo_USD", "Costo_MXN", "Abono", "Saldo", "Entregado", "Liquidado", "Fecha_Liquidacion", "Venta_Directa_MXN"]
    df_final = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
    for c in cols:
        if c not in df_final.columns:
            df_final[c] = ""
    conn.update(worksheet="CompradoraV", data=df_final[cols])
    return True


nav_sidebar()
tc_actual = obtener_tc()
df_nube = lectura_segura()
proximo_id = len(df_nube)

hoy = datetime.now()
inicio_semana = hoy - timedelta(days=hoy.weekday())
fin_semana = inicio_semana + timedelta(days=6)
rango_actual = f"{inicio_semana.strftime('%d/%m/%y')} al {fin_semana.strftime('%d/%m/%y')}"

st.title("🚀 Control de Ventas")
st.caption("Registro rápido: elige si es una compra online o una compra para una compradora.")

with st.sidebar:
    st.header(f"📝 Registro (ID: {proximo_id})")
    tipo_registro = st.radio("TIPO DE REGISTRO", ["🛒 Compra Online", "👩‍💼 Compra Compradora"], index=0)

    if tipo_registro == "🛒 Compra Online":
        nombre = st.text_input("PRODUCTO", placeholder="Nombre del producto")
        tipo_articulo = st.selectbox("TIPO DE ARTÍCULO", TIPOS_ARTICULO, index=0)
        cliente = st.text_input("CLIENTE (Opcional)", placeholder="¿A quién se le vendió?")
        foto_archivo = st.file_uploader("📷 SUBIR FOTO", type=["jpg", "png", "jpeg"])
        if foto_archivo:
            st.image(foto_archivo, caption="Vista previa", use_container_width=True)
        tienda_sel = st.selectbox("TIENDA", TIENDAS)
        tienda_final = st.text_input("Tienda custom:") if tienda_sel == "CUSTOM" else tienda_sel
        usd_bruto_txt = st.text_input("COSTO USD", placeholder="Ej: 50.00")
        tc_mercado_txt = st.text_input("TIPO DE CAMBIO", value=str(tc_actual))
        venta_mxn_txt = st.text_input("VENTA FINAL (MXN)", placeholder="Ej: 1500.00")
        porcentaje_comision = st.radio("COMISIÓN", [12, 15], index=0, horizontal=True)
        usd_bruto = limpiar_num(usd_bruto_txt)
        tc_mercado = limpiar_num(tc_mercado_txt)
        venta_mxn = limpiar_num(venta_mxn_txt)
        usd_tax = usd_bruto * 1.0825
        comi_mxn = (usd_tax * (porcentaje_comision / 100)) * 19
        costo_tot_mxn = (usd_tax * tc_mercado) + comi_mxn
        ganancia_mxn = venta_mxn - costo_tot_mxn
        usd_final_eq = costo_tot_mxn / tc_mercado if tc_mercado > 0 else 0
        if st.button("CALCULAR 🔍", use_container_width=True):
            st.info(f"Comisión ({porcentaje_comision:.0f}%): ${comi_mxn:,.2f}\n\nInversión: ${costo_tot_mxn:,.2f}\n\nGanancia: ${ganancia_mxn:,.2f}")
        btn_guardar_online = st.button("GUARDAR EN NUBE ✅", use_container_width=True, type="primary")
        btn_guardar_compradora = False
    else:
        prod = st.text_input("PRODUCTO", placeholder="Nombre del producto")
        cliente_c = st.text_input("COMPRADORA", placeholder="Nombre")
        tipo_articulo_c = st.selectbox("TIPO DE ARTÍCULO", TIPOS_ARTICULO, index=0)
        foto_c = st.file_uploader("📷 FOTO", type=["jpg", "png", "jpeg"])
        st.info(f"💡 TC Actual: ${tc_actual}")
        c1, c2 = st.columns(2)
        with c1:
            usd_c = limpiar_num(st.text_input("Costo USD (Opcional)", placeholder="0.00"))
        with c2:
            venta_c = limpiar_num(st.text_input("Venta Directa MXN", placeholder="0.00"))
        abono_c = limpiar_num(st.text_input("Abono MXN", placeholder="0.00"))
        btn_guardar_compradora = st.button("GUARDAR REGISTRO ✅", use_container_width=True, type="primary")
        btn_guardar_online = False

    st.divider()
    st.caption("La sección de registros solo consulta/edita; el alta se hace desde Registro.")

if btn_guardar_online:
    if not nombre:
        st.error("Ingresa el nombre del producto.")
    elif usd_bruto <= 0 or tc_mercado <= 0 or venta_mxn <= 0:
        st.error("Ingresa costo USD, tipo de cambio y precio de venta válidos.")
    else:
        with st.spinner("Subiendo a Cloudinary y sincronizando Sheets..."):
            if guardar_online(nombre, cliente, foto_archivo, tienda_final, tipo_articulo, usd_bruto, tc_mercado, venta_mxn, porcentaje_comision):
                st.cache_data.clear()
                st.success("✅ ¡Guardado y sincronizado exitosamente!")
                time.sleep(1)
                st.rerun()

if btn_guardar_compradora:
    if not prod or (usd_c <= 0 and venta_c <= 0):
        st.error("Ingresa el producto y al menos un costo (USD o MXN).")
    elif abono_c > (venta_c if venta_c > 0 else ((usd_c * 1.0825) * tc_actual) + (((usd_c * 1.0825) * 0.12) * 19)):
        st.error("El abono no puede ser mayor al total.")
    else:
        with st.spinner("Subiendo y sincronizando..."):
            if guardar_compradora(prod, cliente_c, foto_c, usd_c, venta_c, abono_c, tipo_articulo_c):
                st.cache_data.clear()
                st.success("✅ ¡Registro de compradora guardado!")
                time.sleep(1)
                st.rerun()

st.subheader("📋 Historial y Cobranza")
if not df_nube.empty:
    df_para_editar = df_nube.copy().sort_index(ascending=False)
    if "TIPO_ARTICULO" not in df_para_editar.columns:
        df_para_editar["TIPO_ARTICULO"] = "Otro"
    for col in ["CLIENTE", "FOTO_URL"]:
        if col not in df_para_editar.columns:
            df_para_editar[col] = "N/A"
    if "COMI_CHECK" not in df_para_editar.columns:
        df_para_editar["COMI_CHECK"] = False
    else:
        df_para_editar["COMI_CHECK"] = df_para_editar["COMI_CHECK"].fillna(False).astype(bool)
    edited_df = st.data_editor(
        df_para_editar,
        column_config={
            "TIPO_ARTICULO": st.column_config.SelectboxColumn("TIPO", options=TIPOS_ARTICULO),
            "FOTO_URL": st.column_config.ImageColumn("🖼️ FOTO"),
            "CLIENTE": st.column_config.TextColumn("👤 CLIENTE"),
            "ESTADO_PAGO": st.column_config.SelectboxColumn("ESTADO", options=["🔴 Debe", "🟡 Abonado", "🟢 Pagado"]),
            "MONTO_RECIBIDO": st.column_config.NumberColumn("RECIBIDO", format="$%.2f"),
            "COMI_CHECK": st.column_config.CheckboxColumn("COMI. PAGADA")
        },
        disabled=[c for c in df_para_editar.columns if c not in ["ESTADO_PAGO", "MONTO_RECIBIDO", "COMI_CHECK", "CLIENTE", "TIPO_ARTICULO"]],
        use_container_width=True, key="ed_v25_cloud"
    )
    if st.button("💾 GUARDAR CAMBIOS DE TABLA"):
        for idx in edited_df.index:
            if edited_df.at[idx, "ESTADO_PAGO"] == "🟢 Pagado":
                edited_df.at[idx, "MONTO_RECIBIDO"] = edited_df.at[idx, "VENTA_MXN"]
        conn.update(data=edited_df.sort_index())
        time.sleep(1)
        st.success("¡Base de datos actualizada!")
        st.cache_data.clear()
        st.rerun()

st.divider()
st.subheader("💰 Reporte Semanal")
if not df_nube.empty and "RANGO_SEMANA" in df_nube.columns:
    semanas = df_nube["RANGO_SEMANA"].dropna().unique().tolist()
    if semanas:
        c_sel, c_b1, c_b2 = st.columns([2, 1, 1])
        with c_sel:
            sem_sel = st.selectbox("Semana:", semanas, label_visibility="collapsed")
        with c_b1:
            btn_sel = st.button("Consultar Selección", use_container_width=True)
        with c_b2:
            btn_act = st.button("SEMANA ACTUAL", type="primary", use_container_width=True)

        def stats(df_f, tit):
            st.markdown(f"#### {tit}")
            m1, m2, m3 = st.columns(3)
            m1.metric("Venta Total", f"${pd.to_numeric(df_f['VENTA_MXN'], errors='coerce').sum():,.2f}")
            m2.metric("Comisiones", f"${pd.to_numeric(df_f['COMISION_PAGADA_MXN'], errors='coerce').sum():,.2f}")
            m3.metric("Ganancia", f"${pd.to_numeric(df_f['GANANCIA_MXN'], errors='coerce').sum():,.2f}")
        if btn_sel:
            stats(df_nube[df_nube["RANGO_SEMANA"] == sem_sel], sem_sel)
        if btn_act:
            stats(df_nube[df_nube["RANGO_SEMANA"] == rango_actual], "Semana Actual")
