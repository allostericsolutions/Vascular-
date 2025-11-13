
import openai
except Exception:
openai = None

from .prompts import EXPLANATION_PROMPT  # Importa el prompt

def format_question_for_openai(question_data, user_answer):
"""
Formats a single question and the user's incorrect answer.
"""
enunciado = question_data["enunciado"]
opciones = question_data["opciones"]
respuesta_correcta = question_data["respuesta_correcta"]

opciones_str = "\n".join([f"{chr(97 + i)}) {opcion}" for i, opcion in enumerate(opciones)])

formatted_question = (
    f"Pregunta: {enunciado}\n"
    f"Opciones:\n{opciones_str}\n"
    f"Respuesta incorrecta: {user_answer}\n"
    f"Respuesta correcta: {', '.join(respuesta_correcta)}"
)
return formatted_question
def get_openai_explanation(incorrect_answers):
"""
Gets explanations from OpenAI for incorrect answers,
adding 'Concept to Study:' if there's a local explanation.

Comportamiento robusto y silencioso:
- Si no hay librería OpenAI o no hay API key: no llama a la API y continúa sin mostrar errores.
- Si falla la llamada a la API: se omite esa explicación y se continúa sin interrumpir el flujo.
- Si existe explicación local en la pregunta, se usa sin llamar a la API.
"""
explanations = {}

# Configuración perezosa/silenciosa de la API:
openai_enabled = False
if openai is not None:
    # No lanzar KeyError: usar .get
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if api_key:
        try:
            openai.api_key = api_key
            openai_enabled = True
        except Exception:
            # Si no se puede configurar la key, desactivamos sin romper
            openai_enabled = False

for answer_data in incorrect_answers:
    question_data = answer_data["pregunta"]
    user_answer = answer_data["respuesta_usuario"]
    question_index = answer_data["indice_pregunta"]

    # Explicación local (no requiere OpenAI)
    local_explanation = question_data.get("explicacion_openai", "").strip()
    concept_label = question_data.get("concept_to_study", "").strip()

    if local_explanation:
        # Mantener el estilo "Concept to Study:" si corresponde
        if concept_label:
            final_text = f"Concept to Study: {concept_label}\n{local_explanation}"
        else:
            final_text = local_explanation

        explanations[question_index] = final_text
        continue

    # Si no hay explicación local y OpenAI no está habilitado, omitir silenciosamente
    if not openai_enabled:
        continue

    # Llamada a OpenAI (si está habilitado)
    formatted_question = format_question_for_openai(question_data, user_answer)
    prompt = EXPLANATION_PROMPT.format(
        pregunta=formatted_question,
        respuesta_incorrecta=user_answer,
        respuesta_correcta=', '.join(question_data["respuesta_correcta"])
    )

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=16000,
            top_p=0.1,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        explanation = response.choices[0].message.content.strip()
        explanations[question_index] = explanation
    except Exception:
        # Fallo de API o red: omitir en silencio
        continue

return explanations
