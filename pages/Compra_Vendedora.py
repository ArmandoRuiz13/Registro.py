import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Compra Vendedora - Seguimiento", layout="centered")

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

st.title("🛍️ Compra Vendedora")

if st.button("⬅️ Volver al Menú", use_container_width=True):
    st.switch_page("app.py")

st.divider()

# --- FORMULARIO DE REGISTRO EXPRESS ---
with st.expander("🚀 NUEVO REGISTRO RÁPIDO", expanded=True):
    with st.form("form_registro_express", clear_on_submit=True):
        f_producto = st.text_input("Producto")
        f_cliente = st.text_input("Cliente (Opcional)")
        f_foto = st.file_uploader("📷 Foto", type=["jpg", "png", "jpeg"])
        
        c1, c2 = st.columns(2)
        with c1:
            f_usd = st.number_input("Costo USD", min_value=0.0, step=0.1)
        with c2:
            f_abono = st.number_input("Abono inicial (MXN)", min_value=0.0, step=50.0)
            
        submit = st.form_submit_button("✅ GUARDAR Y SEGUIR", use_container_width=True)

    if submit:
        if f_producto and f_usd > 0:
            with st.spinner("Registrando..."):
                url_foto = subir_a_nube(f_foto) if f_foto else "https://via.placeholder.com/150"
                
                # Cálculos internos
                f_usd_tax = f_usd * 1.0825
                f_comi_mxn = (f_usd_tax * 0.12) * 19
                costo_mxn = round((f_usd_tax * tc_actual) + f_comi_mxn, 2)
                saldo_inicial = costo_mxn - f_abono
                
                nuevo_reg = {
                    "ID": len(df_cv) + 1,
                    "Fecha_Registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Producto": f_producto,
                    "Cliente": f_cliente if f_cliente else "N/A",
                    "Foto_URL": url_foto,
                    "Costo_USD": f_usd,
                    "Costo_MXN": costo_mxn,
                    "Abono": f_abono,
                    "Saldo": saldo_inicial,
                    "Entregado": "NO", # Por defecto NO al registrar
                    "Liquidado": "NO",  # Por defecto NO al registrar
                    "Fecha_Liquidacion": "Pendiente"
                }
                
                df_final = pd.concat([df_cv, pd.DataFrame([nuevo_reg])], ignore_index=True)
                conn.update(worksheet="CompradoraV", data=df_final)
                st.cache_data.clear()
                st.success(f"¡Registrado! Costo: ${costo_mxn:,.2f}")
                time.sleep(1)
                st.rerun()

# --- SECCIÓN DE SEGUIMIENTO Y MODIFICACIÓN ---
st.subheader("📋 Seguimiento de Pedidos")

if not df_cv.empty:
    # Filtros rápidos
    vistas = ["Todos", "Pendientes 🔴", "Entregados 📦", "Liquidados 🟢"]
    sel_vista = st.segmented_control("Filtrar por:", vistas, default="Todos")
    
    df_edit = df_cv.copy().sort_index(ascending=False)
    
    if sel_vista == "Pendientes 🔴":
        df_edit = df_edit[df_edit["Liquidado"] == "NO"]
    elif sel_vista == "Entregados 📦":
        df_edit = df_edit[df_edit["Entregado"] == "SÍ"]
    elif sel_vista == "Liquidados 🟢":
        df_edit = df_edit[df_edit["Liquidado"] == "SÍ"]

    # Aquí es donde modificas el estado de entrega y liquidación
    edited_df = st.data_editor(
        df_edit,
        column_config={
            "Foto_URL": st.column_config.ImageColumn("🖼️"),
            "Producto": st.column_config.TextColumn("Producto", disabled=True),
            "Abono": st.column_config.NumberColumn("Abono (MXN)", format="$%.2f"),
            "Entregado": st.column_config.SelectboxColumn("Entregado", options=["SÍ", "NO"]),
            "Liquidado": st.column_config.SelectboxColumn("Liquidado", options=["SÍ", "NO"]),
            "Saldo": st.column_config.NumberColumn("Saldo", format="$%.2f", disabled=True),
            "Fecha_Liquidacion": st.column_config.TextColumn("Fecha Liq.", disabled=True),
            "ID": None, "Fecha_Registro": None, "Costo_USD": None, "Costo_MXN": None # Ocultos para vista limpia
        },
        use_container_width=True,
        hide_index=True
    )

    if st.button("💾 GUARDAR CAMBIOS DE SEGUIMIENTO", use_container_width=True, type="primary"):
        # Lógica para actualizar fechas y saldos automáticamente al editar
        for idx in edited_df.index:
            # Si se marca como liquidado ahora
            if edited_df.at[idx, "Liquidado"] == "SÍ":
                if edited_df.at[idx, "Fecha_Liquidacion"] == "Pendiente":
                    edited_df.at[idx, "Fecha_Liquidacion"] = datetime.now().strftime("%d/%m/%Y")
                edited_df.at[idx, "Saldo"] = 0.0
            else:
                edited_df.at[idx, "Fecha_Liquidacion"] = "Pendiente"
                # Recalcular saldo por si cambió el abono
                total_mxn = df_cv.loc[idx, "Costo_MXN"]
                edited_df.at[idx, "Saldo"] = total_mxn - edited_df.at[idx, "Abono"]

        # Sincronizar con la base principal
        df_cv.update(edited_df)
        conn.update(worksheet="CompradoraV", data=df_cv)
        st.cache_data.clear()
        st.success("¡Seguimiento actualizado!")
        time.sleep(1)
        st.rerun()
else:
    st.info("Aún no tienes registros para seguimiento.")