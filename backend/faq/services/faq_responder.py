"""Generador de respuestas AI para preguntas del FAQ.

Toma la pregunta del usuario y devuelve una respuesta corta basada en
contexto fijo de SkilTak. El prompt incluye un "system card" que
describe qué hace la plataforma — esto previene que el modelo
alucine features que no existen.

La respuesta se muestra al user al instante (toast) y queda como
`ai_draft` en `FaqQuestion` para que el admin la revise antes de
publicar.
"""

from __future__ import annotations

import logging

import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class FaqResponderError(Exception):
    """Falla al generar respuesta. La view la traduce a 502/503."""


# Context fijo de SkilTak. Sin esto el modelo inventa precios, planes,
# integraciones, etc. Actualizar cuando lancemos features nuevas.
_PLATFORM_CONTEXT = """
SkilTak es una plataforma LATAM de búsqueda de empleo con AI:
- Agrega ofertas de Computrabajo, Elempleo, LinkedIn, WeWorkRemotely y Trabajos Colombia (varias veces al día).
- Calcula un porcentaje de match entre el CV del usuario y las skills mencionadas en cada oferta.
- Tiene una herramienta "Mejorar CV con AI" que reescribe summary, cuantifica bullets y reordena skills. 1 uso por cuenta.
- Es gratuita actualmente. No hay planes pagos todavía.
- Los datos del CV NO se comparten con empresas, ni se venden, ni se usan para entrenar modelos.
- Los usuarios pueden marcar ofertas como "ignoradas" para sacarlas del feed principal.
- Las postulaciones se rastrean en "Mis postulaciones" con estados (pending, applied, interview, offer, rejected).
- El sistema de notificaciones avisa de matches nuevos según preferencias en Configuración.
- Soporte: privacy@skiltak.com para temas de datos personales.
""".strip()


_PROMPT_TEMPLATE = """Eres el asistente de soporte de SkilTak. Tu trabajo es responder UNA pregunta de un usuario de la plataforma, basándote ÚNICAMENTE en el contexto de abajo.

CONTEXTO DE LA PLATAFORMA:
{platform_context}

REGLAS:
- Responde en ESPAÑOL NEUTRO con TUTEO ("tú puedes", no "vos podés", no "usted puede").
- Sé conciso: 2-4 oraciones máximo. Sin saludo, sin firma, sin "espero que te ayude".
- Si la pregunta es sobre algo que NO existe en SkilTak (ej. "¿tienen app móvil?"), respondelo honestamente: di que esa funcionalidad no está disponible actualmente y sugiere alternativas si las hay.
- Si la pregunta es ofensiva, irrelevante a la plataforma, o spam, responde: "Esta pregunta será revisada por nuestro equipo de moderación. Si quieres ayuda específica sobre SkilTak, contáctanos en privacy@skiltak.com."
- NO inventes precios, planes, integraciones, partners, certificaciones, números de usuarios, premios, ni fechas de lanzamiento.
- NO prometas features futuras con fechas concretas ("próximamente en marzo" prohibido).
- Si no estás seguro, dilo: "Esto es algo que prefiero que te confirme el equipo directamente — escríbenos a privacy@skiltak.com."

PREGUNTA DEL USUARIO:
{question}

RESPUESTA:""".strip()


def generate_answer(question: str) -> str:
    """Pide a Gemini una respuesta a la pregunta del user.

    Devuelve texto plano (sin markdown fences). Si Gemini falla o
    devuelve algo vacío, levanta `FaqResponderError` — la view la
    traduce a 502 y el front muestra "no pudimos generar respuesta
    automática; un admin revisará tu pregunta pronto".
    """
    question = (question or "").strip()
    if not question:
        raise FaqResponderError("Pregunta vacía.")

    if not settings.GEMINI_API_KEY:
        raise FaqResponderError("Gemini no está configurado en este servidor.")

    prompt = _PROMPT_TEMPLATE.format(
        platform_context=_PLATFORM_CONTEXT,
        question=question[:1000],  # cap para no superar contexto
    )

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
    except Exception as exc:
        logger.warning("Gemini FAQ responder failed: %s", exc)
        raise FaqResponderError(
            "No pudimos generar una respuesta automática en este momento."
        ) from exc

    text = (response.text or "").strip()
    # Stripear markdown fences por las dudas (algunos modelos los meten
    # aunque pidamos texto plano).
    if text.startswith("```"):
        # Cortar primera línea (apertura del fence) y cierre final.
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3].rstrip()

    if not text:
        raise FaqResponderError("La respuesta del modelo llegó vacía.")

    # Cap defensivo — si Gemini decide hacer un essay, lo recortamos
    # al primer párrafo largo. El admin igual va a editar antes de
    # publicar.
    if len(text) > 1500:
        text = text[:1500].rsplit(".", 1)[0] + "."

    return text
