import streamlit as st
import pandas as pd
import time
import requests
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Inventario Pro", layout="wide")

# 🔑 CONFIGURACIÓN DE CLOUDINARY
CLOUD_NAME = "doi81tooh"
API_KEY = "245491997239959"
API_SECRET = "8Hgvfh6amI8vd0W_rG43HnSb2OI"

# --- FUNCIÓN PARA SUBIR IMÁGENES ---
def subir_a_nube(archivo_imagen):
    try:
        url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
        data = {
            "upload_preset": "ml_default", 
            "api_key": API_KEY,
        }
        files = {"file": archivo_imagen.getvalue()}
        res = requests.post(url, data=data, files=files)
        return res.json().get("secure_url") if res.status_code == 200 else None
    except:
        return None

# BOTÓN PARA VOLVER
if st.sidebar.button("⬅️ VOLVER A VENTAS"):
    st.switch_page("app.py") 

st.sidebar.divider()
st.title("📦 Gestión de Inventario y Stock")

conn = st.connection("gsheets", type=GSheetsConnection)

def lectura_inventario():
    # Se agregó la columna "Imagen"
    columnas_base = ["Imagen", "Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos"]
    try: 
        df = conn.read(worksheet="Inventario", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_base)
        df.columns = [str(c).strip() for c in df.columns]
        for col in columnas_base:
            if col not in df.columns:
                df[col] = "" if col in ["Imagen", "Producto", "Tienda", "Color", "Talla"] else 0
        return df[columnas_base]
    except Exception:
        return pd.DataFrame(columns=columnas_base)

df_inv = lectura_inventario()

for col in ["Precio MXN", "Precio Venta", "Cantidad", "Vendidos"]:
    df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# --- FORMULARIO DE REGISTRO (SIDEBAR) ---
    with st.sidebar:
        st.header("🆕 Nuevo Producto")
        
        tiendas_opc = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
        f_tienda_sel = st.selectbox("Tienda", tiendas_opc)
        f_tienda_final = st.text_input("Nombre de Tienda Custom") if f_tienda_sel == "CUSTOM" else f_tienda_sel

        opciones_talla = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "Numérica/Otra"]
        f_talla_sel = st.selectbox("Talla", opciones_talla)
        f_talla_final = st.text_input("Escribe la talla") if f_talla_sel == "Numérica/Otra" else f_talla_sel

        # --- CAMBIO AQUÍ: Cargador + Vista Previa ---
        f_foto = st.file_uploader("📷 Seleccionar Foto", type=["jpg", "png", "jpeg"])
        
        if f_foto:
            st.image(f_foto, caption="Vista previa de la prenda", use_container_width=True)
        # --------------------------------------------

        with st.form("registro_inv", clear_on_submit=False):
            f_nombre = st.text_input("Nombre del Producto")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                f_precio_costo = st.text_input("Precio Costo")
                f_color = st.text_input("Color")
            with col_f2:
                f_precio_venta = st.text_input("Precio Venta")
                f_cantidad_txt = st.text_input("Stock Inicial")

            f_vendidos_txt = st.text_input("Ventas realizadas", value="0")
        
        def limpiar_num(val):
            try: return float(str(val).replace(',', '')) if val != "" else 0.0
            except: return 0.0

        if st.form_submit_button("AÑADIR REGISTRO", use_container_width=True):
            if f_nombre and f_tienda_final:
                with st.spinner("Subiendo imagen..."):
                    url_foto = subir_a_nube(f_foto) if f_foto else ""
                
                nuevo = pd.DataFrame([{
                    "Imagen": url_foto,
                    "Producto": f_nombre, 
                    "Tienda": f_tienda_final, 
                    "Precio MXN": limpiar_num(f_precio_costo),
                    "Precio Venta": limpiar_num(f_precio_venta),
                    "Color": f_color, 
                    "Talla": f_talla_final, 
                    "Cantidad": limpiar_num(f_cantidad_txt), 
                    "Vendidos": limpiar_num(f_vendidos_txt)
                }])
                df_inv = pd.concat([df_inv, nuevo], ignore_index=True)
                conn.update(worksheet="Inventario", data=df_inv)
                st.cache_data.clear()
                st.success("¡Guardado!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Faltan datos")

# --- CÁLCULOS ---
df_inv["Disponible"] = df_inv["Cantidad"] - df_inv["Vendidos"]
df_inv["Venta Total $"] = df_inv["Vendidos"] * df_inv["Precio Venta"]
df_inv["Ganancia $"] = (df_inv["Precio Venta"] - df_inv["Precio MXN"]) * df_inv["Vendidos"]

# --- TABLA ---
st.subheader("📊 Tabla de Inventario")
edited_inv = st.data_editor(
    df_inv,
    column_config={
        "Imagen": st.column_config.ImageColumn("🖼️ Vista"),
        "Disponible": st.column_config.NumberColumn(disabled=True),
        "Venta Total $": st.column_config.NumberColumn(format="$%.2f", disabled=True),
        "Ganancia $": st.column_config.NumberColumn(format="$%.2f", disabled=True)
    },
    use_container_width=True,
    hide_index=True
)

if st.button("💾 GUARDAR CAMBIOS DE TABLA"):
    cols_s = ["Imagen", "Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos"]
    conn.update(worksheet="Inventario", data=edited_inv[cols_s])
    st.success("¡Sincronizado!")
    st.cache_data.clear()
    time.sleep(1)
    st.rerun()

# --- ESTADÍSTICAS ---
st.divider()
st.subheader("📈 Resumen de Stock y Ventas")
if not edited_inv.empty:
    m1, m2, m3, m4 = st.columns(4)
    total_disponible = int(edited_inv['Disponible'].sum())
    
    m1.metric("📦 Stock Restante", f"{total_disponible} pzs")
    m2.metric("💰 Ventas Totales", f"${edited_inv['Venta Total $'].sum():,.2f}")
    m3.metric("💵 Ganancia Real", f"${edited_inv['Ganancia $'].sum():,.2f}")
    m4.metric("🏗️ Valor en Bodega", f"${(edited_inv['Disponible'] * edited_inv['Precio MXN']).sum():,.2f}")