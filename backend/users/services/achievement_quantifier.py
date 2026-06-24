"""Servicio que toma una descripción de experiencia y devuelve 3
variantes 'cuantificadas' por AI — agregando números concretos, métricas
de impacto y verbos de acción.

Usa Gemini. El user nunca ve la respuesta cruda — la view la envuelve
y el frontend la muestra como un picker.

Si no hay GEMINI_API_KEY, levanta `QuantifyError` que la view traduce
a 503. Si el modelo devuelve algo inutilizable, también levantamos —
es preferible a mostrar variantes vacías.
"""

from __future__ import annotations

import json
import logging
import re

import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class QuantifyError(Exception):
    """Falla al cuantificar. La view la traduce a 502/503."""


_PROMPT_TEMPLATE = """Sos un coach de CV especializado en ayudar a profesionales a redactar logros con impacto cuantificable.

Tu tarea: tomar un bullet de experiencia laboral y devolver 3 reescrituras del MISMO logro, pero cuantificadas con números, porcentajes, métricas de tiempo o de equipo cuando sea razonable inferirlos.

CONTEXTO DEL ROL (opcional, puede estar vacío):
- Puesto: {role_title}
- Empresa: {company}

TEXTO ORIGINAL:
{original_text}

REGLAS OBLIGATORIAS:
- Devolvé EXACTAMENTE 3 variantes, ordenadas de conservadora a ambiciosa.
- Cada variante: 1-2 oraciones, máximo 280 caracteres.
- Cada variante DEBE incluir AL MENOS un número concreto (porcentaje, cantidad de personas, monto, tiempo, frecuencia, etc.).
- Los números pueden ser ESTIMACIONES RAZONABLES marcadas con "+" o "~" (ej: "+15%", "~20 clientes/mes") — eso señala al user que verifique, no que inventamos.
- Empezá cada variante con un VERBO DE ACCIÓN en pasado (Lideré, Reduje, Implementé, Coordiné, Optimicé, Automaticé, Aumenté, Diseñé, Negocié, etc).
- NO inventes herramientas, tecnologías o productos que no estén en el original.
- NO uses jerga corporativa hueca ("alineé sinergias", "impulsé el growth mindset").
- NO empieces con "Responsable de" — es pasivo y débil.
- Mantené el idioma del original (si está en español, devolvé en español; si en inglés, en inglés).

DEVOLVÉ ÚNICAMENTE un JSON válido con esta forma exacta:
{{"suggestions": ["variante 1", "variante 2", "variante 3"]}}

Sin markdown, sin explicaciones, sin texto adicional."""


def quantify_achievement(
    *,
    original_text: str,
    role_title: str = "",
    company: str = "",
) -> list[str]:
    """Devuelve 3 reescrituras cuantificadas del texto original.

    Side effect: una llamada HTTP a Gemini (~2-4s).
    Raises `QuantifyError` con mensaje legible si falla.
    """
    if not (original_text or "").strip():
        raise QuantifyError("El texto a cuantificar no puede estar vacío.")
    if len(original_text) > 2000:
        raise QuantifyError("El texto es demasiado largo (máx 2000 chars).")
    if not settings.GEMINI_API_KEY:
        raise QuantifyError("Gemini no está configurado en este servidor.")

    prompt = _PROMPT_TEMPLATE.format(
        role_title=role_title or "(no especificado)",
        company=company or "(no especificado)",
        original_text=original_text.strip(),
    )

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
    except Exception as exc:
        logger.warning("Gemini quantify_achievement failed: %s", exc)
        raise QuantifyError(
            "No pudimos generar sugerencias en este momento. Intentá en un minuto."
        ) from exc

    raw = (response.text or "").strip()
    # Gemini a veces devuelve el JSON envuelto en markdown fences.
    raw = _strip_markdown_fences(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Gemini quantify devolvió JSON inválido: %s", raw[:300])
        raise QuantifyError(
            "La respuesta del modelo no es válida. Intentá regenerar."
        ) from exc

    suggestions = data.get("suggestions") if isinstance(data, dict) else None
    if not isinstance(suggestions, list) or not suggestions:
        raise QuantifyError("El modelo no devolvió sugerencias utilizables.")

    # Sanitización: trim, filtrar vacíos, cap a 3, cap longitud.
    cleaned = [
        re.sub(r"\s+", " ", s).strip()[:400]
        for s in suggestions
        if isinstance(s, str) and s.strip()
    ]
    if not cleaned:
        raise QuantifyError("El modelo no devolvió sugerencias utilizables.")

    return cleaned[:3]


def _strip_markdown_fences(text: str) -> str:
    """Gemini a veces envuelve el JSON en ```json ... ```. Lo limpiamos."""
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text
