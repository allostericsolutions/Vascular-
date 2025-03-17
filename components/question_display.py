# components/question_display.py
import streamlit as st
import os

def display_question(question, question_num):
  """
  Displays the question statement, image (if it exists), and options.
  """
  col1, col2 = st.columns([1, 3])
  with col1:
    st.subheader(f"Question {question_num}:")
  with col2:
    st.subheader("SPI Practice Exam - ARDMS")

  with st.container():
    st.write(question['enunciado'])

  with st.container():
    if question['image']:
      image_path = os.path.join("assets", "images", question['image'])
      try:
        # --- CAMBIO AQUÍ: Envuelve st.image y el enlace en un div ---
        st.markdown(f'<div class="image-container">', unsafe_allow_html=True)
        st.image(image_path) # Eliminado use_container_width=True
        st.markdown(f'<a href="{image_path}" target="_blank">Ver imagen en pestaña nueva</a>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)  # Cierra el div
        # ------------------------------------------------------------
      except FileNotFoundError:
        st.error(f"Image not found: {image_path}")

  with st.container():
    existing_answer = st.session_state.answers.get(str(question_num - 1), None)

    if existing_answer is not None and existing_answer in question['opciones']:
      selected_index = question['opciones'].index(existing_answer)
    else:
      selected_index = None

    stable_key = f"respuesta_{question_num}"

    # --- MODIFICACIÓN AQUÍ ---
    labeled_options = [f"{chr(97 + i)}) {option}" for i, option in enumerate(question['opciones'])]
    # --- FIN DE LA MODIFICACIÓN ---

    selected = st.radio(
      "Select an answer:",
      options=labeled_options,  # Usamos las opciones con letras
      index=selected_index,
      key=stable_key
    )

    # --- MODIFICACIÓN AQUÍ ---
    # Necesitamos obtener la opción original, sin la letra, para almacenarla correctamente
    if selected:
      selected_option_index = ord(selected[0]) - 97  # Obtener el índice de la letra
      original_selected_option = question['opciones'][selected_option_index]
    else:
        original_selected_option = None
    st.session_state.answers[str(question_num - 1)] = original_selected_option
    # --- FIN DE LA MODIFICACIÓN ---
