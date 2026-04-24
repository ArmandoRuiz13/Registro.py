import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA (Móvil First) ---
st.set_page_config(page_title="Compra Vendedora", layout="centered")

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

def lectura_compradora():
    columnas_base = [
        "ID", "Fecha_Registro", "Producto", "Cliente", "Foto_URL", 
        "Costo_USD", "Costo_MXN", "Abono", "Saldo", 
        "Entregado", "Liquidado", "Fecha_Liquidacion"
    ]
    try: 
        df = conn.read(worksheet="CompradoraV", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_base)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame(columns=columnas_base)

# --- INICIO DE LÓGICA ---
tc_actual = obtener_tc()
df_cv = lectura_compradora()

# --- INTERFAZ MÓVIL ---
st.title("🛍️ Compra Vendedora")

# Botón para volver rápido
if st.button("⬅️ Volver al Menú", use_container_width=True):
    st.switch_page("app.py")

st.divider()

# --- FORMULARIO DE REGISTRO RÁPIDO ---
with st.expander("➕ REGISTRAR NUEVA COMPRA", expanded=True):
    with st.form("form_registro"):
        f_producto = st.text_input("Producto", placeholder="Ej: Tenis Nike")
        f_cliente = st.text_input("Cliente", placeholder="¿Quién lo encargó?")
        
        f_foto = st.file_uploader("📷 Tomar/Subir Foto", type=["jpg", "png", "jpeg"])
        
        col1, col2 = st.columns(2)
        with col1:
            f_usd = st.number_input("Costo USD", min_value=0.0, step=0.1)
        with col2:
            f_abono = st.number_input("Abono (MXN)", min_value=0.0, step=50.0)
            
        st.write(f"💡 TC actual: **${tc_actual}**")
        
        # Cálculo de costos (siguiendo tu lógica previa)
        f_usd_tax = f_usd * 1.0825
        f_comi_mxn = (f_usd_tax * 0.12) * 19
        costo_mxn = round((f_usd_tax * tc_actual) + f_comi_mxn, 2)
        
        st.info(f"Costo Total: **${costo_mxn:,.2f} MXN**")
        
        f_entregado = st.checkbox("¿Ya se entregó?")
        f_liquidado = st.checkbox("¿Ya está liquidado?")

        submit = st.form_submit_button("💾 GUARDAR REGISTRO", use_container_width=True)

    if submit:
        if f_producto and f_usd > 0:
            with st.spinner("Subiendo datos..."):
                url_foto = subir_a_nube(f_foto) if f_foto else "https://via.placeholder.com/150"
                
                # Lógica de liquidación
                fecha_liq = datetime.now().strftime("%d/%m/%Y") if f_liquidado else "Pendiente"
                saldo = costo_mxn - f_abono if not f_liquidado else 0.0
                
                nuevo_reg = {
                    "ID": len(df_cv) + 1,
                    "Fecha_Registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Producto": f_producto,
                    "Cliente": f_cliente if f_cliente else "N/A",
                    "Foto_URL": url_foto,
                    "Costo_USD": f_usd,
                    "Costo_MXN": costo_mxn,
                    "Abono": f_abono,
                    "Saldo": saldo,
                    "Entregado": "SÍ" if f_entregado else "NO",
                    "Liquidado": "SÍ" if f_liquidado else "NO",
                    "Fecha_Liquidacion": fecha_liq
                }
                
                df_final = pd.concat([df_cv, pd.DataFrame([nuevo_reg])], ignore_index=True)
                conn.update(worksheet="CompradoraV", data=df_final)
                st.cache_data.clear()
                st.success("✅ Guardado correctamente")
                time.sleep(1)
                st.rerun()
        else:
            st.warning("Escribe el nombre y el costo.")

# --- LISTADO / GESTIÓN ---
st.subheader("📋 Mis Pedidos")

if not df_cv.empty:
    # Filtro rápido para móvil
    opcion_filtro = st.radio("Ver:", ["Todos", "Pendientes 🔴", "Liquidados 🟢"], horizontal=True)
    
    df_mostrar = df_cv.copy().sort_index(ascending=False)
    
    if "Pendientes" in opcion_filtro:
        df_mostrar = df_mostrar[df_mostrar["Liquidado"] == "NO"]
    elif "Liquidados" in opcion_filtro:
        df_mostrar = df_mostrar[df_mostrar["Liquidado"] == "SÍ"]

    # Editor de tabla simplificado para móvil
    edited_df = st.data_editor(
        df_mostrar,
        column_config={
            "Foto_URL": st.column_config.ImageColumn("🖼️"),
            "Costo_MXN": st.column_config.NumberColumn("Costo", format="$%.2f", disabled=True),
            "Abono": st.column_config.NumberColumn("Abono", format="$%.2f"),
            "Saldo": st.column_config.NumberColumn("Saldo", format="$%.2f", disabled=True),
            "Entregado": st.column_config.SelectboxColumn("Entreg.", options=["SÍ", "NO"]),
            "Liquidado": st.column_config.SelectboxColumn("Liq.", options=["SÍ", "NO"]),
            "ID": None, "Fecha_Registro": None, "Costo_USD": None # Ocultar columnas poco importantes en móvil
        },
        use_container_width=True,
        hide_index=True
    )

    if st.button("💾 ACTUALIZAR CAMBIOS", use_container_width=True, type="primary"):
        # Al actualizar, recalculamos saldos y fechas de liquidación
        for i in edited_df.index:
            # Si se marca como liquidado y no tenía fecha, poner hoy
            if edited_df.at[i, "Liquidado"] == "SÍ" and edited_df.at[i, "Fecha_Liquidacion"] == "Pendiente":
                edited_df.at[i, "Fecha_Liquidacion"] = datetime.now().strftime("%d/%m/%Y")
                edited_df.at[i, "Saldo"] = 0.0
            elif edited_df.at[i, "Liquidado"] == "NO":
                edited_df.at[i, "Fecha_Liquidacion"] = "Pendiente"
                edited_df.at[i, "Saldo"] = edited_df.at[i, "Costo_MXN"] - edited_df.at[i, "Abono"]

        # Mezclamos con el DF original para no perder las filas filtradas
        df_cv.update(edited_df)
        conn.update(worksheet="CompradoraV", data=df_cv)
        st.cache_data.clear()
        st.success("¡Datos actualizados!")
        time.sleep(1)
        st.rerun()

else:
    st.info("No hay registros en CompradoraV aún.")
