import streamlit as st

st.markdown("""<style>
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] { display:none !important; }
</style>""", unsafe_allow_html=True)
st.switch_page("app.py")
