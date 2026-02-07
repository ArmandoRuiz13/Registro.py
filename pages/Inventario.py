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

def lectura_inventario():
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
for col in ["Precio MXN", "Precio Venta", "Cantidad", "Vendidos"]:
    df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# --- FORMULARIO DE REGISTRO (SIDEBAR) ---
with st.sidebar:
    st.header("🆕 Nuevo Producto")
    
    # Selectores fuera del form para que la reactividad (ocultar/mostrar) sea instantánea
    tiendas_opc = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
    f_tienda_sel = st.selectbox("Tienda", tiendas_opc)
    
    # LOGICA OCULTAR TIENDA
    f_tienda_final = f_tienda_sel
    if f_tienda_sel == "CUSTOM":
        f_tienda_final = st.text_input("Nombre de Tienda Custom")

    opciones_talla = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "Numérica/Otra"]
    f_talla_sel = st.selectbox("Talla", opciones_talla)
    
    # LOGICA OCULTAR TALLA
    f_talla_final = f_talla_sel
    if f_talla_sel == "Numérica/Otra":
        f_talla_final = st.text_input("Escribe la talla")

    # Formulario para el resto de datos (esto quita el "Press Enter to Submit")
    with st.form("registro_inv", clear_on_submit=True):
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
            if f_nombre and f_tienda_final and f_talla_final:
                nuevo = pd.DataFrame([{
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
                st.success("Guardado!")
                st.rerun()
            else:
                st.error("Faltan datos (Nombre, Tienda o Talla)")

    # --- BORRADO ---
    st.divider()
    st.header("🗑️ Borrar Registro")
    if not df_inv.empty:
        prod_borrar = st.selectbox("Elegir:", df_inv.index, format_func=lambda x: f"{df_inv.loc[x, 'Producto']} ({df_inv.loc[x, 'Talla']})")
        if st.button("ELIMINAR"):
            st.session_state.confirmar = True
        
        if st.session_state.get('confirmar', False):
            st.warning("¿Seguro?")
            if st.button("SÍ, ELIMINAR"):
                df_inv = df_inv.drop(prod_borrar)
                conn.update(worksheet="Inventario", data=df_inv)
                st.session_state.confirmar = False
                st.cache_data.clear()
                st.rerun()

# --- CÁLCULOS ---
df_inv["Disponible"] = df_inv["Cantidad"] - df_inv["Vendidos"]
df_inv["Venta Total $"] = df_inv["Vendidos"] * df_inv["Precio Venta"]
df_inv["Ganancia $"] = (df_inv["Precio Venta"] - df_inv["Precio MXN"]) * df_inv["Vendidos"]

# --- TABLA ---
st.subheader("📊 Tabla de Inventario")
edited_inv = st.data_editor(
    df_inv,
    column_config={
        "Disponible": st.column_config.NumberColumn(disabled=True),
        "Venta Total $": st.column_config.NumberColumn(format="$%.2f", disabled=True),
        "Ganancia $": st.column_config.NumberColumn(format="$%.2f", disabled=True)
    },
    use_container_width=True
)

if st.button("💾 GUARDAR CAMBIOS DE TABLA"):
    cols_s = ["Producto", "Tienda", "Precio MXN", "Precio Venta", "Color", "Talla", "Cantidad", "Vendidos"]
    conn.update(worksheet="Inventario", data=edited_inv[cols_s])
    st.success("¡Sincronizado!")
    st.cache_data.clear()
    st.rerun()

# --- ESTADÍSTICAS ---
st.divider()
st.subheader("📈 Estadísticas")
if not edited_inv.empty:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Stock Piezas", f"{int(edited_inv['Disponible'].sum())}")
    m2.metric("Ventas Totales", f"${edited_inv['Venta Total $'].sum():,.2f}")
    m3.metric("Ganancia Real", f"${edited_inv['Ganancia $'].sum():,.2f}")
    m4.metric("Valor Invertido", f"${(edited_inv['Disponible'] * edited_inv['Precio MXN']).sum():,.2f}")