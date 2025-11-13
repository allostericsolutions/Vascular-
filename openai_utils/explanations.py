
import openai
import os
import streamlit as st
from .prompts import EXPLANATION_PROMPT  # Importa el prompt

# Configuración de la API Key (desde Streamlit Secrets)
openai.api_key = st.secrets["OPENAI_API_KEY"]

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
    """
    explanations = {}
    for answer_data in incorrect_answers:
        question_data = answer_data["pregunta"]
        user_answer = answer_data["respuesta_usuario"]
        question_index = answer_data["indice_pregunta"]

        # Si hay explicación local, no llamamos a OpenAI
        local_explanation = question_data.get("explicacion_openai", "").strip()
        concept_label = question_data.get("concept_to_study", "").strip()

        if local_explanation:
            # Para que se muestre al estilo de ChatGPT, añadimos "Concept to Study:" si corresponde
            if concept_label:
                # Combina la etiqueta con la explicación local
                final_text = f"Concept to Study: {concept_label}\n{local_explanation}"
            else:
                # Si no hay concept_to_study, usamos la explicación local tal cual
                final_text = local_explanation

            explanations[question_index] = final_text
            continue

        # Si no hay explicación local, se llama a OpenAI
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
        except openai.OpenAIError as e:
            print(f"Error de OpenAI: {e}")
            st.error(f"Error al obtener la explicación de OpenAI: {e}")
            return {}
        except Exception as e:
            print(f"Error inesperado: {e}")
            st.error(f"Ocurrió un error inesperado: {e}")
            return {}

    return explanations
