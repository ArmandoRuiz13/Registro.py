import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Lolis · Registros Online", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
header,footer{visibility:hidden}[data-testid="stSidebar"]{min-width:300px;max-width:360px}[data-testid="stSidebarContent"]{padding:.9rem .75rem}[data-testid="stSidebar"] button{min-height:44px;border-radius:12px!important;font-weight:700!important}@media(max-width:700px){[data-testid="stSidebar"]{min-width:86vw;max-width:88vw}.block-container{padding:.7rem .7rem 1.5rem!important}}
</style>""",unsafe_allow_html=True)
conn=st.connection("gsheets",type=GSheetsConnection)
with st.sidebar:
    st.markdown("# 🛍️ Lolis")
    st.caption("Menú")
    if st.button("📝 Registro",use_container_width=True):st.switch_page("app.py")
    if st.button("📋 Registros Online",use_container_width=True):st.switch_page("pages/Registros_Online.py")
    if st.button("👩‍💼 Registros Compradoras",use_container_width=True):st.switch_page("pages/Registros_Compradoras.py")
    if st.button("💰 Cobranza",use_container_width=True):st.switch_page("pages/Cobranza_Movil.py")

st.title("📋 Registros Online")
st.caption("Compras que tú realizas online. Aquí solo se muestran y editan; el alta se hace desde Registro.")
try:
    df=conn.read(ttl=0);df.columns=[str(c).strip() for c in df.columns]
except Exception:df=pd.DataFrame()
if df.empty:st.info("No hay registros online.");st.stop()
if "TIPO_ARTICULO" not in df.columns:df["TIPO_ARTICULO"]="Otro"
for c in ["VENTA_MXN","MONTO_RECIBIDO","GANANCIA_MXN","COSTO_TOTAL_MXN"]:
    if c in df.columns:df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)
c1,c2,c3=st.columns(3)
with c1:bus=st.text_input("🔎 Buscar",placeholder="Producto o cliente")
with c2:tipo=st.selectbox("Tipo",["Todos","Tenis","Ropa","Accesorio","Otro"])
with c3:estado=st.selectbox("Pago",["Todos","🔴 Debe","🟡 Abonado","🟢 Pagado"])
view=df.copy()
if bus:view=view[view.astype(str).apply(lambda r:r.str.contains(bus,case=False,na=False).any(),axis=1)]
if tipo!="Todos":view=view[view["TIPO_ARTICULO"]==tipo]
if estado!="Todos" and "ESTADO_PAGO" in view.columns:view=view[view["ESTADO_PAGO"]==estado]
cols=[c for c in ["FECHA_REGISTRO","TIPO_ARTICULO","PRODUCTO","CLIENTE","TIENDA","COSTO_TOTAL_MXN","VENTA_MXN","GANANCIA_MXN","ESTADO_PAGO","MONTO_RECIBIDO","COMI_CHECK","FOTO_URL"] if c in view.columns]
edited=st.data_editor(view.sort_index(ascending=False)[cols],hide_index=True,use_container_width=True,column_config={"TIPO_ARTICULO":st.column_config.SelectboxColumn("TIPO",options=["Tenis","Ropa","Accesorio","Otro"]),"FOTO_URL":st.column_config.ImageColumn("📷 FOTO"),"COSTO_TOTAL_MXN":st.column_config.NumberColumn("COSTO",format="$%.2f"),"VENTA_MXN":st.column_config.NumberColumn("VENTA",format="$%.2f"),"GANANCIA_MXN":st.column_config.NumberColumn("GANANCIA",format="$%.2f"),"MONTO_RECIBIDO":st.column_config.NumberColumn("RECIBIDO",format="$%.2f"),"ESTADO_PAGO":st.column_config.SelectboxColumn("ESTADO",options=["🔴 Debe","🟡 Abonado","🟢 Pagado"]),"COMI_CHECK":st.column_config.CheckboxColumn("COMI. PAGADA")})
if st.button("💾 GUARDAR CAMBIOS",use_container_width=True,type="primary"):
    for idx in edited.index:
        for c in ["CLIENTE","TIPO_ARTICULO","ESTADO_PAGO","MONTO_RECIBIDO","COMI_CHECK"]:
            if c in edited.columns:df.at[idx,c]=edited.at[idx,c]
        if df.at[idx,"ESTADO_PAGO"]=="🟢 Pagado":df.at[idx,"MONTO_RECIBIDO"]=df.at[idx,"VENTA_MXN"]
    st.cache_data.clear();conn.update(data=df);st.success("Actualizado");time.sleep(.5);st.rerun()
