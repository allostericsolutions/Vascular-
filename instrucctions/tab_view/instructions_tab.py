# instrucctions/tab_view/instructions_tab.py
import streamlit as st
from instrucctions.logic.instructions_manager import get_instructions_text

def instructions_tab():
    """
    Renderiza las instrucciones en un expander de Streamlit.
    """
    with st.expander("Instrucciones para el Examen", expanded=False):
        texto = get_instructions_text()
        st.markdown(texto)
