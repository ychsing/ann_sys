import streamlit as st
import re

def require_user():
    if "user_email" in st.session_state:
        return st.session_state["user_email"]

    st.title("Annotation System Login")

    email = st.text_input("請輸入您的 Email（作為標註身分）")

    if not email:
        st.stop()

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        st.error("Email 格式不正確")
        st.stop()

    st.session_state["user_email"] = email
    return email
