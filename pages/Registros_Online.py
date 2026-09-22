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

# 🔧 FIX: Google Sheets deja la cuadrícula extendida (ej. hasta la fila 1000) aunque
# solo haya datos reales en las primeras filas. conn.read() trae también esas filas
# vacías, y eso hace tronar st.data_editor porque ESTADO_PAGO (SelectboxColumn) y
# COMI_CHECK (CheckboxColumn) no aceptan valores vacíos/NaN fuera de sus opciones.
if not df.empty:
    df = df.dropna(how="all")
    if "PRODUCTO" in df.columns:
        df = df[df["PRODUCTO"].astype(str).str.strip().ne("")]
    df = df.reset_index(drop=True)

if df.empty:
    st.info("No hay registros online.")
    st.stop()

for col,default in [("TIPO_ARTICULO","Otro"),("CLIENTE","N/A"),("FOTO_URL","")]:
    if col not in df.columns: df[col]=default
for c in ["VENTA_MXN","MONTO_RECIBIDO","GANANCIA_MXN","COSTO_TOTAL_MXN"]:
    if c in df.columns: df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)

# 🔧 FIX: normalizar ESTADO_PAGO a una de las opciones válidas del SelectboxColumn
ESTADOS_VALIDOS=["🔴 Debe","🟡 Abonado","🟢 Pagado"]
if "ESTADO_PAGO" in df.columns:
    df["ESTADO_PAGO"]=df["ESTADO_PAGO"].astype(str).str.strip()
    df.loc[~df["ESTADO_PAGO"].isin(ESTADOS_VALIDOS),"ESTADO_PAGO"]="🔴 Debe"
else:
    df["ESTADO_PAGO"]="🔴 Debe"

# 🔧 FIX: COMI_CHECK como booleano real para el CheckboxColumn
if "COMI_CHECK" in df.columns:
    df["COMI_CHECK"]=df["COMI_CHECK"].apply(lambda v: str(v).strip().lower() in ("1","true","sí","si","x","yes"))
else:
    df["COMI_CHECK"]=False

# FOTO_URL y CLIENTE siempre como texto limpio (evita None en ImageColumn/TextColumn)
df["FOTO_URL"]=df["FOTO_URL"].fillna("").astype(str)
df["CLIENTE"]=df["CLIENTE"].fillna("N/A").astype(str)

c1,c2,c3=st.columns(3)
with c1: bus=st.text_input("🔎 Buscar",placeholder="Producto o cliente")
with c2: tipo=st.selectbox("Tipo",["Todos"]+sorted(df["TIPO_ARTICULO"].dropna().astype(str).unique().tolist()))
with c3: estado=st.selectbox("Pago",["Todos"]+ESTADOS_VALIDOS)

view=df.copy()
if bus: view=view[view.astype(str).apply(lambda r:r.str.contains(bus,case=False,na=False).any(),axis=1)]
if tipo!="Todos": view=view[view["TIPO_ARTICULO"]==tipo]
if estado!="Todos" and "ESTADO_PAGO" in view.columns: view=view[view["ESTADO_PAGO"]==estado]

st.write(f"**{len(view)} registros**")
cols=[c for c in ["FECHA_REGISTRO","PRODUCTO","TIPO_ARTICULO","CLIENTE","TIENDA","COSTO_TOTAL_MXN","VENTA_MXN","GANANCIA_MXN","ESTADO_PAGO","MONTO_RECIBIDO","COMI_CHECK","FOTO_URL"] if c in view.columns]
vista_ordenada = view.sort_index(ascending=False)[cols]
edit=st.data_editor(vista_ordenada,hide_index=True,use_container_width=True,column_config={"FOTO_URL":st.column_config.ImageColumn("📷 FOTO"),"COSTO_TOTAL_MXN":st.column_config.NumberColumn("COSTO",format="$%.2f"),"VENTA_MXN":st.column_config.NumberColumn("VENTA",format="$%.2f"),"GANANCIA_MXN":st.column_config.NumberColumn("GANANCIA",format="$%.2f"),"MONTO_RECIBIDO":st.column_config.NumberColumn("RECIBIDO",format="$%.2f"),"ESTADO_PAGO":st.column_config.SelectboxColumn("ESTADO",options=ESTADOS_VALIDOS),"COMI_CHECK":st.column_config.CheckboxColumn("COMI. PAGADA")})
if st.button("💾 GUARDAR CAMBIOS",use_container_width=True,type="primary"):
    # 🔧 FIX: antes se usaba view.index[i] tratando i como POSICIÓN, lo cual guardaba
    # los cambios en la fila equivocada en cuanto había un filtro/búsqueda activo.
    # edit conserva el mismo índice (label) que vista_ordenada, así que usamos ese
    # índice directamente contra df.
    for idx in edit.index:
        if idx in df.index:
            for col in ["CLIENTE","ESTADO_PAGO","MONTO_RECIBIDO","COMI_CHECK"]:
                if col in edit.columns and col in df.columns: df.at[idx,col]=edit.at[idx,col]
            if df.at[idx,"ESTADO_PAGO"]=="🟢 Pagado": df.at[idx,"MONTO_RECIBIDO"]=df.at[idx,"VENTA_MXN"]
    conn.update(data=df)
    st.cache_data.clear(); st.success("Actualizado"); time.sleep(.4); st.rerun()