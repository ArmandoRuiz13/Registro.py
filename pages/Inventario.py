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

# --- FUNCIÓN DE LECTURA ROBUSTA ---
def lectura_inventario():
    columnas_base = ["Producto", "Tienda", "Precio MXN", "Color", "Talla", "Cantidad", "Vendidos"]
    try: 
        df = conn.read(worksheet="Inventario", ttl=0)
        
        # Si la hoja existe pero está totalmente vacía
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_base)
        
        # Limpiar nombres de columnas existentes
        df.columns = [str(c).strip() for c in df.columns]
        
        # Asegurar que todas las columnas necesarias existan
        for col in columnas_base:
            if col not in df.columns:
                df[col] = 0 if col in ["Precio MXN", "Cantidad", "Vendidos"] else ""
        
        return df[columnas_base]
    except Exception as e:
        # Si la pestaña ni siquiera existe o hay error de conexión
        return pd.DataFrame(columns=columnas_base)

df_inv = lectura_inventario()

# --- CONVERSIÓN A NÚMEROS ---
columnas_num = ["Precio MXN", "Cantidad", "Vendidos"]
for col in columnas_num:
    df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# --- FORMULARIO DE REGISTRO (SIDEBAR) ---
# --- DENTRO DEL FORMULARIO EN EL SIDEBAR ---
with st.sidebar:
    st.header("🆕 Nuevo Producto")
    with st.form("registro_inv", clear_on_submit=True):
        f_nombre = st.text_input("Nombre del Producto")
        
        # Tiendas
        tiendas_opc = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
        f_tienda_sel = st.selectbox("Tienda", tiendas_opc)
        f_tienda_custom = st.text_input("Escribe la tienda custom:") if f_tienda_sel == "CUSTOM" else ""
        f_tienda_final = f_tienda_custom if f_tienda_sel == "CUSTOM" else f_tienda_sel
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_precio = st.number_input("Precio MXN", min_value=0.0, step=50.0)
            
            # --- SECCIÓN DE TALLAS MEJORADA ---
            opciones_talla = [
                "XXS", "XS", "S", "M", "L", "XL", "XXL", 
                "Talla Numérica", "Otra"
            ]
            f_talla_sel = st.selectbox("Talla", opciones_talla)
            
            # Si elige numérica u otra, aparece el campo para escribir
            if f_talla_sel in ["Talla Numérica", "Otra"]:
                f_talla_final = st.text_input("Ingresa la talla:")
            else:
                f_talla_final = f_talla_sel

        with col_f2:
            f_cantidad = st.number_input("Cantidad", min_value=1, step=1)
            f_color = st.text_input("Color")
            
        f_vendidos = st.number_input("Ventas iniciales", min_value=0, step=1)
        
        if st.form_submit_button("AÑADIR REGISTRO", use_container_width=True):
            if f_nombre and f_talla_final:
                nuevo = pd.DataFrame([{
                    "Producto": f_nombre, 
                    "Tienda": f_tienda_final, 
                    "Precio MXN": f_precio,
                    "Color": f_color, 
                    "Talla": f_talla_final, # Aquí se guarda la talla final (fija o escrita)
                    "Cantidad": f_cantidad, 
                    "Vendidos": f_vendidos
                }])
                # ... (resto del código de guardado igual que antes)
                df_inv = pd.concat([df_inv, nuevo], ignore_index=True)
                conn.update(worksheet="Inventario", data=df_inv)
                st.cache_data.clear()
                st.success(f"¡{f_nombre} (Talla {f_talla_final}) agregado!")
                st.rerun()
            else:
                st.warning("El nombre y la talla son obligatorios")
# --- CÁLCULOS AUTOMÁTICOS ---
df_inv["Disponible"] = df_inv["Cantidad"] - df_inv["Vendidos"]
df_inv["Total Vendido"] = df_inv["Vendidos"] * df_inv["Precio MXN"]
df_inv["Valor Stock"] = df_inv["Disponible"] * df_inv["Precio MXN"]

# --- TABLA PRINCIPAL ---
st.subheader("📊 Control de Stock")
edited_inv = st.data_editor(
    df_inv,
    column_config={
        "Disponible": st.column_config.NumberColumn("Disponible", disabled=True),
        "Total Vendido": st.column_config.NumberColumn("Vendido ($)", format="$%.2f", disabled=True),
        "Valor Stock": st.column_config.NumberColumn("Valor Inventario", format="$%.2f", disabled=True)
    },
    num_rows="dynamic",
    use_container_width=True,
    key="editor_vfinal"
)

if st.button("💾 GUARDAR CAMBIOS DE TABLA", use_container_width=True):
    # Solo guardamos las columnas que no son cálculos automáticos
    cols_a_guardar = ["Producto", "Tienda", "Precio MXN", "Color", "Talla", "Cantidad", "Vendidos"]
    conn.update(worksheet="Inventario", data=edited_inv[cols_a_guardar])
    st.success("¡Nube actualizada!")
    st.cache_data.clear()
    st.rerun()

# --- ESTADÍSTICAS ---
st.divider()
st.subheader("📈 Estadísticas Generales")
m1, m2, m3, m4 = st.columns(4)

total_disponible = int(edited_inv["Disponible"].sum())
total_dinero_ventas = edited_inv["Total Vendido"].sum()
valor_total_almacen = edited_inv["Valor Stock"].sum()

m1.metric("Piezas Disponibles", f"{total_disponible} pzs")
m2.metric("Venta Realizada", f"${total_dinero_ventas:,.2f}")
m3.metric("Valor en Almacén", f"${valor_total_almacen:,.2f}")

# Calcular tienda más popular
if not edited_inv.empty:
    top_tienda = edited_inv.groupby("Tienda")["Cantidad"].sum().idxmax()
    m4.metric("Tienda Mayorista", top_tienda)

    # Gráfico de stock por tienda
    st.write("### Inventario por Tienda")
    st.bar_chart(edited_inv.groupby("Tienda")["Disponible"].sum())