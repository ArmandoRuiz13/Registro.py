import streamlit as st
import pandas as pd
import time
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Lolis · Registros Compradoras", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
#MainMenu,footer,header{visibility:hidden}.block-container{padding-top:1rem!important;max-width:1200px}
[data-testid="stButton"] button{border-radius:14px!important;min-height:44px!important;font-weight:700!important}
@media(max-width:700px){.block-container{padding:.5rem .8rem!important}h1{font-size:1.6rem!important}}
</style>""",unsafe_allow_html=True)
CLOUD_NAME="doi81tooh"; API_KEY="245491997239959"
TIPOS=["Tenis","Ropa","Accesorio","Otro"]
conn=st.connection("gsheets",type=GSheetsConnection)

def nav():
    cols=st.columns(4)
    for c,label,page in zip(cols,["➕ Registrar","📋 Online","👩‍💼 Compradoras","💰 Cobranza"],["app.py","pages/Registros_Online.py","pages/Registros_Compradoras.py","pages/Cobranza.py"]):
        with c:
            if st.button(label,use_container_width=True,key="n_"+label): st.switch_page(page)
nav()
st.title("👩‍💼 Registros Compradoras")
st.caption("Pedidos que te hacen compradoras. Esta información se guarda en la hoja CompradoraV, separada de los registros online.")

def num(v):
    try:return float(str(v).replace(',','').replace('$','')) if v not in (None,'') else 0.0
    except:return 0.0

def img(f):
    try:
        r=requests.post(f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload",data={"upload_preset":"ml_default","api_key":API_KEY},files={"file":f.getvalue()},timeout=30)
        return r.json().get("secure_url") if r.status_code==200 else ""
    except:return ""

def read():
    try:
        d=conn.read(worksheet="CompradoraV",ttl=0)
        if d is None:return pd.DataFrame()
        d.columns=[str(c).strip() for c in d.columns]
        if "Venta_Directa_MXN" not in d.columns:d["Venta_Directa_MXN"]=0.0
        if "TIPO_ARTICULO" not in d.columns:d["TIPO_ARTICULO"]="Otro"
        for c in ["ID","Costo_USD","Costo_MXN","Abono","Saldo","Venta_Directa_MXN"]: 
            if c in d.columns:d[c]=pd.to_numeric(d[c],errors='coerce').fillna(0)
        if "Foto_URL" in d.columns:d["Foto_URL"]=d["Foto_URL"].fillna("")
        return d
    except:return pd.DataFrame()

df=read()
with st.container(border=True):
    st.subheader("⚡ Nuevo registro")
    c1,c2,c3=st.columns([1.3,1,1])
    with c1:p=st.text_input("PRODUCTO *",placeholder="Ej. Pulsera")
    with c2:cl=st.text_input("COMPRADORA *",placeholder="Nombre")
    with c3:tipo=st.selectbox("TIPO",TIPOS)
    foto=st.file_uploader("📷 FOTO",type=["jpg","jpeg","png"])
    c1,c2,c3=st.columns(3)
    with c1:u=num(st.text_input("COSTO USD",placeholder="Opcional"))
    with c2:venta=num(st.text_input("COSTO / VENTA MXN *",placeholder="490"))
    with c3:abono=num(st.text_input("ABONO MXN",placeholder="250"))
    if st.button("✅ GUARDAR COMPRADORA",use_container_width=True,type="primary"):
        if not p.strip() or not cl.strip() or venta<=0: st.error("Ingresa producto, compradora y monto.")
        elif abono>venta: st.error("El abono no puede ser mayor al total.")
        else:
            url=img(foto) if foto else ""
            nuevo={"ID":int(df["ID"].max()+1) if not df.empty else 1,"Fecha_Registro":datetime.now().strftime("%d/%m/%Y %H:%M"),"Producto":p.strip(),"TIPO_ARTICULO":tipo,"Cliente":cl.strip(),"Foto_URL":url,"Costo_USD":u,"Costo_MXN":venta,"Abono":abono,"Saldo":max(venta-abono,0),"Entregado":"NO","Liquidado":"SÍ" if abono>=venta else "NO","Fecha_Liquidacion":datetime.now().strftime("%d/%m/%Y") if abono>=venta else "Pendiente","Venta_Directa_MXN":venta}
            df2=pd.concat([df,pd.DataFrame([nuevo])],ignore_index=True)
            conn.update(worksheet="CompradoraV",data=df2); st.cache_data.clear(); st.success("✅ Registro guardado"); time.sleep(.4); st.rerun()

if not df.empty:
    c1,c2=st.columns(2)
    with c1: q=st.text_input("🔎 Buscar",placeholder="Producto o compradora")
    with c2: f=st.selectbox("Mostrar",["Todos","Pendientes","Liquidados"])
    view=df.copy()
    if q:view=view[view.astype(str).apply(lambda r:r.str.contains(q,case=False,na=False).any(),axis=1)]
    if f=="Pendientes":view=view[view["Liquidado"]=="NO"]
    if f=="Liquidados":view=view[view["Liquidado"]=="SÍ"]
    cols=[c for c in ["ID","Fecha_Registro","Producto","TIPO_ARTICULO","Cliente","Foto_URL","Costo_MXN","Abono","Saldo","Entregado","Liquidado","Fecha_Liquidacion","Venta_Directa_MXN"] if c in view.columns]
    edit=st.data_editor(view.sort_index(ascending=False)[cols],hide_index=True,use_container_width=True,column_config={"Foto_URL":st.column_config.ImageColumn("📷 FOTO"),"Costo_MXN":st.column_config.NumberColumn("TOTAL",format="$%.2f"),"Abono":st.column_config.NumberColumn("ABONO",format="$%.2f"),"Saldo":st.column_config.NumberColumn("SALDO",format="$%.2f"),"Venta_Directa_MXN":st.column_config.NumberColumn("VENTA",format="$%.2f"),"Entregado":st.column_config.SelectboxColumn("ENTREGA",options=["SÍ","NO"]),"Liquidado":st.column_config.SelectboxColumn("PAGO",options=["SÍ","NO"])})
    if st.button("💾 GUARDAR CAMBIOS",use_container_width=True,type="primary"):
        for idx in view.index:
            row=edit.loc[idx] if idx in edit.index else None
            if row is not None:
                for c in ["Abono","Entregado","Liquidado"]:
                    if c in row.index:df.at[idx,c]=row[c]
                df.at[idx,"Saldo"]=max(float(df.at[idx,"Costo_MXN"])-float(df.at[idx,"Abono"]),0)
                if df.at[idx,"Liquidado"]=="SÍ":df.at[idx,"Saldo"]=0.0;df.at[idx,"Entregado"]="SÍ";df.at[idx,"Fecha_Liquidacion"]=datetime.now().strftime("%d/%m/%Y")
        conn.update(worksheet="CompradoraV",data=df);st.cache_data.clear();st.success("Actualizado");time.sleep(.4);st.rerun()
