import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Lolis · Registrar", layout="wide", initial_sidebar_state="collapsed")

CLOUD_NAME = "doi81tooh"
API_KEY = "245491997239959"

TIPOS_ARTICULO = ["Tenis", "Ropa", "Accesorio", "Otro"]
TIENDAS = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
COLUMNAS_ONLINE = [
    "FECHA_REGISTRO", "PRODUCTO", "TIPO_ARTICULO", "CLIENTE", "FOTO_URL", "TIENDA",
    "USD_BRUTO", "USD_CON_8.25", "USD_FINAL_EQ", "TC_MERCADO", "COMISION_PAGADA_MXN",
    "COSTO_TOTAL_MXN", "VENTA_MXN", "GANANCIA_MXN", "RANGO_SEMANA", "ESTADO_PAGO",
    "MONTO_RECIBIDO", "COMI_CHECK", "FECHA"
]

st.markdown("""
<style>
#MainMenu, footer {visibility:hidden;}
header {visibility:hidden; height:0;}
.block-container {padding-top:1rem !important; padding-bottom:2rem !important; max-width:1100px;}
.topbar {position:sticky; top:0; z-index:999; background:rgba(255,255,255,.94); backdrop-filter:blur(12px); padding:8px 0 10px; margin-bottom:8px; border-bottom:1px solid #eee;}
[data-testid="stButton"] button {border-radius:14px !important; min-height:46px !important; font-weight:700 !important;}
.fast-card {border:1px solid #e8e8e8; border-radius:18px; padding:14px 16px; background:#fff; box-shadow:0 3px 16px rgba(0,0,0,.05);}
.small-help {color:#777;font-size:.86rem;}
@media (max-width: 700px) {
 .block-container {padding: .5rem .8rem 1.5rem !important;}
 h1 {font-size:1.65rem !important;}
 h2 {font-size:1.3rem !important;}
 .topbar {margin-left:-.8rem; margin-right:-.8rem; padding-left:.8rem; padding-right:.8rem;}
 [data-testid="stHorizontalBlock"] {gap:.35rem !important;}
 [data-testid="stFileUploaderDropzone"] {padding:.65rem !important;}
}
</style>
""", unsafe_allow_html=True)


def nav():
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    cols = st.columns(4)
    labels = ["➕ Registrar", "📋 Online", "👩‍💼 Compradoras", "💰 Cobranza"]
    pages = ["app.py", "pages/Registros_Online.py", "pages/Registros_Compradoras.py", "pages/Cobranza.py"]
    for c, label, page in zip(cols, labels, pages):
        with c:
            if st.button(label, use_container_width=True, key=f"nav_{label}"):
                st.switch_page(page)
    st.markdown('</div>', unsafe_allow_html=True)


def limpiar_num(val):
    try:
        if val in (None, ""):
            return 0.0
        return float(str(val).replace(",", "").replace("$", ""))
    except Exception:
        return 0.0


@st.cache_data(ttl=3600)
def obtener_tc():
    try:
        return round(requests.get("https://open.er-api.com/v6/latest/USD", timeout=8).json()["rates"]["MXN"], 2)
    except Exception:
        return 18.50


def subir_a_nube(archivo):
    try:
        url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
        data = {"upload_preset": "ml_default", "api_key": API_KEY, "quality": "auto", "fetch_format": "auto"}
        res = requests.post(url, data=data, files={"file": archivo.getvalue()}, timeout=30)
        return res.json().get("secure_url") if res.status_code == 200 else None
    except Exception:
        return None


conn = st.connection("gsheets", type=GSheetsConnection)


def lectura_online():
    try:
        df = conn.read(ttl=0)
        if df is None:
            return pd.DataFrame(columns=COLUMNAS_ONLINE)
        df.columns = [str(c).strip() for c in df.columns]
        for col in COLUMNAS_ONLINE:
            if col not in df.columns:
                defaults = {"TIPO_ARTICULO": "Otro", "CLIENTE": "N/A", "FOTO_URL": "", "ESTADO_PAGO": "🔴 Debe", "MONTO_RECIBIDO": 0.0, "COMI_CHECK": False}
                df[col] = defaults.get(col, "")
        return df
    except Exception:
        return pd.DataFrame(columns=COLUMNAS_ONLINE)


def normalizar_online(df):
    for col in COLUMNAS_ONLINE:
        if col not in df.columns:
            df[col] = ""
    numeric = ["USD_BRUTO", "USD_CON_8.25", "USD_FINAL_EQ", "TC_MERCADO", "COMISION_PAGADA_MXN", "COSTO_TOTAL_MXN", "VENTA_MXN", "GANANCIA_MXN", "MONTO_RECIBIDO"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["COMI_CHECK"] = df["COMI_CHECK"].fillna(False).astype(bool)
    df["TIPO_ARTICULO"] = df["TIPO_ARTICULO"].fillna("Otro").replace("", "Otro")
    return df[COLUMNAS_ONLINE]


nav()
tc_actual = obtener_tc()
df_nube = normalizar_online(lectura_online())
proximo_id = len(df_nube)

st.title("➕ Registrar venta")
st.caption("Registro rápido · compras online · optimizado para teléfono")

# Una sola pantalla, con pocos campos visibles y cálculo automático.
st.markdown('<div class="fast-card">', unsafe_allow_html=True)

c1, c2 = st.columns([1.5, 1])
with c1:
    nombre = st.text_input("PRODUCTO *", placeholder="Ej. Tenis New Balance 530")
with c2:
    tipo_articulo = st.selectbox("TIPO DE ARTÍCULO *", TIPOS_ARTICULO)

c1, c2 = st.columns([1, 1])
with c1:
    cliente = st.text_input("CLIENTE", placeholder="Opcional")
with c2:
    tienda_sel = st.selectbox("TIENDA", TIENDAS)

if tienda_sel == "CUSTOM":
    tienda_final = st.text_input("NOMBRE DE TIENDA", placeholder="Escribe la tienda")
else:
    tienda_final = tienda_sel

foto_archivo = st.file_uploader("📷 FOTO (opcional)", type=["jpg", "jpeg", "png"], accept_multiple_files=False)
if foto_archivo:
    st.image(foto_archivo, caption="Vista previa", width=220)

c1, c2, c3 = st.columns(3)
with c1:
    usd_bruto = limpiar_num(st.text_input("COSTO USD", placeholder="50"))
with c2:
    tc_mercado = limpiar_num(st.text_input("TIPO DE CAMBIO", value=str(tc_actual)))
with c3:
    venta_mxn = limpiar_num(st.text_input("VENTA FINAL MXN", placeholder="1500"))

porcentaje_comision = st.radio("COMISIÓN", [12, 15], index=0, horizontal=True)

usd_tax = usd_bruto * 1.0825
comi_mxn = (usd_tax * (porcentaje_comision / 100)) * 19
costo_tot_mxn = (usd_tax * tc_mercado) + comi_mxn
usd_final_eq = costo_tot_mxn / tc_mercado if tc_mercado > 0 else 0
ganancia_mxn = venta_mxn - costo_tot_mxn

m1, m2, m3 = st.columns(3)
m1.metric("Inversión", f"${costo_tot_mxn:,.2f}")
m2.metric("Venta", f"${venta_mxn:,.2f}")
m3.metric("Ganancia", f"${ganancia_mxn:,.2f}")

if st.button("✅ GUARDAR REGISTRO", use_container_width=True, type="primary"):
    if not nombre.strip():
        st.error("Escribe el nombre del producto.")
    elif usd_bruto <= 0:
        st.error("Ingresa el costo USD.")
    elif tc_mercado <= 0:
        st.error("Ingresa un tipo de cambio válido.")
    elif venta_mxn <= 0:
        st.error("Ingresa el precio de venta.")
    else:
        with st.spinner("Guardando..."):
            foto_url = ""
            if foto_archivo:
                foto_url = subir_a_nube(foto_archivo)
                if not foto_url:
                    st.error("No se pudo subir la foto a Cloudinary.")
                    st.stop()
            ahora = datetime.now()
            inicio_semana = ahora - timedelta(days=ahora.weekday())
            fin_semana = inicio_semana + timedelta(days=6)
            nuevo = {
                "FECHA_REGISTRO": ahora.strftime("%d/%m/%Y %H:%M"),
                "PRODUCTO": nombre.strip(),
                "TIPO_ARTICULO": tipo_articulo,
                "CLIENTE": cliente.strip() or "N/A",
                "FOTO_URL": foto_url,
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
            }
            df_fresco = normalizar_online(lectura_online())
            df_final = pd.concat([df_fresco, pd.DataFrame([nuevo])], ignore_index=True)
            conn.update(data=df_final[COLUMNAS_ONLINE])
            st.cache_data.clear()
            st.success("✅ Registro guardado")
            time.sleep(.5)
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div class='small-help'>💡 El tipo de artículo se guarda en <b>TIPO_ARTICULO</b> para que puedas distinguir Tenis, Ropa, Accesorios y Otros en Excel/Google Sheets.</div>", unsafe_allow_html=True)
