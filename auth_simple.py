import streamlit as st
import re

def require_user():
    if "user_email" in st.session_state:
        return st.session_state["user_email"]

    email = st.text_input("請輸入您的 Email")

    if not email:
        st.stop()

    email = email.strip().lower()

    st.session_state["user_email"] = email
    return email

