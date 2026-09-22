import streamlit as st
import pandas as pd
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Lolis · Registros Compradoras", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
header,footer{visibility:hidden}
[data-testid="stSidebar"]{min-width:300px;max-width:360px}
[data-testid="stSidebarContent"]{padding:.9rem .75rem}
[data-testid="stSidebar"] button{min-height:44px;border-radius:12px!important;font-weight:700!important}
@media(max-width:700px){[data-testid="stSidebar"]{min-width:86vw;max-width:88vw}.block-container{padding:.7rem .7rem 1.5rem!important}h1{font-size:1.55rem!important}}
</style>
""", unsafe_allow_html=True)

conn=st.connection("gsheets",type=GSheetsConnection)

def nav():
    with st.sidebar:
        st.markdown("# 🛍️ Lolis")
        st.caption("Menú")
        if st.button("📝 Registro",use_container_width=True):st.switch_page("app.py")
        if st.button("📋 Registros Online",use_container_width=True):st.switch_page("pages/Registros_Online.py")
        if st.button("👩‍💼 Registros Compradoras",use_container_width=True):st.switch_page("pages/Registros_Compradoras.py")
        if st.button("💰 Cobranza",use_container_width=True):st.switch_page("pages/Cobranza_Movil.py")
nav()

st.title("👩‍💼 Registros Compradoras")
st.caption("Aquí solo se muestran y editan los registros existentes de compradoras. Para crear uno nuevo usa Registro → Compra Compradora.")

try:
    df=conn.read(worksheet="CompradoraV",ttl=0)
    df.columns=[str(c).strip() for c in df.columns]
except Exception:
    df=pd.DataFrame()

if df.empty:
    st.info("No hay registros de compradoras.")
    st.stop()

if "TIPO_ARTICULO" not in df.columns:df["TIPO_ARTICULO"]="Otro"
if "Foto_URL" in df.columns:df["Foto_URL"]=df["Foto_URL"].fillna("")
for c in ["ID","Costo_USD","Costo_MXN","Abono","Saldo","Venta_Directa_MXN"]:
    if c in df.columns:df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)

c1,c2=st.columns(2)
with c1:q=st.text_input("🔎 Buscar",placeholder="Producto o compradora")
with c2:f=st.selectbox("Mostrar",["Todos","Pendientes","Liquidados"])
view=df.copy()
if q:view=view[view.astype(str).apply(lambda r:r.str.contains(q,case=False,na=False).any(),axis=1)]
if f=="Pendientes" and "Liquidado" in view.columns:view=view[view["Liquidado"]=="NO"]
if f=="Liquidados" and "Liquidado" in view.columns:view=view[view["Liquidado"]=="SÍ"]

cols=[c for c in ["ID","Fecha_Registro","TIPO_ARTICULO","Producto","Cliente","Foto_URL","Costo_USD","Costo_MXN","Abono","Saldo","Entregado","Liquidado","Fecha_Liquidacion","Venta_Directa_MXN"] if c in view.columns]
edited=st.data_editor(view.sort_index(ascending=False)[cols],hide_index=True,use_container_width=True,column_config={
    "TIPO_ARTICULO":st.column_config.SelectboxColumn("TIPO",options=["Tenis","Ropa","Accesorio","Otro"]),
    "Foto_URL":st.column_config.ImageColumn("🖼️ FOTO"),
    "Costo_MXN":st.column_config.NumberColumn("PRECIO FINAL",format="$%.2f"),
    "Venta_Directa_MXN":st.column_config.NumberColumn("VENTA MXN",format="$%.2f"),
    "Abono":st.column_config.NumberColumn("ABONO",format="$%.2f"),
    "Saldo":st.column_config.NumberColumn("SALDO",format="$%.2f",disabled=True),
    "Liquidado":st.column_config.SelectboxColumn("LIQ.",options=["SÍ","NO"]),
    "Entregado":st.column_config.SelectboxColumn("ENTR.",options=["SÍ","NO"]),
    "Costo_USD":st.column_config.NumberColumn("USD",format="$%.2f")
})

if st.button("💾 GUARDAR CAMBIOS EN TABLA",use_container_width=True,type="primary"):
    for idx in edited.index:
        df.at[idx,"TIPO_ARTICULO"]=edited.at[idx,"TIPO_ARTICULO"]
        df.at[idx,"Abono"]=edited.at[idx,"Abono"]
        df.at[idx,"Entregado"]=edited.at[idx,"Entregado"]
        df.at[idx,"Liquidado"]=edited.at[idx,"Liquidado"]
        df.at[idx,"Saldo"]=max(float(df.at[idx,"Costo_MXN"])-float(df.at[idx,"Abono"]),0)
        if df.at[idx,"Liquidado"]=="SÍ":
            df.at[idx,"Saldo"]=0.0
            df.at[idx,"Entregado"]="SÍ"
            df.at[idx,"Fecha_Liquidacion"]=datetime.now().strftime("%d/%m/%Y")
    conn.update(worksheet="CompradoraV",data=df)
    st.cache_data.clear();st.success("¡Actualizado!");time.sleep(.5);st.rerun()
