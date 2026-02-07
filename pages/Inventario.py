import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Inventario Pro", layout="wide")

# BOTÓN PARA VOLVER AL PRINCIPAL (app.py)
if st.sidebar.button("⬅️ VOLVER A VENTAS"):
    st.switch_page("app.py") 

st.title("📦 Gestión de Inventario y Stock")

conn = st.connection("gsheets", type=GSheetsConnection)

def lectura_inventario():
    for i in range(3):
        try: 
            # Lee de la pestaña "Inventario" de tu Google Sheet
            df = conn.read(worksheet="Inventario", ttl=0)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception: 
            time.sleep(1)
    # Estructura inicial si la hoja está vacía
    return pd.DataFrame(columns=[
        "Producto", "Precio MXN", "Color", "Talla", "Cantidad", "Vendidos"
    ])

df_inv = lectura_inventario()

# Convertir columnas a números para cálculos
columnas_num = ["Precio MXN", "Cantidad", "Vendidos"]
for col in columnas_num:
    df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# --- CÁLCULOS AUTOMÁTICOS ---
# Quedan (Stock) = Cantidad inicial - Vendidos
df_inv["Quedan (Stock)"] = df_inv["Cantidad"] - df_inv["Vendidos"]

# Total Vendido = Vendidos * Precio MXN
df_inv["Total Vendido"] = df_inv["Vendidos"] * df_inv["Precio MXN"]

st.info("Agrega productos con el botón '+' al final de la tabla. El stock y total vendido se calculan solos.")

# --- EDITOR DE TABLA ---
edited_inv = st.data_editor(
    df_inv,
    column_config={
        "Producto": st.column_config.TextColumn("Producto", width="medium"),
        "Precio MXN": st.column_config.NumberColumn("Precio MXN", format="$%.2f"),
        "Color": st.column_config.TextColumn("Color"),
        "Talla": st.column_config.SelectboxColumn("Talla", options=["XS", "S", "M", "L", "XL", "XL Tall", "28x30", "29", "30", "32"]),
        "Cantidad": st.column_config.NumberColumn("Stock Inicial"),
        "Vendidos": st.column_config.NumberColumn("Ventas Realizadas"),
        "Quedan (Stock)": st.column_config.NumberColumn("Disponible", disabled=True),
        "Total Vendido": st.column_config.NumberColumn("Total Vendido", format="$%.2f", disabled=True)
    },
    num_rows="dynamic",
    use_container_width=True,
    key="editor_inv_v2"
)

# --- BOTÓN DE GUARDADO ---
if st.button("💾 GUARDAR CAMBIOS EN LA NUBE"):
    # Quitamos las columnas calculadas para no guardarlas en el Excel (se recalculan al abrir)
    df_save = edited_inv.drop(columns=["Quedan (Stock)", "Total Vendido"])
    conn.update(worksheet="Inventario", data=df_save)
    st.success("¡Inventario sincronizado!")
    st.cache_data.clear()
    st.rerun()

# --- RESUMEN DE MÉTRICAS ---
st.divider()
c1, c2 = st.columns(2)
with c1:
    st.metric("Total Piezas en Stock", f"{int(edited_inv['Quedan (Stock)'].sum())} pzs")
with c2:
    st.metric("Venta Acumulada", f"${edited_inv['Total Vendido'].sum():,.2f}")