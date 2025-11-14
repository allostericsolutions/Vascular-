# screens/user_data_input.py
import streamlit as st
import time
import os
from utils.question_manager import select_random_questions, select_short_questions, shuffle_options

def user_data_input():
    """
    Screen for user data input with image on the left.
    """
    image_column, form_column = st.columns([1, 2])  # Divide en dos columnas, ajusta ratios si es necesario

    with image_column:
        image_path = os.path.join("assets", "images", "AllostericSolutions.png")
        st.image(image_path, width=290)  # Controla el tamaño con 'width', ajusta el valor

    with form_column:
        with st.form("user_form"):
            st.header("User Data")

            # Email ya validado en la pantalla de login
            email_guardado = st.session_state.user_data.get("email", "").strip()

            st.warning(
                "Please note: The email address you used to access this exam is recorded and may be used to "
                "investigate misuse of access codes. Its use is authorized by the administrator for the "
                "purpose communicated to you."
            )

            nombre = st.text_input("Full Name:")

            # Mostrar email fijo (no editable)
            st.text_input("Email:", value=email_guardado, disabled=True)

            submitted = st.form_submit_button("Start Exam")
            if submitted:
                if not nombre.strip():
                    st.error("Please, complete your full name.")
                elif not email_guardado:
                    st.error("No email was found for this session. Please log in again.")
                else:
                    # Guardar nombre, conservar email ya existente
                    st.session_state.user_data["nombre"] = nombre.strip()

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

                    st.session_state.answers = {
                        str(i): None for i in range(len(st.session_state.selected_questions))
                    }
                    st.session_state.start_time = time.time()
                    st.rerun()
