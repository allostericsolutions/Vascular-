
import streamlit as st
import os
from datetime import datetime

def display_question(question, question_num):
    """
    Displays the question statement, image (if it exists), and options.
    """
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.subheader(f"Question {question_num}:")
    with col2:
        st.subheader("RVT Practice Exam - ARDMS")
    with col3:
        minutes_remaining = st.session_state.get("minutes_remaining")
        if minutes_remaining is not None:
            st.markdown(
                f"""
                <div style='text-align: right; font-size: 20px; color: red;'>
                    <strong>Minutes Remaining:</strong> {minutes_remaining}
                </div>
                """,
                unsafe_allow_html=True
            )

    with st.container():
        st.write(question['enunciado'])

    with st.container():
        image_name = (question.get('image') or "").strip()
        if image_name:
            image_path = os.path.join("assets", "images", image_name)
            if os.path.exists(image_path):
                try:
                    st.markdown('<div class="image-container">', unsafe_allow_html=True)
                    st.image(image_path) 
                    st.markdown('</div>', unsafe_allow_html=True)
                except Exception:
                    st.warning("Image could not be displayed. Please continue the exam and report this issue.")
            else:
                st.warning("Image file not found. Please continue the exam and report this issue.")

    with st.container():
        existing_answer = st.session_state.answers.get(str(question_num - 1), None)
        
        if existing_answer is not None and existing_answer in question['opciones']:
            selected_index = question['opciones'].index(existing_answer)
        else:
            selected_index = None

        stable_key = f"respuesta_{question_num}"

        labeled_options = [f"{chr(97 + i)}) {option}" for i, option in enumerate(question['opciones'])]

        selected = st.radio(
            "Select an answer:",
            options=labeled_options,
            index=selected_index,
            key=stable_key
        )

        if selected:
            selected_option_index = ord(selected[0]) - 97
            original_selected_option = question['opciones'][selected_option_index]
            
            if existing_answer != original_selected_option:
                user_email = st.session_state.user_data.get("email", "Desconocido")
                timestamp = datetime.now().strftime("%H:%M:%S")
                es_correcta = original_selected_option in question["respuesta_correcta"]
                status_txt = "CORRECTO" if es_correcta else "INCORRECTO"
                print(f"[{timestamp}] {user_email} | P{question_num} | {status_txt} | Respondió: {original_selected_option[:50]}...")
        else:
            original_selected_option = None
            
