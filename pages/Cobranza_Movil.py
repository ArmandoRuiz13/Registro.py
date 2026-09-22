import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Cobranza Flash", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
<style>
/* Oculta la navegación automática de Streamlit en todas las páginas.
   El menú personalizado de la aplicación sigue visible. */
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] { display:none !important; }

.block-container{padding-top:.5rem!important;padding-bottom:0!important;max-width:400px!important}
header,footer{visibility:hidden}
.img-wrapper{position:relative;width:100%;height:200px;background:#000;border-radius:15px;overflow:hidden;margin-bottom:5px}
.img-wrapper img{width:100%;height:100%;object-fit:contain}
.floating-status{position:absolute;top:10px;right:10px;padding:4px 10px;border-radius:8px;font-size:10px;font-weight:bold;z-index:10;box-shadow:0 2px 5px rgba(0,0,0,.5);text-align:center}
.date-badge{position:absolute;top:40px;right:10px;padding:2px 8px;border-radius:5px;font-size:9px;background:rgba(0,0,0,.7);color:#fff;z-index:10}
.stButton button{border-radius:12px!important;height:3rem!important;font-weight:bold!important}
.nav-col button{background:#262730!important;border:1px solid #444!important;color:#00FFAA!important;font-size:20px!important}
.prod-title{font-size:1rem;font-weight:bold;text-align:center;margin:0;line-height:1.1}.client-text{color:#888;font-size:.9rem;text-align:center;margin:0;display:flex;justify-content:center;align-items:center;gap:5px}.price-text{color:#00FFAA;font-size:1.5rem;font-weight:bold;text-align:center;margin:0}.abono-text{color:#FFCC00;font-size:.8rem;text-align:center;background:rgba(255,204,0,.1);border-radius:5px;margin:2px 0;padding:2px}.preload-img{display:none}
[data-testid="stSidebar"]{min-width:280px;max-width:340px}[data-testid="stSidebarContent"]{padding:.8rem .7rem}[data-testid="stSidebar"] button{min-height:44px;border-radius:12px!important;font-weight:700!important}
@media(max-width:700px){[data-testid="stSidebar"]{min-width:86vw;max-width:88vw}}
</style>
""",unsafe_allow_html=True)

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

def leer_online():
    try:
        df=conn.read(ttl=10);df.columns=[str(c).strip() for c in df.columns];return df
    except Exception:return pd.DataFrame()

def leer_compradoras():
    try:
        df=conn.read(worksheet="CompradoraV",ttl=10);df.columns=[str(c).strip() for c in df.columns];return df
    except Exception:return pd.DataFrame()

online=leer_online()
compradoras=leer_compradoras()

items=[]
if not online.empty and "ESTADO_PAGO" in online.columns:
    p=online[online["ESTADO_PAGO"].isin(["🔴 Debe","🟡 Abonado"])].copy()
    for idx,row in p.iterrows():items.append({"origen":"online","idx":idx,"producto":row.get("PRODUCTO",""),"cliente":row.get("CLIENTE","S/N"),"foto":row.get("FOTO_URL",""),"fecha":row.get("FECHA","S/F"),"estado":"ABONADO" if "Abonado" in str(row.get("ESTADO_PAGO","")) else "DEBE","total":float(pd.to_numeric(row.get("VENTA_MXN",0),errors="coerce") or 0),"abono":float(pd.to_numeric(row.get("MONTO_RECIBIDO",0),errors="coerce") or 0),"saldo":float(pd.to_numeric(row.get("VENTA_MXN",0),errors="coerce") or 0)-float(pd.to_numeric(row.get("MONTO_RECIBIDO",0),errors="coerce") or 0)})
if not compradoras.empty and "Liquidado" in compradoras.columns:
    p=compradoras[compradoras["Liquidado"]=="NO"].copy()
    for idx,row in p.iterrows():items.append({"origen":"compradora","idx":idx,"producto":row.get("Producto",""),"cliente":row.get("Cliente","S/N"),"foto":row.get("Foto_URL",""),"fecha":row.get("Fecha_Registro","S/F"),"estado":"ABONADO" if float(pd.to_numeric(row.get("Abono",0),errors="coerce") or 0)>0 else "DEBE","total":float(pd.to_numeric(row.get("Costo_MXN",0),errors="coerce") or 0),"abono":float(pd.to_numeric(row.get("Abono",0),errors="coerce") or 0),"saldo":float(pd.to_numeric(row.get("Saldo",0),errors="coerce") or 0)})

if not items:
    st.success("¡Todo cobrado! ✨")
    if st.button("🏠 Menú",use_container_width=True):st.switch_page("app.py")
    st.stop()

if "idx_c" not in st.session_state:st.session_state.idx_c=0
if st.session_state.idx_c>=len(items):st.session_state.idx_c=0
reg=items[st.session_state.idx_c]
color_st="#FFCC00" if reg["estado"]=="ABONADO" else "#FF4B4B"
foto=reg["foto"]
url_f=foto if str(foto) not in ("","nan","None") else "https://via.placeholder.com/400x300?text=Sin+Foto"
fecha_val=str(reg["fecha"]).split(" ")[0]

st.markdown(f"<div class='img-wrapper'><div class='floating-status' style='background:{color_st};color:black'>{reg['estado']}</div><div class='date-badge'>📅 {fecha_val}</div><img src='{url_f}?v={st.session_state.idx_c}'></div>",unsafe_allow_html=True)

c1,c2,c3=st.columns([1,.5,1])
def cambiar_indice(delta):
    st.session_state.idx_c=(st.session_state.idx_c+delta)%len(items);time.sleep(.05);st.rerun()
with c1:
    st.markdown('<div class="nav-col">',unsafe_allow_html=True)
    if st.button("❮",key=f"prev_{st.session_state.idx_c}",use_container_width=True):cambiar_indice(-1)
    st.markdown('</div>',unsafe_allow_html=True)
with c2:st.markdown(f"<p style='text-align:center;font-size:11px;margin-top:14px;font-weight:bold;color:#666;'>{st.session_state.idx_c+1}/{len(items)}</p>",unsafe_allow_html=True)
with c3:
    st.markdown('<div class="nav-col">',unsafe_allow_html=True)
    if st.button("❯",key=f"next_{st.session_state.idx_c}",use_container_width=True):cambiar_indice(1)
    st.markdown('</div>',unsafe_allow_html=True)

st.markdown(f"<p class='prod-title'>{reg['producto']}</p>",unsafe_allow_html=True)
st.markdown(f"<p class='client-text'>📱 <b>{reg['cliente'] if str(reg['cliente']) not in ('nan','None','') else 'S/N'}</b> · {'ONLINE' if reg['origen']=='online' else 'COMPRADORA'}</p>",unsafe_allow_html=True)
st.markdown(f"<p class='price-text'>${reg['total']:,.2f}</p>",unsafe_allow_html=True)
if reg["abono"]>0:
    st.markdown(f"<p class='abono-text'>Abonó: ${reg['abono']:,.2f} | Falta: ${reg['saldo']:,.2f}</p>",unsafe_allow_html=True)
else:st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)

with st.popover("✅ PAGAR TODO",use_container_width=True):
    if st.button("CONFIRMAR PAGO",type="primary",use_container_width=True,key=f"pay_{reg['origen']}_{reg['idx']}"):
        if reg["origen"]=="online":
            df=online.copy();df.at[reg["idx"],"ESTADO_PAGO"]="🟢 Pagado";df.at[reg["idx"],"MONTO_RECIBIDO"]=df.at[reg["idx"],"VENTA_MXN"];conn.update(data=df)
        else:
            df=compradoras.copy();df.at[reg["idx"],"Liquidado"]="SÍ";df.at[reg["idx"],"Abono"]=df.at[reg["idx"],"Costo_MXN"];df.at[reg["idx"],"Saldo"]=0.0;df.at[reg["idx"],"Entregado"]="SÍ";df.at[reg["idx"],"Fecha_Liquidacion"]=pd.Timestamp.now().strftime("%d/%m/%Y");conn.update(worksheet="CompradoraV",data=df)
        st.toast("✅ ¡Registrado!");time.sleep(.5);st.cache_data.clear();st.rerun()

preload=[(st.session_state.idx_c-1)%len(items),(st.session_state.idx_c+1)%len(items)]
st.markdown("".join([f"<img src='{items[i]['foto']}' class='preload-img'>" for i in preload if str(items[i]['foto']) not in ('','nan','None')]),unsafe_allow_html=True)
if st.button("🏠 Menú",use_container_width=True):st.switch_page("app.py")
