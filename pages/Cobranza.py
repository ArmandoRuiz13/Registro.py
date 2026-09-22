import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Lolis · Cobranza", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
#MainMenu,footer,header{visibility:hidden}.block-container{padding-top:1rem!important;max-width:1100px}
[data-testid="stButton"] button{border-radius:14px!important;min-height:48px!important;font-weight:800!important}
.paycard{border:1px solid #e8e8e8;border-radius:18px;padding:14px;margin-bottom:10px;background:#fff;box-shadow:0 2px 12px rgba(0,0,0,.04)}
@media(max-width:700px){.block-container{padding:.5rem .8rem!important}h1{font-size:1.6rem!important}}
</style>""",unsafe_allow_html=True)
conn=st.connection("gsheets",type=GSheetsConnection)

def nav():
    cols=st.columns(4)
    for c,label,page in zip(cols,["➕ Registrar","📋 Online","👩‍💼 Compradoras","💰 Cobranza"],["app.py","pages/Registros_Online.py","pages/Registros_Compradoras.py","pages/Cobranza.py"]):
        with c:
            if st.button(label,use_container_width=True,key="n_"+label):st.switch_page(page)
nav()
st.title("💰 Cobranza")
st.caption("Un solo lugar para cobrar rápidamente tanto registros online como registros de compradoras.")

def read_online():
    try:
        d=conn.read(ttl=0);d.columns=[str(c).strip() for c in d.columns];return d
    except:return pd.DataFrame()
def read_buy():
    try:
        d=conn.read(worksheet="CompradoraV",ttl=0);d.columns=[str(c).strip() for c in d.columns];return d
    except:return pd.DataFrame()

dfo=read_online();dfc=read_buy()
for c in ["VENTA_MXN","MONTO_RECIBIDO"]:
    if c in dfo.columns:dfo[c]=pd.to_numeric(dfo[c],errors='coerce').fillna(0)
for c in ["Costo_MXN","Abono","Saldo","ID"]:
    if c in dfc.columns:dfc[c]=pd.to_numeric(dfc[c],errors='coerce').fillna(0)

pending_o=dfo[dfo.get("ESTADO_PAGO",pd.Series(index=dfo.index,dtype=str)).isin(["🔴 Debe","🟡 Abonado"])].copy() if not dfo.empty else pd.DataFrame()
pending_c=dfc[dfc.get("Liquidado",pd.Series(index=dfc.index,dtype=str))=="NO"].copy() if not dfc.empty else pd.DataFrame()

t1,t2=st.tabs([f"📋 Online · {len(pending_o)}",f"👩‍💼 Compradoras · {len(pending_c)}"])
with t1:
    if pending_o.empty:st.success("🟢 No hay pagos online pendientes.")
    else:
        q=st.text_input("🔎 Buscar online",placeholder="Producto o cliente",key="qo")
        if q:pending_o=pending_o[pending_o.astype(str).apply(lambda r:r.str.contains(q,case=False,na=False).any(),axis=1)]
        for idx,row in pending_o.sort_index(ascending=False).iterrows():
            producto=row.get("PRODUCTO","Sin producto");cliente=row.get("CLIENTE","N/A");total=float(row.get("VENTA_MXN",0));rec=float(row.get("MONTO_RECIBIDO",0));saldo=max(total-rec,0);estado=row.get("ESTADO_PAGO","🔴 Debe")
            with st.container(border=True):
                c1,c2=st.columns([2.2,1])
                with c1:
                    st.markdown(f"**{producto}**")
                    st.caption(f"👤 {cliente} · {row.get('TIPO_ARTICULO','Otro')} · {row.get('FECHA','')}")
                    st.write(f"Total **${total:,.2f}** · Recibido **${rec:,.2f}** · Falta **${saldo:,.2f}**")
                with c2:
                    if st.button("💵 PAGAR TODO",key=f"po_{idx}",use_container_width=True,type="primary"):
                        dfo.at[idx,"ESTADO_PAGO"]="🟢 Pagado";dfo.at[idx,"MONTO_RECIBIDO"]=total;conn.update(data=dfo);st.cache_data.clear();st.toast("✅ Pago registrado");time.sleep(.4);st.rerun()
with t2:
    if pending_c.empty:st.success("🟢 No hay pagos de compradoras pendientes.")
    else:
        q=st.text_input("🔎 Buscar compradora",placeholder="Producto o nombre",key="qc")
        if q:pending_c=pending_c[pending_c.astype(str).apply(lambda r:r.str.contains(q,case=False,na=False).any(),axis=1)]
        for idx,row in pending_c.sort_values("ID",ascending=False).iterrows():
            producto=row.get("Producto","Sin producto");cliente=row.get("Cliente","N/A");total=float(row.get("Costo_MXN",0));abono=float(row.get("Abono",0));saldo=max(total-abono,0)
            with st.container(border=True):
                c1,c2=st.columns([2.2,1])
                with c1:
                    st.markdown(f"**{producto}**")
                    st.caption(f"👤 {cliente} · ID {int(row.get('ID',0))}")
                    st.write(f"Total **${total:,.2f}** · Abono **${abono:,.2f}** · Falta **${saldo:,.2f}**")
                with c2:
                    if st.button("💵 LIQUIDAR",key=f"pc_{idx}",use_container_width=True,type="primary"):
                        dfc.at[idx,"Liquidado"]="SÍ";dfc.at[idx,"Entregado"]="SÍ";dfc.at[idx,"Saldo"]=0.0;dfc.at[idx,"Fecha_Liquidacion"]=pd.Timestamp.now().strftime("%d/%m/%Y");conn.update(worksheet="CompradoraV",data=dfc);st.cache_data.clear();st.toast("✅ Liquidado");time.sleep(.4);st.rerun()
