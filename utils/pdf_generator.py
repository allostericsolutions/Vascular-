import os
import textwrap
import streamlit as st
from datetime import datetime
from fpdf import FPDF

def to_latin1(s: str) -> str:
    """
    Reemplaza caracteres fuera de rango Latin-1
    por '?' para evitar UnicodeEncodeError.
    """
    return s.encode("latin-1", errors="replace").decode("latin-1")

class CustomPDF(FPDF):
    def __init__(self):
        super().__init__()
        # Para usar en footer (total de páginas)
        self.alias_nb_pages()

    def header(self):
        """
        Header desactivado (sello de agua comentado).
        """
        pass  # No se modifica

    def footer(self):
        """
        Pie de página con número de página y fecha/hora.
        """
        self.set_y(-15)
        self.set_font("Arial", 'I', 8)
        # Número de página
        page_text = f"Page {self.page_no()}/{''}"
        page_text = to_latin1(page_text)
        self.cell(0, 5, page_text, align='C')

        # Debajo, fecha/hora
        self.set_y(-10)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp = to_latin1(timestamp)
        self.cell(0, 5, f"Generated on: ", align='C')

# --- Función Auxiliar (Modificada) ---
def _draw_classification_row(pdf: FPDF, classification: str, value1: str, value2: str = None, value3: str = None):
    """Dibuja una fila en la tabla (ahora más flexible)."""
    line_height = 6

    # Abreviaturas (solo para el PDF, si es necesario)
    if classification == "Clinical Safety, Patient Care, and Quality Assurance":
        classification = "Clin. Safety"  # Abreviatura más corta
    elif classification == "Imaging Principles and Instrumentation":
        classification = "Imag. Princ."  # Abreviatura más corta

    wrapped_lines = textwrap.wrap(classification, width=28)  # AJUSTE MÁS AGRESIVO
    num_lines = max(1, len(wrapped_lines))
    total_height = num_lines * line_height

    x_start = pdf.get_x()
    y_start = pdf.get_y()
    # Parte de clasificación (multilínea)
    for i, txt in enumerate(wrapped_lines):
        if i == 0:
            border_mode = "LTR" if num_lines > 1 else "LRB"
        elif i == num_lines - 1:
            border_mode = "LRB"
        else:
            border_mode = "LR"
        pdf.cell(65, line_height, txt, border=border_mode, ln=1 if i < num_lines -1 else 0, align='L') # Reduje un poco
        if i < num_lines -1:
          pdf.set_x(x_start)

    pdf.set_xy(x_start + 65, y_start) #Ajuste

    pdf.cell(22, total_height, str(value1), border="LTRB", align='C') # Reduje
    if value2 is not None:
        pdf.cell(22, total_height, str(value2), border="LTRB", align='C')# Reduje
    if value3 is not None:
        pdf.cell(70, total_height, str(value3), border="LTRB", ln=1, align='C') #Aumente para el feedback
    else:
        pdf.ln()  # Forzar salto de línea si no hay tercer valor


def get_feedback(percent: float) -> str:
    """
    Devuelve el comentario de retroalimentación basado en el porcentaje.
    """
    if percent >= 95:
        return "Excellent"
    elif 80 <= percent <= 94:
        return "Satisfactory"
    elif 61 <= percent <= 79:
        return "May Require Further Study"
    elif percent <= 60:
        return "Requires Further Study"
    return "Unknown"  # En caso de un valor inesperado

def generate_pdf(user_data, score, status, photo_path=None):
    """
    Genera el PDF con dos tablas.  Ahora incluye el logo SOLO en la primera página.
    """
    pdf = CustomPDF()
    pdf.add_page()

    # --- Logo SOLO en la primera página ---
    logo_path = os.path.join("assets", "images", "medgoal.png")  # <-- CAMBIO AQUÍ
    print(f"Intentando cargar logo desde: {logo_path}")
    if os.path.exists(logo_path):
        print(f"¡El logo existe en {logo_path}!")
        pdf.image(logo_path, x=10, y=10, w=50)  # Ajusta x, y, w
    else:
        print(f"¡¡¡El logo NO se encontró en {logo_path}!!!")
    # --------------------------------------

    pdf.ln(40)  # Espacio DESPUÉS del logo (ajusta según sea necesario)

    # Título
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, to_latin1("RVT - ARDMS Exam Result"), ln=True, align='C')
    pdf.ln(10)

    # Datos de usuario
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, to_latin1(f"Name: {user_data.get('nombre', '')}"), ln=True)
    pdf.cell(0, 10, to_latin1(f"Email: {user_data.get('email', '')}"), ln=True)

    # Foto
    if photo_path and os.path.exists(photo_path):
        pdf.image(photo_path, x=10, y=pdf.get_y() + 5, w=30)
        pdf.ln(40)

    pdf.ln(5)

    # Puntuaciones
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, to_latin1(f"Passing Score: 555"), ln=True)
    pdf.cell(0, 10, to_latin1(f"Your Score: {score}"), ln=True)
    pdf.cell(0, 10, to_latin1(f"Status: {status}"), ln=True)
    pdf.ln(5)

    # --- Desglose por Clasificación (Dos Tablas) ---
    classification_stats = st.session_state.get("classification_stats")
    if classification_stats:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, to_latin1("Detailed Breakdown by Topic"), ln=True)

        # --- Tabla 1: Clasificación y Preguntas Hechas ---
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(65, 8, to_latin1("Classification"), border=1, ln=0, align='C')
        pdf.cell(22, 8, to_latin1("Q's Asked"), border=1, ln=1, align='C')  # Encabezado abreviado
        pdf.set_font("Arial", '', 12)

        total_questions_asked = 0
        for clasif, stats in classification_stats.items():
            total = stats.get("total", 0)
            total_questions_asked += total
            _draw_classification_row(pdf, clasif, total)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(65, 8, to_latin1("TOTAL"), border=1, ln=0, align='C')
        pdf.cell(22, 8, str(total_questions_asked), border=1, ln=1, align='C')


        pdf.ln(10)  # Espacio entre las tablas

        # --- Tabla 2: Respuestas Correctas, Porcentaje y Comentarios ---
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(65, 8, to_latin1("Classification"), border=1, ln=0, align='C')
        pdf.cell(22, 8, to_latin1("Correct"), border=1, ln=0, align='C')  # Encabezado abreviado
        pdf.cell(22, 8, to_latin1("%"), border=1, ln=0, align='C')  # Encabezado abreviado
        pdf.cell(70, 8, to_latin1("Feedback"), border=1, ln=1, align='C') # Más espacio para feedback
        pdf.set_font("Arial", '', 12)

        total_correct_answers = 0
        for clasif, stats in classification_stats.items():
            total = stats.get("total", 0)
            correct = stats.get("correct", 0)
            percent = (correct / total) * 100 if total > 0 else 0.0
            feedback = get_feedback(percent)
            total_correct_answers += correct
            _draw_classification_row(pdf, clasif, correct, f"{percent:.2f}%", feedback)  # Formato a 2 decimales

        total_percent = (total_correct_answers / total_questions_asked) * 100 if total_questions_asked > 0 else 0.0
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(65, 8, to_latin1("TOTAL"), border=1, ln=0, align='C')
        pdf.cell(22, 8, str(total_correct_answers), border=1, ln=0, align='C')
        pdf.cell(22, 8, f"{total_percent:.2f}%", border=1, ln=0, align='C')
        pdf.cell(70, 8, get_feedback(total_percent), border=1, ln=1, align='C')  # Feedback para el total


    pdf.ln(5)

    # --- Explicaciones y Feedback ---
    explanations = st.session_state.get("explanations")
    if explanations:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, to_latin1("Explanations & Feedback"), ln=True)
        pdf.set_font("Arial", '', 11)

        for q_idx, exp_text in explanations.items():
            #No se necesita concept_number
            #if str(q_idx).isdigit():
            #    concept_number = int(q_idx) + 1
            #else:
            #    concept_number = q_idx

            # Buscar "Concept to Study:" y ponerlo en negrita
            exp_text = to_latin1(exp_text) # Convertir todo antes.
            if "Concept to Study:" in exp_text:
                parts = exp_text.split("Concept to Study:", 1)
                before = parts[0]
                rest = parts[1]

                pdf.multi_cell(0, 6, before) # Parte antes (si existe)

                pdf.set_font("Arial", 'B', 11) # Negrita
                pdf.multi_cell(0, 6, "Concept to Study:")
                pdf.set_font("Arial", '', 11) # Volver a normal

                pdf.multi_cell(0, 6, rest.lstrip()) #.lstrip() para quitar espacios
            else:
                # Si no se encuentra "Concept to Study:", imprimir normal
                pdf.multi_cell(0, 6, exp_text)

            pdf.ln(4)

    # Guardar PDF
    if not os.path.exists("results"):
        os.makedirs("results")
    file_name = f"{user_data.get('email', 'unknown')}_result.pdf"
    path = os.path.join("results", file_name)
    pdf.output(path)
    return path
