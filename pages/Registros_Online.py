import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Lolis · Registros Online", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
#MainMenu,footer,header{visibility:hidden}.block-container{padding-top:1rem!important;max-width:1200px}
[data-testid="stButton"] button{border-radius:14px!important;min-height:44px!important;font-weight:700!important}
@media(max-width:700px){.block-container{padding:.5rem .8rem!important}h1{font-size:1.6rem!important}}
</style>""", unsafe_allow_html=True)
conn = st.connection("gsheets", type=GSheetsConnection)

def nav():
    cols=st.columns(4)
    for c,label,page in zip(cols,["➕ Registrar","📋 Online","👩‍💼 Compradoras","💰 Cobranza"],["app.py","pages/Registros_Online.py","pages/Registros_Compradoras.py","pages/Cobranza.py"]):
        with c:
            if st.button(label,use_container_width=True,key="n_"+label): st.switch_page(page)
nav()
st.title("📋 Registros Online")
st.caption("Compras que tú realizas online. Se guardan separadas de los registros de compradoras.")
try:
    df=conn.read(ttl=0); df.columns=[str(c).strip() for c in df.columns]
except Exception:
    df=pd.DataFrame()
if df.empty:
    st.info("No hay registros online.")
    st.stop()
for col,default in [("TIPO_ARTICULO","Otro"),("CLIENTE","N/A"),("FOTO_URL","")]:
    if col not in df.columns: df[col]=default

# Normaliza las fotos para evitar que valores vacíos/NaN rompan ImageColumn.
df["FOTO_URL"] = df["FOTO_URL"].fillna("").astype(str).replace({"nan": "", "None": ""})
for c in ["VENTA_MXN","MONTO_RECIBIDO","GANANCIA_MXN","COSTO_TOTAL_MXN"]:
    if c in df.columns: df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)

c1,c2,c3=st.columns(3)
with c1: bus=st.text_input("🔎 Buscar",placeholder="Producto o cliente")
with c2: tipo=st.selectbox("Tipo",["Todos"]+sorted(df["TIPO_ARTICULO"].dropna().astype(str).unique().tolist()))
with c3: estado=st.selectbox("Pago",["Todos","🔴 Debe","🟡 Abonado","🟢 Pagado"])

view=df.copy()
if bus: view=view[view.astype(str).apply(lambda r:r.str.contains(bus,case=False,na=False).any(),axis=1)]
if tipo!="Todos": view=view[view["TIPO_ARTICULO"]==tipo]
if estado!="Todos" and "ESTADO_PAGO" in view.columns: view=view[view["ESTADO_PAGO"]==estado]

st.write(f"**{len(view)} registros**")
cols=[c for c in ["FECHA_REGISTRO","PRODUCTO","TIPO_ARTICULO","CLIENTE","TIENDA","COSTO_TOTAL_MXN","VENTA_MXN","GANANCIA_MXN","ESTADO_PAGO","MONTO_RECIBIDO","COMI_CHECK","FOTO_URL"] if c in view.columns]
# Configuración de columnas construida de forma segura: algunas versiones de
# Streamlit no exponen ImageColumn. En ese caso la foto se muestra como URL.
column_config = {}
if "FOTO_URL" in cols:
    image_column = getattr(st.column_config, "ImageColumn", None)
    if image_column is not None:
        column_config["FOTO_URL"] = image_column("📷 FOTO")
    else:
        column_config["FOTO_URL"] = st.column_config.LinkColumn("📷 FOTO", display_text="Abrir foto")
if "COSTO_TOTAL_MXN" in cols:
    column_config["COSTO_TOTAL_MXN"] = st.column_config.NumberColumn("COSTO", format="$%.2f")
if "VENTA_MXN" in cols:
    column_config["VENTA_MXN"] = st.column_config.NumberColumn("VENTA", format="$%.2f")
if "GANANCIA_MXN" in cols:
    column_config["GANANCIA_MXN"] = st.column_config.NumberColumn("GANANCIA", format="$%.2f")
if "MONTO_RECIBIDO" in cols:
    column_config["MONTO_RECIBIDO"] = st.column_config.NumberColumn("RECIBIDO", format="$%.2f")
if "ESTADO_PAGO" in cols:
    column_config["ESTADO_PAGO"] = st.column_config.SelectboxColumn(
        "ESTADO", options=["🔴 Debe", "🟡 Abonado", "🟢 Pagado"]
    )
if "COMI_CHECK" in cols:
    column_config["COMI_CHECK"] = st.column_config.CheckboxColumn("COMI. PAGADA")

edit = st.data_editor(
    view.sort_index(ascending=False)[cols],
    hide_index=True,
    use_container_width=True,
    column_config=column_config,
)
if st.button("💾 GUARDAR CAMBIOS",use_container_width=True,type="primary"):
    # Editamos sobre la base original usando FECHA_REGISTRO+PRODUCTO como referencia visual.
    for i in edit.index:
        match=i if i in view.index else None
        if match is not None:
            for col in ["CLIENTE","ESTADO_PAGO","MONTO_RECIBIDO","COMI_CHECK"]:
                if col in edit.columns and col in df.columns: df.at[match,col]=edit.at[i,col]
            if df.at[match,"ESTADO_PAGO"]=="🟢 Pagado": df.at[match,"MONTO_RECIBIDO"]=df.at[match,"VENTA_MXN"]
    conn.update(data=df)
    st.cache_data.clear(); st.success("Actualizado"); time.sleep(.4); st.rerun()
