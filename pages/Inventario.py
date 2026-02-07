import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Inventario Pro", layout="wide")

# BOTÓN PARA VOLVER
if st.sidebar.button("⬅️ VOLVER A VENTAS"):
    st.switch_page("app.py") 

st.sidebar.divider()

st.title("📦 Gestión de Inventario y Stock")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN DE LECTURA ROBUSTA (Crea columnas si no existen) ---
def lectura_inventario():
    # Agregada columna "Precio Venta"
    columnas_base = ["Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos"]
    try: 
        df = conn.read(worksheet="Inventario", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_base)
        
        df.columns = [str(c).strip() for c in df.columns]
        for col in columnas_base:
            if col not in df.columns:
                df[col] = 0 if col in ["Precio MXN", "Precio Venta", "Cantidad", "Vendidos"] else ""
        
        return df[columnas_base]
    except Exception:
        return pd.DataFrame(columns=columnas_base)

df_inv = lectura_inventario()

# --- CONVERSIÓN A NÚMEROS ---
columnas_num_totales = ["Precio MXN", "Precio Venta", "Cantidad", "Vendidos"]
for col in columnas_num_totales:
    df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# --- FORMULARIO DE REGISTRO (SIDEBAR) ---
with st.sidebar:
    st.header("🆕 Nuevo Producto")
    
    # Usamos el formulario para evitar el "Press Enter to Submit"
    with st.form("registro_inv", clear_on_submit=True):
        f_nombre = st.text_input("Nombre del Producto", placeholder="Ej: Gorra Nike")
        
        # Tienda
        tiendas_opc = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
        f_tienda_sel = st.selectbox("Tienda", tiendas_opc)
        f_tienda_custom = st.text_input("Nombre de Tienda Custom (Si aplica)")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_precio_costo = st.text_input("Precio Costo (MXN)", placeholder="Ej: 500")
            f_color = st.text_input("Color")
            
        with col_f2:
            f_precio_venta = st.text_input("Precio Venta (MXN)", placeholder="Ej: 850")
            f_cantidad_txt = st.text_input("Stock Inicial", placeholder="10")

        # Talla
        opciones_talla = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "Numérica/Otra"]
        f_talla_sel = st.selectbox("Talla", opciones_talla)
        f_talla_extra = st.text_input("Escribe la talla (Si es Numérica)")
            
        f_vendidos_txt = st.text_input("Ventas realizadas", value="0")
        
        def limpiar_num(val):
            try: return float(str(val).replace(',', '')) if val != "" else 0.0
            except: return 0.0

        submit = st.form_submit_button("AÑADIR REGISTRO", use_container_width=True)
        
        if submit:
            # Lógica de selección final
            t_final = f_tienda_custom if f_tienda_sel == "CUSTOM" else f_tienda_sel
            ta_final = f_talla_extra if f_talla_sel == "Numérica/Otra" else f_talla_sel
            
            if f_nombre:
                nuevo = pd.DataFrame([{
                    "Producto": f_nombre, 
                    "Tienda": t_final, 
                    "Precio MXN": limpiar_num(f_precio_costo),
                    "Precio Venta": limpiar_num(f_precio_venta),
                    "Color": f_color, 
                    "Talla": ta_final, 
                    "Cantidad": limpiar_num(f_cantidad_txt), 
                    "Vendidos": limpiar_num(f_vendidos_txt)
                }])
                df_inv = pd.concat([df_inv, nuevo], ignore_index=True)
                conn.update(worksheet="Inventario", data=df_inv)
                st.cache_data.clear()
                st.success("¡Producto añadido!")
                st.rerun()
            else:
                st.error("El nombre es obligatorio")

    # --- SECCIÓN DE BORRADO ---
    st.divider()
    st.header("🗑️ Borrar Registro")
    if not df_inv.empty:
        prod_borrar = st.selectbox("Elegir producto:", df_inv.index, format_func=lambda x: f"{df_inv.loc[x, 'Producto']} - {df_inv.loc[x, 'Talla']}")
        if st.button("BORRAR", use_container_width=True):
            st.session_state.confirmar = True
        
        if st.session_state.get('confirmar', False):
            st.warning("¿Confirmas eliminarlo?")
            b1, b2 = st.columns(2)
            if b1.button("SÍ", type="primary"):
                df_inv = df_inv.drop(prod_borrar)
                conn.update(worksheet="Inventario", data=df_inv)
                st.session_state.confirmar = False
                st.cache_data.clear()
                st.rerun()
            if b2.button("NO"):
                st.session_state.confirmar = False
                st.rerun()

# --- CÁLCULOS ---
df_inv["Disponible"] = df_inv["Cantidad"] - df_inv["Vendidos"]
df_inv["Venta Total $"] = df_inv["Vendidos"] * df_inv["Precio Venta"]
df_inv["Ganancia Estimada $"] = (df_inv["Precio Venta"] - df_inv["Precio MXN"]) * df_inv["Vendidos"]

# --- TABLA ---
st.subheader("📊 Tabla de Inventario")
edited_inv = st.data_editor(
    df_inv,
    column_config={
        "Precio MXN": st.column_config.NumberColumn("Costo", format="$%.2f"),
        "Precio Venta": st.column_config.NumberColumn("Venta", format="$%.2f"),
        "Disponible": st.column_config.NumberColumn(disabled=True),
        "Venta Total $": st.column_config.NumberColumn(format="$%.2f", disabled=True),
        "Ganancia Estimada $": st.column_config.NumberColumn(format="$%.2f", disabled=True)
    },
    num_rows="dynamic", use_container_width=True
)

if st.button("💾 GUARDAR CAMBIOS DE TABLA"):
    cols_s = ["Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos"]
    conn.update(worksheet="Inventario", data=edited_inv[cols_s])
    st.success("¡Datos guardados!")
    st.cache_data.clear()
    st.rerun()

# --- ESTADÍSTICAS ---
st.divider()
st.subheader("📈 Estadísticas de Negocio")
if not edited_inv.empty:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Piezas en Stock", f"{int(edited_inv['Disponible'].sum())}")
    m2.metric("Total Ventas", f"${edited_inv['Venta Total $'].sum():,.2f}")
    m3.metric("Ganancia Realizada", f"${edited_inv['Ganancia Estimada $'].sum():,.2f}")
    m4.metric("Inversión en Stock", f"${(edited_inv['Disponible'] * edited_inv['Precio MXN']).sum():,.2f}")