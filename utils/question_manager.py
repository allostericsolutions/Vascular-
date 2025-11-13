import json
import random
from typing import List, Dict, Any
import streamlit as st


def load_questions():
    """
    Loads all questions from 'data/preguntas.json'.
    """
    with open('data/preguntas.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def _qid(q: Dict[str, Any]) -> str:
    """
    Identificador único de pregunta (usa 'id' si existe; si no, 'enunciado').
    """
    return str(q.get("id") or q.get("enunciado"))


def _has_image(q: Dict[str, Any]) -> bool:
    """
    Determina si la pregunta tiene imagen (campo 'image' no vacío).
    """
    img = q.get("image")
    return bool(img and str(img).strip())


def ensure_additional_images_by_distribution(
    selected_questions: List[Dict[str, Any]],
    add_distribution: Dict[str, int]
) -> List[Dict[str, Any]]:
    """
    Post-proceso: suma preguntas con imagen reemplazando preguntas SIN imagen
    dentro de la MISMA clasificación, según la distribución pedida (p.ej. 4/4/2).
    - No duplica preguntas (usa id/enunciado para evitar repetir).
    - No altera la distribución por clasificación (reemplazo en la misma clase).
    - Si en alguna clase no hay suficientes víctimas o candidatas, añade las que se pueda.
    - No redistribuye el faltante a otras clases (respeta el ratio).
    """
    if not add_distribution:
        return selected_questions

    # Fuente: banco completo (FULL). Esta utilidad se invoca desde select_random_questions (full).
    source = load_questions()

    # Conjunto de IDs ya seleccionados
    selected_ids = {_qid(q) for q in selected_questions}

    # Víctimas (SIN imagen) por clase elegible
    victims_by_class: Dict[str, List[int]] = {}
    for idx, q in enumerate(selected_questions):
        c = q.get("clasificacion", "Other")
        if c in add_distribution and not _has_image(q):
            victims_by_class.setdefault(c, []).append(idx)

    # Pool de candidatas (CON imagen) por clase elegible, evitando duplicados
    pool_by_class: Dict[str, List[Dict[str, Any]]] = {}
    for q in source:
        c = q.get("clasificacion", "Other")
        if c in add_distribution and _has_image(q):
            qid = _qid(q)
            if qid not in selected_ids:
                pool_by_class.setdefault(c, []).append(q)

    # Aleatoriedad en víctimas y pool
    for c in victims_by_class:
        random.shuffle(victims_by_class[c])
    for c in pool_by_class:
        random.shuffle(pool_by_class[c])

    # Ejecutar el plan por clase (no se redistribuye el faltante)
    for c, target in add_distribution.items():
        if target <= 0:
            continue
        victims = victims_by_class.get(c, [])
        pool = pool_by_class.get(c, [])
        while target > 0 and victims and pool:
            v_idx = victims.pop()
            cand = pool.pop()
            selected_questions[v_idx] = cand
            selected_ids.add(_qid(cand))
            target -= 1

    return selected_questions


def select_random_questions(total=120):
    """
    Selects questions randomly, based on classification percentages.
    Aplica un post-proceso para sumar +10 preguntas con imagen (4/4/2)
    en las clases elegibles, sin alterar la distribución por clasificación.
    (Solo afecta al examen FULL; el SHORT usa select_short_questions y no se modifica.)
    """
    preguntas = load_questions()
    classification_percentages = {
        "Normal Anatomy, Perfusion, and Function": 21,
        "Pathology, Perfusion, and Function": 32,
        "Surgically Altered Anatomy and Pathology": 6,
        "Physiologic Exams": 12,
        "Ultrasound-guided Procedures/Intraoperative Assessment": 7,
        "Quality Assurance, Safety, and Physical Principles": 14,
        "Preparation,Documentation, and communication": 8,
    }
    total_percentage = sum(classification_percentages.values())
    if total_percentage != 100:
        raise ValueError("The sum of classification percentages must be 100.")

    clasificaciones: Dict[str, List[Dict[str, Any]]] = {}
    for pregunta in preguntas:
        clasif = pregunta.get("clasificacion", "Other")
        if clasif not in clasificaciones:
            clasificaciones[clasif] = []
        clasificaciones[clasif].append(pregunta)

    selected_questions: List[Dict[str, Any]] = []
    for clasif, percentage in classification_percentages.items():
        if clasif in clasificaciones:
            num_questions = int(total * (percentage / 100))
            available_questions = clasificaciones[clasif]
            selected_questions.extend(
                random.sample(available_questions, min(num_questions, len(available_questions)))
            )

    remaining = total - len(selected_questions)
    if remaining > 0:
        remaining_pool = [p for p in preguntas if p not in selected_questions]
        selected_questions.extend(random.sample(remaining_pool, remaining))

    # --- POST-PROCESO: sumar +10 con imagen en 3 clasificaciones (4/4/2) SOLO para FULL ---
    add_plan_by_class = {
        "Normal Anatomy, Perfusion, and Function": 4,
        "Pathology, Perfusion, and Function": 4,
        "Surgically Altered Anatomy and Pathology": 2,
    }
    selected_questions = ensure_additional_images_by_distribution(selected_questions, add_plan_by_class)
    # ----------------------------------------------------------------------------------------

    random.shuffle(selected_questions)
    return selected_questions


def shuffle_options(question):
    """
    Shuffles the options of a question randomly.
    """
    opciones = question.get("opciones", []).copy()
    random.shuffle(opciones)
    return opciones


def calculate_score():
    """
    Calculates the exam score and stores incorrect answers.
    Also calculates a classification-wise count of correct answers.
    """
    questions = st.session_state.selected_questions
    total_questions = len(questions)
    if total_questions == 0:
        return 0

    correct_count = 0
    # Contadores de aciertos por clasificación
    classification_stats: Dict[str, Dict[str, int]] = {}

    # Acceso más robusto al nombre del usuario
    user_name = st.session_state.get('user_data', {}).get('nombre', 'Unknown User')

    for idx, question in enumerate(questions):
        # Inicializar conteo para la clasificación de la pregunta
        clasif = question.get("clasificacion", "Other")
        if clasif not in classification_stats:
            classification_stats[clasif] = {"correct": 0, "total": 0}
        classification_stats[clasif]["total"] += 1

        user_answer = st.session_state.answers.get(str(idx), None)
        print(f"[{user_name}] Pregunta {idx}: Respuesta del usuario: {user_answer}, Respuesta correcta: {question['respuesta_correcta']}")  # DEBUG

        if user_answer is not None and user_answer in question["respuesta_correcta"]:
            correct_count += 1
            classification_stats[clasif]["correct"] += 1
        elif user_answer is not None:  # Solo registra si el usuario respondió
            incorrect_info = """
            """

            incorrect_info = {
                "pregunta": {
                    "enunciado": question["enunciado"],
                    "opciones": question["opciones"],
                    "respuesta_correcta": question["respuesta_correcta"],
                    "image": question.get("image"),
                    "explicacion_openai": question.get("explicacion_openai", ""),
                    "concept_to_study": question.get("concept_to_study", "")
                },
                "respuesta_usuario": user_answer,
                "indice_pregunta": idx
            }
            st.session_state.incorrect_answers.append(incorrect_info)
            print(f"[{user_name}] Añadida respuesta incorrecta a la lista: {incorrect_info}")  # DEBUG

    print(f"[{user_name}] Total de respuestas correctas: {correct_count}")  # DEBUG
    print(f"[{user_name}] Lista final de respuestas incorrectas en calculate_score: {st.session_state.incorrect_answers}")  # DEBUG

    # Guardar la estadística de clasificaciones
    st.session_state.classification_stats = classification_stats

    x = correct_count / total_questions
    if x <= 0:
        final_score = 0
    elif x <= 0.75:
        slope1 = 555 / 0.75
        final_score = slope1 * x
    else:
        slope2 = (700 - 555) / (1 - 0.75)
        final_score = slope2 * (x - 0.75) + 555

    return int(final_score)


# ------------------------------------------
# Para examen corto
# ------------------------------------------
def load_short_questions():
    """
    Loads all questions from 'data/preguntas_corto.json'.
    """
    with open('data/preguntas_corto.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def select_short_questions(total=30):
    """
    Selects 'total' questions randomly from the short exam questions file.
    Since this is for the free/demo version, no distribution by classification is applied.
    """
    questions = load_short_questions()
    if total > len(questions):
        total = len(questions)
    selected_questions = random.sample(questions, total)
    random.shuffle(selected_questions)
    return selected_questions
