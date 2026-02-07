import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Inventario Pro", layout="wide")

# BOTÓN PARA VOLVER AL PRINCIPAL (app.py)
if st.sidebar.button("⬅️ VOLVER A VENTAS"):
    st.switch_page("app.py") 

st.sidebar.divider()

st.title("📦 Gestión de Inventario y Stock")

conn = st.connection("gsheets", type=GSheetsConnection)

def lectura_inventario():
    for i in range(3):
        try: 
            df = conn.read(worksheet="Inventario", ttl=0)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception: 
            time.sleep(1)
    return pd.DataFrame(columns=[
        "Producto", "Tienda", "Precio MXN", "Color", "Talla", "Cantidad", "Vendidos"
    ])

df_inv = lectura_inventario()

# Asegurar que la columna Tienda existe
if "Tienda" not in df_inv.columns:
    df_inv["Tienda"] = "N/A"

# Convertir columnas a números para cálculos
columnas_num = ["Precio MXN", "Cantidad", "Vendidos"]
for col in columnas_num:
    df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# --- FORMULARIO DE REGISTRO (SIDEBAR) ---
with st.sidebar:
    st.header("🆕 Registrar Producto")
    with st.form("nuevo_producto", clear_on_submit=True):
        f_nombre = st.text_input("Nombre del Producto")
        
        # Lógica de Tienda
        tiendas_lista = ["Hollister", "American Eagle", "Macys", "Finishline", "Guess", "Nike", "Aeropostale", "JDSports", "CUSTOM"]
        f_tienda_sel = st.selectbox("Tienda", tiendas_lista)
        f_tienda_custom = st.text_input("Nombre de tienda custom") if f_tienda_sel == "CUSTOM" else ""
        
        f_tienda_final = f_tienda_custom if f_tienda_sel == "CUSTOM" else f_tienda_sel
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_precio = st.number_input("Precio MXN", min_value=0.0, step=10.0)
            f_talla = st.selectbox("Talla", ["XS", "S", "M", "L", "XL", "XL Tall", "28x30", "29", "30", "32"])
        with col_f2:
            f_cantidad = st.number_input("Stock Inicial", min_value=1, step=1)
            f_color = st.text_input("Color")
        
        enviar = st.form_submit_button("Añadir al Inventario", use_container_width=True)
        
        if enviar:
            if f_nombre and f_tienda_final:
                nuevo_item = pd.DataFrame([{
                    "Producto": f_nombre,
                    "Tienda": f_tienda_final,
                    "Precio MXN": f_precio,
                    "Color": f_color,
                    "Talla": f_talla,
                    "Cantidad": f_cantidad,
                    "Vendidos": 0
                }])
                df_actualizado = pd.concat([df_inv, nuevo_item], ignore_index=True)
                conn.update(worksheet="Inventario", data=df_actualizado)
                st.success("¡Producto agregado!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Faltan datos obligatorios")

# --- CÁLCULOS AUTOMÁTICOS ---
df_inv["Quedan (Stock)"] = df_inv["Cantidad"] - df_inv["Vendidos"]
df_inv["Total Vendido"] = df_inv["Vendidos"] * df_inv["Precio MXN"]
df_inv["Inversión Total"] = df_inv["Cantidad"] * df_inv["Precio MXN"]

# --- EDITOR DE TABLA ---
st.subheader("📊 Tabla de Control")
edited_inv = st.data_editor(
    df_inv,
    column_config={
        "Producto": st.column_config.TextColumn("Producto", width="medium"),
        "Tienda": st.column_config.TextColumn("Tienda"),
        "Precio MXN": st.column_config.NumberColumn("Precio MXN", format="$%.2f"),
        "Talla": st.column_config.SelectboxColumn("Talla", options=["XS", "S", "M", "L", "XL", "XL Tall", "28x30", "29", "30", "32"]),
        "Quedan (Stock)": st.column_config.NumberColumn("Disponible", disabled=True),
        "Total Vendido": st.column_config.NumberColumn("Total Vendido", format="$%.2f", disabled=True),
        "Inversión Total": st.column_config.NumberColumn("Valor Inventario", format="$%.2f", disabled=True)
    },
    num_rows="dynamic",
    use_container_width=True,
    key="editor_inv_v3"
)

if st.button("💾 GUARDAR CAMBIOS DE LA TABLA"):
    df_save = edited_inv.drop(columns=["Quedan (Stock)", "Total Vendido", "Inversión Total"])
    conn.update(worksheet="Inventario", data=df_save)
    st.success("¡Nube actualizada!")
    st.cache_data.clear()
    st.rerun()

# --- ESTADÍSTICAS AVANZADAS ---
st.divider()
st.subheader("📈 Resumen de Inventario")
m1, m2, m3, m4 = st.columns(4)

with m1:
    total_stock = int(edited_inv['Quedan (Stock)'].sum())
    st.metric("Piezas Disponibles", f"{total_stock} pzs")

with m2:
    total_venta = edited_inv['Total Vendido'].sum()
    st.metric("Venta Acumulada", f"${total_venta:,.2f}")

with m3:
    valor_inv = edited_inv['Inversión Total'].sum()
    st.metric("Valor Total Inventario", f"${valor_inv:,.2f}")

with m4:
    # Tienda con más productos
    tienda_top = edited_inv['Tienda'].value_counts().idxmax() if not edited_inv.empty else "N/A"
    st.metric("Tienda con más Variedad", tienda_top)

# Gráfico rápido de stock por tienda
if not edited_inv.empty:
    st.write("### Distribución de Stock por Tienda")
    stock_tienda = edited_inv.groupby("Tienda")["Quedan (Stock)"].sum().sort_values(ascending=False)
    st.bar_chart(stock_tienda)