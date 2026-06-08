import streamlit as st
from datetime import datetime


def render_topbar(module_label: str, operator: str) -> None:
    now = datetime.now().strftime("%d/%m/%Y  %H:%M")
    st.markdown(
        f"""
        <div class="topbar">
            <div class="brand">CASHLESS<span> APP</span></div>
            <div style="display:flex;gap:2rem;align-items:center;">
                <div class="meta">MÓDULO: {module_label.upper()}</div>
                <div class="meta">OPERADOR: {operator.upper()}</div>
                <div class="meta">{now}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ADD Theme Toggle
