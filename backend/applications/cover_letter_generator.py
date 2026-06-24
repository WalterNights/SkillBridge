"""Generador de cartas de presentación con Gemini.

Toma el perfil del user + datos de la oferta, arma un prompt y devuelve
la carta como texto plano. No persiste — eso lo hace la view.

Si la GEMINI_API_KEY no está configurada o Gemini falla, levanta
`CoverLetterGenerationError` con mensaje legible — la view la traduce
a 503/502 según corresponda.
"""

from __future__ import annotations

import logging

import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class CoverLetterGenerationError(Exception):
    """Falla al generar la carta. La view la traduce a un HTTP error."""


# Prompt template parametrizable por tono + idioma. Mantenemos las
# instrucciones bien específicas — Gemini sin guía produce texto genérico
# tipo "estimados señores" que es justo lo que queremos evitar.
_PROMPT_ES = """Sos un especialista en escribir cartas de presentación que generan respuestas.

Escribí una carta de presentación para esta oferta de trabajo, usando los datos del candidato.

DATOS DEL CANDIDATO:
- Nombre: {full_name}
- Título profesional: {professional_title}
- Años de experiencia: {years_experience}
- Ciudad: {city}
- Skills principales: {skills}
- Resumen: {summary}

OFERTA:
- Puesto: {offer_title}
- Empresa: {offer_company}
- Descripción: {offer_description}

TONO: {tone_instruction}

INSTRUCCIONES OBLIGATORIAS:
- Máximo 250 palabras. Mejor 200.
- 3 párrafos exactos: gancho, encaje, cierre con CTA.
- Primer párrafo (gancho): por qué el candidato está específicamente interesado en ESTA empresa o ESTA oferta. Nada genérico tipo "vi su oferta y me interesa". Mencioná algo concreto de la empresa o el puesto.
- Segundo párrafo (encaje): 2-3 skills/experiencias del candidato que matchean directo con la oferta. Ejemplos concretos cuando se pueda. NO listar skills como bullets — prosa.
- Tercer párrafo (cierre): pedir una conversación / próximo paso. Frase corta, asertiva.
- NO usar "estimado/a", "a quien corresponda", ni clichés.
- NO inventar logros que no estén en los datos del candidato.
- NO mencionar la palabra "skills" ni "stack" — usar lenguaje natural.
- Empezar directo, sin "Hola" formal. Algo como "Me llamó la atención..." o "Vi su búsqueda de..." según el tono.
- Despedida: "Saludos, {full_name}" en una línea separada al final.

Devolvé SOLO el texto de la carta. Sin markdown, sin asteriscos, sin encabezados, sin notas explicativas."""


_PROMPT_EN = """You are a specialist in writing cover letters that generate replies.

Write a cover letter for this job offer, using the candidate's data.

CANDIDATE DATA:
- Name: {full_name}
- Professional title: {professional_title}
- Years of experience: {years_experience}
- City: {city}
- Main skills: {skills}
- Summary: {summary}

JOB:
- Position: {offer_title}
- Company: {offer_company}
- Description: {offer_description}

TONE: {tone_instruction}

MANDATORY RULES:
- Maximum 250 words. Better 200.
- 3 paragraphs exactly: hook, fit, close with CTA.
- First paragraph (hook): why the candidate is specifically interested in THIS company or THIS role. Nothing generic. Mention something concrete about the company or role.
- Second paragraph (fit): 2-3 skills/experiences from the candidate that match directly. Concrete examples when possible. Do NOT list skills as bullets — prose.
- Third paragraph (close): ask for a conversation / next step. Short, assertive sentence.
- Do NOT use "Dear Sir/Madam" or "To Whom It May Concern".
- Do NOT invent achievements not in the candidate's data.
- Sign-off: "Best, {full_name}" on a separate line at the end.

Return ONLY the letter text. No markdown, no headers, no explanatory notes."""


_TONE_INSTRUCTIONS_ES = {
    "formal": "Profesional y respetuoso. Vocabulario cuidado pero sin sonar antiguo. Usted o tú según el contexto del país; default a 'tú' si es ambiguo.",
    "cercano": "Cálido y humano, como hablándole a un colega que respetás. Tono conversacional pero competente. Usá 'tú'.",
    "directo": "Sin rodeos, frases cortas. Confianza sin arrogancia. Va directo al valor que aporta el candidato.",
}

_TONE_INSTRUCTIONS_EN = {
    "formal": "Professional and respectful. Careful vocabulary without sounding outdated.",
    "cercano": "Warm and human, like talking to a respected colleague. Conversational but competent.",
    "directo": "No fluff, short sentences. Confident without arrogance. Goes straight to the value.",
}


def generate_cover_letter(
    *,
    user_profile: dict,
    offer_title: str,
    offer_company: str,
    offer_description: str,
    tone: str = "cercano",
    language: str = "es",
) -> str:
    """Genera la carta y devuelve el texto.

    `user_profile` debe tener las claves: full_name, professional_title,
    years_experience, city, skills, summary. Cualquiera puede estar vacía.

    Side effect: una llamada HTTP a la API de Gemini (~2-5s).
    """
    if not settings.GEMINI_API_KEY:
        raise CoverLetterGenerationError("Gemini no está configurado en este servidor.")

    template = _PROMPT_ES if language == "es" else _PROMPT_EN
    tone_map = _TONE_INSTRUCTIONS_ES if language == "es" else _TONE_INSTRUCTIONS_EN
    tone_instruction = tone_map.get(tone, tone_map["cercano"])

    prompt = template.format(
        full_name=user_profile.get("full_name", "") or "el candidato",
        professional_title=user_profile.get("professional_title", "") or "profesional",
        years_experience=user_profile.get("years_experience", "") or "varios",
        city=user_profile.get("city", "") or "",
        skills=user_profile.get("skills", "") or "",
        summary=user_profile.get("summary", "") or "",
        offer_title=offer_title,
        offer_company=offer_company or "la empresa",
        offer_description=(offer_description or "")[:3000],  # cap por costos
        tone_instruction=tone_instruction,
    )

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
    except Exception as exc:
        logger.warning("Gemini cover letter generation failed: %s", exc)
        raise CoverLetterGenerationError(
            "No pudimos generar la carta en este momento. Intentá de nuevo en un minuto."
        ) from exc

    text = (response.text or "").strip()
    if len(text) < 50:
        raise CoverLetterGenerationError(
            "La respuesta del modelo fue demasiado corta. Intentá regenerar."
        )

    # Limpiar markdown residual que a veces Gemini incluye a pesar de las
    # instrucciones — asteriscos sueltos, fences vacíos.
    text = text.replace("**", "").replace("```", "").strip()
    return text
