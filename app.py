import streamlit as st
import json
import time
import os

# Importamos nuestras utilerías y componentes
from utils.auth import verify_password
from utils.question_manager import select_random_questions, shuffle_options, calculate_score
from utils.pdf_generator import generate_pdf
from components.question_display import display_question
from components.navigation import display_navigation
from openai_utils.explanations import get_openai_explanation
from screens.user_data_input import user_data_input # Se importa la función extraída

# ─────────────────────────────────────────────────────────────
# NUEVO IMPORT para las instrucciones
# ─────────────────────────────────────────────────────────────
from instrucctions.tab_view.instructions_tab import instructions_tab
# ─────────────────────────────────────────────────────────────

# Configuración de la página de Streamlit
st.set_page_config(
  page_title="RVT Practice Exam - ARDMS",
  layout="centered",
  initial_sidebar_state="collapsed",
)

def load_css():
  """Carga el archivo CSS personalizado."""
  with open("assets/styles/custom.css", "r") as f:
   st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def load_config():
  """
  Loads the data/config.json file.
  """
  with open('data/config.json', 'r', encoding='utf-8') as f:
   return json.load(f)

config = load_config()

def initialize_session():
  """
  Initializes the application's state variables (Session State).
  """
  if 'authenticated' not in st.session_state:
   st.session_state.authenticated = False
  if 'user_data' not in st.session_state:
   st.session_state.user_data = {}
  # --- CORRECCIÓN DE TYPO Y ADICIÓN DE 'unanswered_questions' ---
  if 'selected_questions' not in st.session_state: # Corregido 'not not in'
   st.session_state.selected_questions = []
  if 'current_question_index' not in st.session_state:
   st.session_state.current_question_index = 0
  if 'answers' not in st.session_state:
   st.session_state.answers = {}
  if 'marked' not in st.session_state:
   st.session_state.marked = set()
  if 'start_time' not in st.session_state:
   st.session_state.start_time = None
  if 'end_exam' not in st.session_state:
   st.session_state.end_exam = False
  if 'incorrect_answers' not in st.session_state:
   st.session_state.incorrect_answers = []
  if 'explanations' not in st.session_state:
   st.session_state.explanations = {}
  # --- NUEVO: Inicialización para preguntas no respondidas ---
  if 'unanswered_questions' not in st.session_state:
   st.session_state.unanswered_questions = []
  # --- FIN NUEVO ---

def authentication_screen():
  """
  Authentication screen: prompts the user for the password.
  """
  with st.container():
   st.title("Authentication")
   password = st.text_input("Enter the password to access the exam:", type="password")
   if st.button("Enter"):
     if verify_password(password):
      st.session_state.authenticated = True
      st.success("Authentication successful.")
      st.rerun()
     else:
      st.error("Incorrect password.")

def display_marked_questions_sidebar():
  """Displays the sidebar with marked questions."""
  if st.session_state.marked:
   st.markdown("""
   <style>
   .title {
     writing-mode: vertical-rl;
     transform: rotate(180deg);
     position: absolute;
     top: 50%;
     left: 0px;
     transform-origin: center;
     white-space: nowrap;
     display: block;
     font-size: 1.2em;
   }
   </style>
   """, unsafe_allow_html=True)

   for index in st.session_state.marked:
     question_number = index + 1
     col1, col2 = st.sidebar.columns([3, 1])
     with col1:
      if st.button(f"Question {question_number}", key=f"goto_{index}"):
        st.session_state.current_question_index = index
        st.rerun()
     with col2:
      if st.button("X", key=f"unmark_{index}"):
        st.session_state.marked.remove(index)
        st.rerun()

# --- FUNCIÓN AÑADIDA: Muestra preguntas sin responder ---
def display_unanswered_questions_sidebar():
  """
  Muestra una lista de preguntas sin responder en la barra lateral, organizadas en filas de 3 columnas.
  Cada pregunta sin responder se presenta como un botón para navegar a ella.
  """
  unanswered_indices = []
   
  # Asegurarse de que las claves de session_state existen y están inicializadas
  if 'answers' not in st.session_state or 'selected_questions' not in st.session_state:
    return # No se puede proceder si el estado no está listo

  # st.session_state.answers es un dict como {'0': 'Respuesta A', '1': None, '2': 'Respuesta C'}
  # st.session_state.selected_questions es la lista de diccionarios de preguntas
   
  # Iterar sobre todos los índices de preguntas posibles (de 0 a N-1)
  for i in range(len(st.session_state.selected_questions)):
    # Comprobar si la respuesta para este índice es None o no está presente en el diccionario
    # La clave en st.session_state.answers es la representación en string del índice (ej: '0', '1', ...)
    if st.session_state.answers.get(str(i)) is None:
      unanswered_indices.append(i)

  # Si hay preguntas sin responder, mostrarlas en la barra lateral
  if unanswered_indices:
    # --- Título en inglés ---
    st.sidebar.subheader("Unanswered Questions")
    # --- Fin Título ---
     
    # Procesar las preguntas sin responder en grupos de 3 para filas
    # Usamos un bucle que avanza de 3 en 3
    for i in range(0, len(unanswered_indices), 3):
      # Tomamos un grupo de hasta 3 índices
      current_group_indices = unanswered_indices[i:i+3]
       
      # Creamos 3 columnas para esta fila
      cols = st.sidebar.columns(3)
       
      # Iteramos sobre las columnas y los índices del grupo actual
      for j, index in enumerate(current_group_indices):
        question_number = index + 1
        # Colocamos el botón en la columna correspondiente (cols[j])
        with cols[j]:
          if st.button(f"Q {question_number}", key=f"goto_unanswered_{index}"):
            st.session_state.current_question_index = index
            st.rerun() # Recarga la aplicación para mostrar la pregunta seleccionada
# --- FIN FUNCIÓN ---


def exam_screen():
  """
  Main exam screen.
  """
  nombre = st.session_state.user_data.get('nombre', '')
  email = st.session_state.user_data.get('email', '')

  # Mostramos Name y Email en la barra lateral
  with st.sidebar:
   st.write("User Information")
   st.text_input("Name", value=nombre, disabled=True)
   st.text_input("Email", value=email, disabled=True)

   # --- AÑADIDO: Llamada a la función para mostrar preguntas sin responder ---
   display_marked_questions_sidebar()
   display_unanswered_questions_sidebar() # <-- Esta línea se añadió
   # --- FIN AÑADIDO ---

  # Resto de la pantalla principal: tiempo, preguntas, etc.
  # --- DETERMINAR TIEMPO LÍMITE SEGÚN TIPO DE EXAMEN ---
  exam_type = st.session_state.get("exam_type", "full") # 'full' por defecto si no está definido
  if exam_type == "short":
   exam_time_limit_seconds = config.get("time_limit_seconds_short")
  elif exam_type == "full":
   exam_time_limit_seconds = config.get("time_limit_seconds")
  else: # Tipo de examen desconocido (por si acaso)
   exam_time_limit_seconds = config.get("time_limit_seconds", 7200) # Valor por defecto si no encuentra la clave

  elapsed_time = time.time() - st.session_state.start_time
  remaining_time = exam_time_limit_seconds - elapsed_time
  minutes_remaining = max(0, int(remaining_time // 60)) # Asegurar no sea negativo
  st.markdown(
   f"""
   <div style='text-align: right; font-size: 16px;'>
     <strong>Minutes Remaining:</strong> {minutes_remaining}
   </div>
   """,
   unsafe_allow_html=True
  )

  if remaining_time <= config["warning_time_seconds"] and remaining_time > 0:
   st.warning("The exam will end in 10 minutes!")

  if remaining_time <= 0 and not st.session_state.end_exam:
   st.session_state.end_exam = True
   st.success("Time is up. The exam will be finalized now.")
   finalize_exam()
   return

  # Ya no es necesario llamar a display_marked_questions_sidebar() aquí, se llama dentro del with st.sidebar:
  # display_marked_questions_sidebar()

  if not st.session_state.end_exam:
   current_index = st.session_state.current_question_index
   question = st.session_state.selected_questions[current_index]
   display_question(question, current_index + 1)
   display_navigation()

   # --- BLOQUE DE FINALIZACIÓN (CON FORMULARIO) ---
   if 'confirm_finish' not in st.session_state:
     st.session_state.confirm_finish = False

   with st.form("finish_form"):
     st.warning("When you are ready to finish the exam, press 'Confirm Completion' and then conclude by pressing 'Finish Exam'.")
     if st.form_submit_button("Confirm Completion"):
      st.session_state.confirm_finish = True

   if st.button("Finish Exam"):
     if st.session_state.confirm_finish:
      st.info("⏳ Please wait a few seconds while we prepare your score and performance report. When ready, you will see 'Results generated in PDF' and be able to download your report.") # <---- MENSAJE DE ESPERA CON ICONO ⏳
      st.session_state.end_exam = True
      finalize_exam()
     else:
      st.warning("Please confirm completion using the button above.")

   # --- FIN DEL BLOQUE CON FORMULARIO ---

def finalize_exam():
  """
  Marks the exam as finished, displays results, and generates the PDF.
  """
  st.session_state.end_exam = True
  score = calculate_score()

  if score >= config["passing_score"]:
   status = "Passed"
  else:
   status = "Not Passed"

  st.header("Exam Results")
  st.write(f"Score Obtained: {score}")
  st.write(f"Status: {status}")

  # ──────────────────────────────────────────────────────────
  # NUEVO BLOQUE: Mostrar desglose por clasificación
  # ──────────────────────────────────────────────────────────
  if "classification_stats" in st.session_state:
   st.sidebar.subheader("Detailed Breakdown by Topic")
   for clasif, stats in st.session_state.classification_stats.items():
     if stats["total"] > 0:
      percent = (stats["correct"] / stats["total"]) * 100
     else:
      percent = 0.0
     st.sidebar.write(f"{clasif}: {percent:.2f}%")

  # --- INTEGRACIÓN CON OPENAI ---
  explanations = get_openai_explanation(st.session_state.incorrect_answers)
  st.session_state.explanations = explanations # Guarda las explicaciones

  # Mostrar las explicaciones en la barra lateral (para depurar)
  # st.sidebar.write("Respuestas incorrectas:", st.session_state.incorrect_answers)
  # st.sidebar.write("Explicaciones de OpenAI:", st.session_state.explanations)

  pdf_path = generate_pdf(st.session_state.user_data, score, status)
  st.success("Results generated in PDF.")

  with open(pdf_path, "rb") as f:
   st.download_button(
     label="Download Results (PDF)",
     data=f,
     file_name=os.path.basename(pdf_path),
     mime="application/pdf"
   )

def main_screen():
  """
  Screen that calls exam_screen() if the exam has not finished.
  """
  exam_screen()

def main():
  """
  MAIN EXECUTION.
  """
  initialize_session()
  load_css()
  # ─────────────────────────────────────────────────────────
  # LLAMADO para mostrar las instrucciones (Expander)
  # ─────────────────────────────────────────────────────────
  instructions_tab()

  # --- Control de tamaño de fuente (AÑADIDO) ---
  with st.sidebar:
   st.write("Adjust Font Size")
   font_size_multiplier = st.slider(
     "Font Size",
     min_value=0.8,
     max_value=2.0,
     value=1.0, # Valor inicial (1.0 = tamaño predeterminado)
     step=0.1,
     key="font_size_slider"
   )

  # Inyectar CSS para aplicar el tamaño de fuente (AÑADIDO)
  st.markdown(f"""
   <style>
     :root {{
      --base-font-size: {16 * font_size_multiplier}px; /* Tamaño base dinámico */
     }}
   </style>
  """, unsafe_allow_html=True)


  if not st.session_state.authenticated:
   authentication_screen()
  elif not st.session_state.user_data:
   user_data_input()
  elif not st.session_state.end_exam:
   main_screen()
  else:
   finalize_exam()

if __name__ == "__main__":
  main()
