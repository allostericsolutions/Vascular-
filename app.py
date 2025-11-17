import streamlit as st
import json
import time
import os
import random

# Importamos nuestras utilerías y componentes
from utils.auth import verify_password, generate_access_code
from utils.question_manager import select_random_questions, shuffle_options, calculate_score
from utils.pdf_generator import generate_pdf
from components.question_display import display_question
from components.navigation import display_navigation
from openai_utils.explanations import get_openai_explanation
from screens.user_data_input import user_data_input  # Se importa la función extraída

# ─────────────────────────────────────────────────────────────
# NUEVO IMPORT para las instrucciones
# ─────────────────────────────────────────────────────────────
from instrucctions.tab_view.instructions_tab import instructions_tab
# ─────────────────────────────────────────────────────────────

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="ARDMS RVT Login",
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
    if 'selected_questions' not in st.session_state:
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
    if 'unanswered_questions' not in st.session_state:
        st.session_state.unanswered_questions = []


# ─────────────────────────────────────────────────────────────
# Generador de código de acceso (solo administrador)
# ─────────────────────────────────────────────────────────────
def access_code_generator():
    """
    UI para generar un código de acceso basado en email.
    Protegido con contraseña de administrador.
    La base se elige al azar según el tipo de examen (full / short).
    Permite especificar la fecha del examen (por defecto, hoy).
    """
    st.subheader("Generate student access code (administrator only)")

    with st.form("generator_form"):
        admin_pass = st.text_input(
            "Admin password for token generation:",
            type="password",
            key="gen_admin_pass"
        )
        gen_email = st.text_input("Student email for this exam:", key="gen_email")

        exam_type_choice = st.selectbox(
            "Exam type:",
            options=["Full", "Short"],
            index=0,
            key="gen_exam_type"
        )

        # Fecha del examen (por defecto, hoy)
        exam_date = st.date_input(
            "Exam date (token will only work on this date):",
            key="gen_exam_date"
        )

        submitted = st.form_submit_button("Generate access code")

    if submitted:
        # 1) Validar contraseña de administrador del generador
        expected_admin_pass = config.get("token_generator_password", "")
        if not expected_admin_pass:
            st.error("Configuration error: 'token_generator_password' is not set in config.json.")
            return

        if admin_pass != expected_admin_pass:
            st.error("Invalid admin password.")
            return

        # 2) Validar email
        if not gen_email.strip():
            st.error("Please enter the student's email.")
            return

        # 3) Elegir base al azar según tipo de examen
        if exam_type_choice == "Full":
            bases = config.get("passwords_full_base", [])
        else:
            bases = config.get("passwords_short_base", [])

        if not bases:
            st.error("No base codes configured for this exam type.")
            return

        base_code = random.choice(bases)

        # 4) Convertir exam_date a 'YYYY-MM-DD'
        try:
            date_str = exam_date.strftime("%Y-%m-%d")
        except Exception as e:
            st.error(f"Invalid exam date: {e}")
            return

        # 5) Generar token usando la fecha elegida
        try:
            token = generate_access_code(gen_email, base_code, date_str=date_str)
        except Exception as e:
            st.error(f"Error generating access code: {e}")
            return

        # 6) Mostrar token para que TÚ se lo des al alumno
        st.success(f"Access code generated for this student ({exam_type_choice}) for {date_str}:")
        st.code(token)
        st.info(
            "Send this access code to the student. "
            "They must use it with the same email, and it will only work on the specified date."
        )


def authentication_screen():
    """
    Authentication screen: asks for email + access code.
    La sección de administrador solo aparece si la URL incluye ?admin=1.
    """
    st.title("ARDMS RVT Login")

    # -------------------------------
    # Login normal para el alumno
    # -------------------------------
    st.subheader("Enter your email and access code")

    email = st.text_input("Email used to generate your access code:")
    token = st.text_input("Access code:", type="password")

    if st.button("Enter"):
        if not email.strip() or not token.strip():
            st.error("Please enter both email and access code.")
        else:
            if verify_password(token, email):
                st.session_state.authenticated = True

                # Guardar el email ya desde aquí
                if "user_data" not in st.session_state or not isinstance(st.session_state.user_data, dict):
                    st.session_state.user_data = {}
                st.session_state.user_data["email"] = email.strip()

                st.success("Authentication successful.")
                st.rerun()
            else:
                st.error("Invalid email or access code.")

    # -------------------------------
    # Sección de administrador (oculta salvo ?admin=1)
    # -------------------------------
    params = st.experimental_get_query_params()
    is_admin_view = params.get("admin", ["0"])[0] == "1"

    if is_admin_view:
        st.markdown("---")
        st.caption("Administrator section – students should ignore this area.")

        with st.expander("Administrator: Generate student access code", expanded=False):
            access_code_generator()


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


def display_unanswered_questions_sidebar():
    """
    Muestra una lista de preguntas sin responder en la barra lateral, organizadas en filas de 3 columnas.
    Cada pregunta sin responder se presenta como un botón para navegar a ella.
    """
    unanswered_indices = []

    if 'answers' not in st.session_state or 'selected_questions' not in st.session_state:
        return

    for i in range(len(st.session_state.selected_questions)):
        if st.session_state.answers.get(str(i)) is None:
            unanswered_indices.append(i)

    if unanswered_indices:
        st.sidebar.subheader("Unanswered Questions")

        for i in range(0, len(unanswered_indices), 3):
            current_group_indices = unanswered_indices[i:i+3]
            cols = st.sidebar.columns(3)

            for j, index in enumerate(current_group_indices):
                question_number = index + 1
                with cols[j]:
                    if st.button(f"Q {question_number}", key=f"goto_unanswered_{index}"):
                        st.session_state.current_question_index = index
                        st.rerun()


def exam_screen():
    """
    Main exam screen.
    """
    nombre = st.session_state.user_data.get('nombre', '')
    email = st.session_state.user_data.get('email', '')

    # Por si acaso, garantizar que start_time está inicializado
    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()

    # Mostramos Name y Email en la barra lateral
    with st.sidebar:
        st.write("User Information")
        st.text_input("Name", value=nombre, disabled=True)
        st.text_input("Email", value=email, disabled=True)

        display_marked_questions_sidebar()
        display_unanswered_questions_sidebar()

    # Determinar tiempo límite según tipo de examen
    exam_type = st.session_state.get("exam_type", "full")  # 'full' por defecto
    if exam_type == "short":
        exam_time_limit_seconds = config.get("time_limit_seconds_short")
    elif exam_type == "full":
        exam_time_limit_seconds = config.get("time_limit_seconds")
    else:
        exam_time_limit_seconds = config.get("time_limit_seconds", 7200)

    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = exam_time_limit_seconds - elapsed_time
    minutes_remaining = max(0, int(remaining_time // 60))

    # Guardar minutos restantes en sesión para uso en el encabezado de la pregunta
    st.session_state["minutes_remaining"] = minutes_remaining

    if remaining_time <= config["warning_time_seconds"] and remaining_time > 0:
        st.warning("The exam will end in 10 minutes!")

    if remaining_time <= 0 and not st.session_state.end_exam:
        st.session_state.end_exam = True
        st.success("Time is up. The exam will be finalized now.")
        # Aquí también debemos usar st.rerun() en lugar de llamar a finalize_exam()
        st.rerun() # CAMBIO CLAVE: Rerun en lugar de llamar a finalize_exam directamente
        return

    if not st.session_state.end_exam:
        current_index = st.session_state.current_question_index
        question = st.session_state.selected_questions[current_index]
        display_question(question, current_index + 1)
        display_navigation()

        if 'confirm_finish' not in st.session_state:
            st.session_state.confirm_finish = False

        with st.form("finish_form"):
            st.warning("When you are ready to finish the exam, press 'Confirm Completion' and then conclude by pressing 'Finish Exam'.")

            col1, col2 = st.columns(2)

            with col1:
                confirm_clicked = st.form_submit_button("Confirm Completion")
            with col2:
                finish_clicked = st.form_submit_button("Finish Exam")

            if confirm_clicked:
                st.session_state.confirm_finish = True

            if finish_clicked:
                if st.session_state.confirm_finish:
                    st.info("⏳ Please wait a few seconds while we prepare your score and performance report. When ready, you will see 'Results generated in PDF' and be able to download your report.")
                    st.session_state.end_exam = True
                    # CAMBIO CLAVE: Rerun en lugar de llamar a finalize_exam directamente
                    st.rerun()
                else:
                    st.warning("Please confirm completion using the button above.")


def finalize_exam():
    """
    Marks the exam as finished, displays results, and generates the PDF.
    """
    # Esta función ahora será llamada desde main() cuando el estado end_exam sea True
    # Ya no necesita establecer end_exam = True aquí, pero no hace daño dejarlo.
    st.session_state.end_exam = True
    score = calculate_score()

    if score >= config["passing_score"]:
        status = "Passed"
    else:
        status = "Not Passed"

    st.header("Exam Results")
    st.write(f"Score Obtained: {score}")
    st.write(f"Status: {status}")

    if "classification_stats" in st.session_state:
        st.sidebar.subheader("Detailed Breakdown by Topic")
        for clasif, stats in st.session_state.classification_stats.items():
            if stats["total"] > 0:
                percent = (stats["correct"] / stats["total"]) * 100
            else:
                percent = 0.0
            st.sidebar.write(f"{clasif}: {percent:.2f}%")

    explanations = get_openai_explanation(st.session_state.incorrect_answers)
    st.session_state.explanations = explanations

    pdf_path = generate_pdf(st.session_state.user_data, score, status)
    st.success("Results generated in PDF.")

    with open(pdf_path, "rb") as f:
        # Este st.download_button() ahora se ejecutará fuera del contexto de un formulario.
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

    # Control de tamaño de fuente
    with st.sidebar:
        st.write("Adjust Font Size")
        font_size_multiplier = st.slider(
            "Font Size",
            min_value=0.8,
            max_value=2.0,
            value=1.0,
            step=0.1,
            key="font_size_slider"
        )

    st.markdown(f"""
        <style>
          :root {{
           --base-font-size: {16 * font_size_multiplier}px;
          }}
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.authenticated:
        instructions_tab()
        authentication_screen()
    # Usamos presencia de 'nombre' como criterio para pasar a examen
    elif not st.session_state.user_data.get("nombre"):
        instructions_tab()
        user_data_input()
    elif not st.session_state.end_exam:
        main_screen()
    else:
        # CAMBIO CLAVE: finalize_exam() se llama aquí directamente cuando el examen ha terminado
        finalize_exam()


if __name__ == "__main__":
    main()
