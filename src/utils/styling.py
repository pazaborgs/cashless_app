import os
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_css(theme: str = "light") -> None:
    css_path = os.path.join(BASE_DIR, "styles", f"theme_{theme}.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
