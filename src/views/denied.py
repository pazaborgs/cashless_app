import streamlit as st
from utils.components import render_topbar


def render_denied() -> None:
    """Acesso negado — URL inválida ou token incorreto."""
    render_topbar("Acesso Negado", "—")
    st.markdown(
        """
        <div class="access-denied">
            <h3>Acesso não autorizado</h3>
            <p>URL inválida ou token incorreto.
            Verifique o link e tente novamente.
            Em caso de dúvida, acione a supervisão do evento.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
