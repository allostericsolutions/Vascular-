# screens/user_data_input.py
import streamlit as st
import time
import os # Asegúrate de importar 'os' aquí
from utils.question_manager import select_random_questions, select_short_questions, shuffle_options

def user_data_input():
    """
    Screen for user data input with image on the left.
    """
    image_column, form_column = st.columns([1, 2]) # Divide en dos columnas, ajusta ratios si es necesario

    with image_column:
        image_path = os.path.join("assets", "images", "AllostericSolutions.png")
        st.image(image_path, width=290) # Controla el tamaño con 'width', ajusta el valor

    with form_column:
        with st.form("user_form"):
            st.header("User Data")
            st.warning("Please note: The email address you provide will be associated with the password you used to access this exam. Its use is authorized by the administrator for the purpose communicated to you.")
            nombre = st.text_input("Full Name:")
            email = st.text_input("Email:")

            submitted = st.form_submit_button("Start Exam")
            if submitted:
                if not nombre.strip() or not email.strip(): # Primero, verifica campos no vacíos (como antes)
                    st.error("Please, complete all fields.")
                elif "@" not in email or "." not in email:  # <---- AÑADIDO: VALIDACIÓN SIMPLE DE EMAIL
                    st.error("Please enter a valid email address.") # Mensaje de error más específico
                else:
                    st.session_state.user_data = {
                        "nombre": nombre.strip(),
                        "email": email.strip()
                    }
                    st.success("Data registered. Preparing the exam...")

                    # ───────────────────────────────────────────────
                    # BLOQUE IMPORTANTE: SELECCIÓN DE MODO DE EXAMEN
                    # ───────────────────────────────────────────────
                    exam_type = st.session_state.get("exam_type", "full")
                    if exam_type == "short":
                        selected = select_short_questions(total=20)
                    else:
                        selected = select_random_questions(total=140)

                    st.session_state.selected_questions = selected
                    for q in st.session_state.selected_questions:
                        q['opciones'] = shuffle_options(q)

                    st.session_state.answers = {str(i): None for i in range(len(st.session_state.selected_questions))}
                    st.session_state.start_time = time.time()
                    st.rerun()
