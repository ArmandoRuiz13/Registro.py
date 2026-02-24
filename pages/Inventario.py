import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inventario Pro v2 - Pagos Granulares", layout="wide")

# 🔑 CONFIGURACIÓN DE CLOUDINARY
CLOUD_NAME = "doi81tooh"
API_KEY = "245491997239959"
API_SECRET = "8Hgvfh6amI8vd0W_rG43HnSb2OI"

# --- FUNCIONES DE APOYO ---
@st.cache_data(ttl=3600)
def obtener_tc():
    try: 
        res = requests.get("https://open.er-api.com/v6/latest/USD").json()
        return round(res["rates"]["MXN"], 2)
    except: return 18.50

def calcular_costo_final_mxn(usd_bruto, tc_mercado):
    usd_tax = usd_bruto * 1.0825
    comi_mxn = (usd_tax * 0.12) * 19
    costo_tot_mxn = (usd_tax * tc_mercado) + comi_mxn
    return round(costo_tot_mxn, 2)

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

def lectura_inventario():
    # CAMBIO: "Pagado Venta" ahora se llama "Pagados" (numérico)
    columnas_base = ["Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos", "Pagados", "Imagen"]
    try: 
        df = conn.read(worksheet="Inventario", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_base)
        
        df.columns = [str(c).strip() for c in df.columns]
        for col in columnas_base:
            if col not in df.columns:
                df[col] = 0 if col in ["Precio MXN", "Precio Venta", "Cantidad", "Vendidos", "Pagados"] else ""
        
        # Aseguramos que Pagados sea numérico
        df["Pagados"] = pd.to_numeric(df["Pagados"], errors='coerce').fillna(0).astype(int)
        return df[columnas_base]
    except:
        return pd.DataFrame(columns=columnas_base)

# --- INICIO DE LÓGICA ---
tc_actual = obtener_tc()
df_inv = lectura_inventario()

for col in ["Precio MXN", "Precio Venta", "Cantidad", "Vendidos", "Pagados"]:
    df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# --- NAVEGACIÓN ---
if st.sidebar.button("⬅️ VOLVER A VENTAS", use_container_width=True):
    st.switch_page("app.py") 
st.sidebar.divider()

# --- SIDEBAR: REGISTRO ---
with st.sidebar:
    st.header(f"🆕 Registro (ID: {len(df_inv)})")
    st.info(f"Tipo de Cambio: **${tc_actual}**")
    
    f_nombre = st.text_input("Nombre del Producto")
    tiendas_opc = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
    f_tienda_sel = st.selectbox("Tienda", tiendas_opc)
    f_tienda_final = st.text_input("Tienda Custom") if f_tienda_sel == "CUSTOM" else f_tienda_sel
    
    st.markdown("---")
    f_usd_txt = st.text_input("Costo USD (Bruto)", value="0.0")
    f_tc_manual = st.text_input("TC para cálculo", value=str(tc_actual))
    
    def limpiar_num(val):
        try: return float(str(val).replace(',', '').replace('$', '')) if val else 0.0
        except: return 0.0

    costo_mxn_final = calcular_costo_final_mxn(limpiar_num(f_usd_txt), limpiar_num(f_tc_manual))
    st.success(f"Costo en MXN: **${costo_mxn_final:,.2f}**")
    
    f_foto = st.file_uploader("📷 Foto del Producto", type=["jpg", "png", "jpeg"])

    with st.form("registro_inv", clear_on_submit=False):
        f_precio_venta = st.text_input("Precio Venta (MXN)")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_color = st.text_input("Color")
            f_cantidad = st.number_input("Stock Total", min_value=1, value=1)
        with col_f2:
            f_talla = st.text_input("Talla")
            # CAMBIO: Ahora pides cuántos de ese stock ya están pagados
            f_pagados = st.number_input("Unidades Pagadas", min_value=0, max_value=int(f_cantidad), value=0)
        
        f_vendidos = st.text_input("Ventas iniciales", value="0")

        if st.form_submit_button("AÑADIR A INVENTARIO", use_container_width=True):
            if f_nombre and costo_mxn_final > 0:
                with st.spinner("Guardando..."):
                    url_foto = subir_a_nube(f_foto) if f_foto else ""
                    nuevo = pd.DataFrame([{
                        "Producto": f_nombre, "Tienda": f_tienda_final, 
                        "Precio MXN": costo_mxn_final,
                        "Precio Venta": limpiar_num(f_precio_venta),
                        "Color": f_color, "Talla": f_talla, 
                        "Cantidad": f_cantidad, 
                        "Vendidos": limpiar_num(f_vendidos),
                        "Pagados": f_pagados, 
                        "Imagen": url_foto
                    }])
                    df_final = pd.concat([lectura_inventario(), nuevo], ignore_index=True)
                    conn.update(worksheet="Inventario", data=df_final)
                    st.cache_data.clear()
                    st.success("✅ ¡Añadido!")
                    time.sleep(1)
                    st.rerun()

    # --- BORRADO ---
    st.divider()
    if not df_inv.empty:
        opciones_del = [f"{i} - {df_inv.loc[i, 'Producto']}" for i in reversed(df_inv.index)]
        seleccion = st.selectbox("Borrar Registro:", opciones_del)
        if st.button("ELIMINAR SELECCIONADO", use_container_width=True):
            st.session_state.confirmar_borrado_inv = True
        
        if st.session_state.get('confirmar_borrado_inv', False):
            st.error("¿Seguro?")
            c1, c2 = st.columns(2)
            if c1.button("SÍ", use_container_width=True):
                idx = int(seleccion.split(" - ")[0])
                df_final = df_inv.drop(idx)
                cols_clean = ["Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos", "Pagados", "Imagen"]
                conn.update(worksheet="Inventario", data=df_final[cols_clean])
                st.session_state.confirmar_borrado_inv = False
                st.cache_data.clear()
                st.rerun()
            if c2.button("NO", use_container_width=True):
                st.session_state.confirmar_borrado_inv = False
                st.rerun()

# --- CÁLCULOS PARA LA VISTA ---
df_inv["Disponible"] = df_inv["Cantidad"] - df_inv["Vendidos"]
df_inv["Venta Total $"] = df_inv["Vendidos"] * df_inv["Precio Venta"]
df_inv["Ganancia $"] = (df_inv["Precio Venta"] - df_inv["Precio MXN"]) * df_inv["Vendidos"]
# Columna visual informativa
df_inv["Estatus Pago"] = df_inv.apply(lambda x: f"✅ {int(x['Pagados'])} de {int(x['Cantidad'])}" if x['Pagados'] >= x['Cantidad'] else f"⚠️ {int(x['Pagados'])} de {int(x['Cantidad'])}", axis=1)
df_inv["ID"] = df_inv.index

cols_vista = ["ID", "Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", 
              "Cantidad", "Vendidos", "Pagados", "Estatus Pago", "Disponible", "Venta Total $", "Ganancia $", "Imagen"]

# --- TABLA INTERACTIVA ---
st.subheader("📊 Gestión de Stock e Inventario")

edited_inv = st.data_editor(
    df_inv[cols_vista].sort_index(ascending=False),
    column_config={
        "ID": st.column_config.NumberColumn("ID", disabled=True),
        "Precio MXN": st.column_config.NumberColumn("COSTO MXN", format="$%.2f"),
        "Precio Venta": st.column_config.NumberColumn("VENTA MXN", format="$%.2f"),
        "Pagados": st.column_config.NumberColumn("U. PAGADAS", help="Cuántas piezas ya pagó el cliente", min_value=0),
        "Estatus Pago": st.column_config.TextColumn("ESTATUS PAGO", disabled=True),
        "Disponible": st.column_config.NumberColumn("STOCK", disabled=True),
        "Venta Total $": st.column_config.NumberColumn("V. TOTAL", format="$%.2f", disabled=True),
        "Ganancia $": st.column_config.NumberColumn("GANANCIA", format="$%.2f", disabled=True),
        "Imagen": st.column_config.ImageColumn("🖼️") 
    },
    use_container_width=True, hide_index=True
)

if st.button("💾 GUARDAR CAMBIOS DE TABLA"):
    # VALIDACIÓN: Que no haya más pagados que stock en ninguna fila
    if any(edited_inv["Pagados"] > edited_inv["Cantidad"]):
        st.error("❌ Error: El número de unidades pagadas no puede ser mayor al stock total.")
    else:
        cols_save = ["Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos", "Pagados", "Imagen"]
        conn.update(worksheet="Inventario", data=edited_inv.sort_index()[cols_save])
        st.success("¡Sincronizado!")
        st.cache_data.clear()
        st.rerun()

# --- MÉTRICAS ---
st.divider()
if not edited_inv.empty:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 Stock Total", f"{int(edited_inv['Disponible'].sum())} pzs")
    m2.metric("💰 Ventas", f"${edited_inv['Venta Total $'].sum():,.2f}")
    
    # Cálculo de cuánto dinero falta por cobrar
    falta_cobrar = ((edited_inv['Cantidad'] - edited_inv['Pagados']) * edited_inv['Precio Venta']).sum()
    m3.metric("⏳ Pendiente Cobro", f"${falta_cobrar:,.2f}", delta_color="inverse")
    
    m4.metric("🏗️ Valor Bodega", f"${(edited_inv['Disponible'] * edited_inv['Precio MXN']).sum():,.2f}")