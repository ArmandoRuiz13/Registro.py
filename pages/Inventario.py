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
    columnas_base = ["Producto", "Tienda", "Precio MXN", "Color", "Talla", "Cantidad", "Vendidos"]
    try: 
        df = conn.read(worksheet="Inventario", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_base)
        df.columns = [str(c).strip() for c in df.columns]
        for col in columnas_base:
            if col not in df.columns:
                df[col] = 0 if col in ["Precio MXN", "Cantidad", "Vendidos"] else ""
        return df[columnas_base]
    except Exception:
        return pd.DataFrame(columns=columnas_base)

df_inv = lectura_inventario()

# --- CONVERSIÓN A NÚMEROS ---
for col in ["Precio MXN", "Cantidad", "Vendidos"]:
    df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# --- FORMULARIO DE REGISTRO (SIDEBAR) ---
with st.sidebar:
    st.header("🆕 Nuevo Producto")
    
    with st.form("registro_inv", clear_on_submit=True):
        f_nombre = st.text_input("Nombre del Producto")
        
        tiendas_opc = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
        f_tienda_sel = st.selectbox("Tienda", tiendas_opc)
        f_tienda_custom = st.text_input("Tienda custom (si aplica):")
        f_tienda_final = f_tienda_custom if f_tienda_sel == "CUSTOM" else f_tienda_sel
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_precio_txt = st.text_input("Precio MXN", placeholder="850")
            f_color = st.text_input("Color")
        with col_f2:
            f_cantidad_txt = st.text_input("Cantidad Total", placeholder="10")
            
            # TALLA colocada después de Cantidad
            opciones_talla = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "Numérica/Otra"]
            f_talla_sel = st.selectbox("Talla", opciones_talla)
            
        # Campo extra que solo se usa si elige Numérica
        f_talla_extra = st.text_input("Escribe la talla (si elegiste Numérica):")
            
        f_vendidos_txt = st.text_input("Ventas iniciales", value="0")
        
        def limpiar_num(val):
            try: return float(val) if val != "" else 0.0
            except: return 0.0

        if st.form_submit_button("AÑADIR REGISTRO", use_container_width=True):
            # Lógica para decidir qué talla guardar
            talla_final = f_talla_extra if f_talla_sel == "Numérica/Otra" else f_talla_sel
            
            if f_nombre and talla_final:
                nuevo = pd.DataFrame([{
                    "Producto": f_nombre, "Tienda": f_tienda_final, "Precio MXN": limpiar_num(f_precio_txt),
                    "Color": f_color, "Talla": talla_final, "Cantidad": limpiar_num(f_cantidad_txt), 
                    "Vendidos": limpiar_num(f_vendidos_txt)
                }])
                df_inv = pd.concat([df_inv, nuevo], ignore_index=True)
                conn.update(worksheet="Inventario", data=df_inv)
                st.cache_data.clear()
                st.rerun()

    # --- SECCIÓN DE BORRADO ---
    st.divider()
    st.header("🗑️ Borrar Producto")
    if not df_inv.empty:
        prod_borrar = st.selectbox("Selecciona para eliminar:", df_inv.index, format_func=lambda x: f"{df_inv.loc[x, 'Producto']} ({df_inv.loc[x, 'Talla']})")
        if st.button("ELIMINAR SELECCIONADO", use_container_width=True):
            st.session_state.confirm_borrar = True
        
        if st.session_state.get('confirm_borrar', False):
            st.warning("¿Confirmas eliminar?")
            cb1, cb2 = st.columns(2)
            if cb1.button("SÍ", type="primary"):
                df_inv = df_inv.drop(prod_borrar)
                conn.update(worksheet="Inventario", data=df_inv)
                st.session_state.confirm_borrar = False
                st.cache_data.clear()
                st.rerun()
            if cb2.button("NO"):
                st.session_state.confirm_borrar = False
                st.rerun()

# --- PROCESAMIENTO ---
df_inv["Disponible"] = df_inv["Cantidad"] - df_inv["Vendidos"]
df_inv["Total Vendido $"] = df_inv["Vendidos"] * df_inv["Precio MXN"]
df_inv["Valor en Stock $"] = df_inv["Disponible"] * df_inv["Precio MXN"]

# --- TABLA PRINCIPAL ---
st.subheader("📊 Tabla de Inventario")
edited_inv = st.data_editor(
    df_inv,
    column_config={
        "Disponible": st.column_config.NumberColumn(disabled=True),
        "Total Vendido $": st.column_config.NumberColumn(format="$%.2f", disabled=True),
        "Valor en Stock $": st.column_config.NumberColumn(format="$%.2f", disabled=True)
    },
    num_rows="dynamic", use_container_width=True, key="editor_inv"
)

if st.button("💾 GUARDAR CAMBIOS DE LA TABLA"):
    cols_save = ["Producto", "Tienda", "Precio MXN", "Color", "Talla", "Cantidad", "Vendidos"]
    conn.update(worksheet="Inventario", data=edited_inv[cols_save])
    st.success("Sincronizado!")
    st.cache_data.clear()
    st.rerun()

# --- ESTADÍSTICAS ---
st.divider()
st.subheader("📈 Análisis de Negocio")
if not edited_inv.empty:
    col1, col2, col3, col4 = st.columns(4)
    
    total_piezas = int(edited_inv["Cantidad"].sum())
    total_vendidas = int(edited_inv["Vendidos"].sum())
    
    col1.metric("Stock Total", f"{total_piezas} und")
    col2.metric("Ventas Realizadas", f"{total_vendidas} und")
    col3.metric("Capital Invertido", f"${(edited_inv['Cantidad'] * edited_inv['Precio MXN']).sum():,.2f}")
    col4.metric("Valor Almacén", f"${edited_inv['Valor en Stock $'].sum():,.2f}")

    c_izq, c_der = st.columns(2)
    with c_izq:
        st.write("### 🏷️ Stock por Tienda")
        st.bar_chart(edited_inv.groupby("Tienda")["Disponible"].sum())
    with c_der:
        st.write("### 💰 Ingresos por Tienda")
        st.bar_chart(edited_inv.groupby("Tienda")["Total Vendido $"].sum())