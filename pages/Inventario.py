import streamlit as st
import pandas as pd
import time
import requests
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inventario Pro", layout="wide")

# 🔑 CONFIGURACIÓN DE CLOUDINARY
CLOUD_NAME = "doi81tooh"
API_KEY = "245491997239959"
API_SECRET = "8Hgvfh6amI8vd0W_rG43HnSb2OI"

# --- FUNCIÓN PARA SUBIR IMÁGENES A CLOUDINARY ---
def subir_a_nube(archivo_imagen):
    try:
        url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
        data = {
            "upload_preset": "ml_default", 
            "api_key": API_KEY,
        }
        files = {"file": archivo_imagen.getvalue()}
        res = requests.post(url, data=data, files=files)
        if res.status_code == 200:
            return res.json().get("secure_url")
        return None
    except Exception:
        return None

# --- NAVEGACIÓN ---
if st.sidebar.button("⬅️ VOLVER A VENTAS", use_container_width=True):
    st.switch_page("app.py") 

st.sidebar.divider()
st.title("📦 Gestión de Inventario y Stock")

# --- CONEXIÓN A GSHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def lectura_inventario():
    # SE AGREGA "Pagado Venta" a la estructura base
    columnas_base = ["Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos", "Pagado Venta", "Imagen"]
    try: 
        df = conn.read(worksheet="Inventario", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_base)
        
        df.columns = [str(c).strip() for c in df.columns]
        
        for col in columnas_base:
            if col not in df.columns:
                # Si es la de pagado, inicializa como False (Check vacío)
                if col == "Pagado Venta":
                    df[col] = False
                else:
                    df[col] = 0 if col in ["Precio MXN", "Precio Venta", "Cantidad", "Vendidos"] else ""
        
        # Aseguramos que sea booleano para que Streamlit pinte el checkbox
        df["Pagado Venta"] = df["Pagado Venta"].fillna(False).astype(bool)
        return df[columnas_base]
    except Exception:
        return pd.DataFrame(columns=columnas_base)

df_inv = lectura_inventario()
proximo_id_visual = len(df_inv)

# Conversión de tipos para cálculos
for col in ["Precio MXN", "Precio Venta", "Cantidad", "Vendidos"]:
    df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# --- SIDEBAR: REGISTRO ---
with st.sidebar:
    st.header(f"🆕 Nuevo Producto (ID: {proximo_id_visual})")
    
    tiendas_opc = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
    f_tienda_sel = st.selectbox("Tienda", tiendas_opc)
    f_tienda_final = st.text_input("Nombre de Tienda Custom") if f_tienda_sel == "CUSTOM" else f_tienda_sel

    opciones_talla = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "Numérica/Otra"]
    f_talla_sel = st.selectbox("Talla", opciones_talla)
    f_talla_final = st.text_input("Escribe la talla") if f_talla_sel == "Numérica/Otra" else f_talla_sel

    f_foto = st.file_uploader("📷 FOTO DEL PRODUCTO", type=["jpg", "png", "jpeg"])
    if f_foto:
        st.image(f_foto, caption="Vista previa", use_container_width=True)

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
        f_pagado = st.checkbox("¿Pagado?") # NUEVO CAMPO EN FORMULARIO
        
        def limpiar_num(val):
            try: return float(str(val).replace(',', '').replace('$', '')) if val != "" else 0.0
            except: return 0.0

        if st.form_submit_button("AÑADIR A INVENTARIO", use_container_width=True):
            if f_nombre and f_tienda_final:
                with st.spinner("Guardando..."):
                    url_foto = subir_a_nube(f_foto) if f_foto else ""
                    
                    nuevo = pd.DataFrame([{
                        "Producto": f_nombre, 
                        "Tienda": f_tienda_final, 
                        "Precio MXN": limpiar_num(f_precio_costo),
                        "Precio Venta": limpiar_num(f_precio_venta),
                        "Color": f_color, 
                        "Talla": f_talla_final, 
                        "Cantidad": limpiar_num(f_cantidad_txt), 
                        "Vendidos": limpiar_num(f_vendidos_txt),
                        "Pagado Venta": f_pagado, # NUEVO
                        "Imagen": url_foto
                    }])
                    
                    df_fresco = lectura_inventario()
                    df_final = pd.concat([df_fresco, nuevo], ignore_index=True)
                    conn.update(worksheet="Inventario", data=df_final)
                    
                    st.cache_data.clear()
                    st.success("✅ ¡Añadido!")
                    time.sleep(1)
                    st.rerun()

    # --- BORRADO CON CONFIRMACIÓN (RESTAURADO) ---
    st.divider()
    if not df_inv.empty:
        opciones_del = [f"{i} - {df_inv.loc[i, 'Producto']}" for i in reversed(df_inv.index)]
        seleccion = st.selectbox("Borrar Registro:", opciones_del)
        
        if st.button("ELIMINAR SELECCIONADO", use_container_width=True):
            st.session_state.confirmar_borrado_inv = True
        
        if st.session_state.get('confirmar_borrado_inv', False):
            st.error("¿Estás seguro de eliminar este producto?")
            c1, c2 = st.columns(2)
            if c1.button("SÍ, ELIMINAR", use_container_width=True):
                idx_borrar = int(seleccion.split(" - ")[0])
                df_final = df_inv.drop(idx_borrar)
                # Al borrar, nos aseguramos de no enviar las columnas calculadas
                cols_limpias = ["Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos", "Pagado Venta", "Imagen"]
                conn.update(worksheet="Inventario", data=df_final[cols_limpias])
                st.session_state.confirmar_borrado_inv = False
                st.cache_data.clear()
                st.rerun()
            if c2.button("CANCELAR", use_container_width=True):
                st.session_state.confirmar_borrado_inv = False
                st.rerun()

# --- CÁLCULOS ---
df_inv["Disponible"] = df_inv["Cantidad"] - df_inv["Vendidos"]
df_inv["Venta Total $"] = df_inv["Vendidos"] * df_inv["Precio Venta"]
df_inv["Ganancia $"] = (df_inv["Precio Venta"] - df_inv["Precio MXN"]) * df_inv["Vendidos"]
df_inv["ID"] = df_inv.index

# ORDEN: Se incluye Pagado Venta en la vista
cols_vista = ["ID", "Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", 
              "Cantidad", "Vendidos", "Pagado Venta", "Disponible", "Venta Total $", "Ganancia $", "Imagen"]

# --- TABLA ---
st.subheader("📊 Tabla de Inventario")
df_vista = df_inv[cols_vista].sort_index(ascending=False)

edited_inv = st.data_editor(
    df_vista,
    column_config={
        "ID": st.column_config.NumberColumn("ID", disabled=True),
        "Pagado Venta": st.column_config.CheckboxColumn("PAGADO?"), # NUEVO
        "Precio MXN": st.column_config.NumberColumn("COSTO", format="$%.2f"),
        "Precio Venta": st.column_config.NumberColumn("VENTA", format="$%.2f"),
        "Disponible": st.column_config.NumberColumn("STOCK", disabled=True),
        "Venta Total $": st.column_config.NumberColumn("V. TOTAL", format="$%.2f", disabled=True),
        "Ganancia $": st.column_config.NumberColumn("GANANCIA", format="$%.2f", disabled=True),
        "Imagen": st.column_config.ImageColumn("🖼️ IMAGEN") 
    },
    use_container_width=True,
    hide_index=True
)

if st.button("💾 GUARDAR CAMBIOS DE TABLA"):
    # Guardamos incluyendo la nueva columna Pagado Venta
    cols_a_guardar = ["Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos", "Pagado Venta", "Imagen"]
    df_sincronizar = edited_inv.sort_index()[cols_a_guardar]
    conn.update(worksheet="Inventario", data=df_sincronizar)
    st.success("¡Sincronizado!")
    st.cache_data.clear()
    st.rerun()

# --- MÉTRICAS ---
st.divider()
if not edited_inv.empty:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 Stock", f"{int(edited_inv['Disponible'].sum())} pzs")
    m2.metric("💰 Ventas", f"${edited_inv['Venta Total $'].sum():,.2f}")
    m3.metric("💵 Ganancia", f"${edited_inv['Ganancia $'].sum():,.2f}")
    m4.metric("🏗️ Bodega", f"${(edited_inv['Disponible'] * edited_inv['Precio MXN']).sum():,.2f}")