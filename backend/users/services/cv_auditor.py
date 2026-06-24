"""Auditor estructural del CV con AI.

Toma el perfil completo del user y devuelve un análisis con score,
categorías evaluadas con severity, mensajes específicos y top
recomendaciones. Usado por el endpoint `/api/users/cv/audit/` antes
de que el user se postule a una oferta — feedback accionable para
mejorar el CV en el momento.

El output es JSON estructurado (no prosa libre) para que el frontend
pueda renderizar gauges + chips por categoría con consistencia visual.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class AuditError(Exception):
    """Falla al auditar. La view la traduce a 502/503."""


# Categorías que evaluamos — el modelo DEBE devolver una entrada por cada
# una. Si Gemini omite alguna, la rellenamos como 'missing' con mensaje
# default para que el frontend no se rompa.
CATEGORIES = (
    "summary",
    "experience",
    "skills",
    "education",
    "contact",
    "length",
)

SEVERITIES = ("ok", "warning", "critical")


_PROMPT_TEMPLATE = """Sos un coach de CVs con 10 años de experiencia ayudando profesionales en LATAM. Tu trabajo es auditar un CV ANTES de que el candidato se postule, dándole feedback accionable.

PERFIL DEL CANDIDATO (en JSON):
{profile_json}

Analizá el CV y devolvé feedback estructurado en JSON. Las categorías a evaluar son EXACTAMENTE estas (no agregues ni quites):

1. **summary** — resumen profesional. Evaluá presencia, largo (idealmente 2-4 oraciones), si tiene verbos de acción y claridad sobre el rol que busca.
2. **experience** — entradas de experiencia. Evaluá cantidad (>=2 ideal), si las descripciones están cuantificadas con números/métricas, si hay gaps temporales sin explicar, si los títulos son específicos.
3. **skills** — habilidades técnicas. Evaluá cantidad (5-15 ideal), si son relevantes al título profesional, si hay mezcla de hard skills y herramientas concretas.
4. **education** — formación. Evaluá presencia y completitud (institución, título, fechas).
5. **contact** — datos de contacto. Evaluá presencia de email, teléfono, ciudad, LinkedIn URL (este último muy valorado por reclutadores).
6. **length** — largo total del CV. Demasiado corto sugiere falta de detalle; demasiado largo sugiere falta de síntesis.

Para cada categoría asigná severity:
- "ok" → el área está bien o muy bien, no requiere acción urgente
- "warning" → hay algo mejorable que vale la pena trabajar
- "critical" → falta algo importante o está muy débil; el reclutador lo va a notar negativo

Reglas:
- Mensaje de cada categoría: 1-2 oraciones máximo, accionable, específico al contenido del candidato (no genérico).
- Score 0-100 holístico — pensálo como: cuán fuerte es este CV para un reclutador típico en LATAM.
- Top 3 recomendaciones priorizadas — las más impactantes que el candidato puede arreglar en <30min.
- NO inventes información del candidato.
- NO uses lenguaje corporativo hueco.

Devolvé ÚNICAMENTE un JSON válido con esta forma exacta:
{{
  "score": <int 0-100>,
  "overall": "<resumen de 1-2 oraciones del estado general del CV>",
  "categories": [
    {{"key": "summary", "label": "Resumen profesional", "severity": "ok|warning|critical", "message": "<feedback específico>"}},
    {{"key": "experience", "label": "Experiencia", "severity": "...", "message": "..."}},
    {{"key": "skills", "label": "Habilidades", "severity": "...", "message": "..."}},
    {{"key": "education", "label": "Educación", "severity": "...", "message": "..."}},
    {{"key": "contact", "label": "Datos de contacto", "severity": "...", "message": "..."}},
    {{"key": "length", "label": "Largo del CV", "severity": "...", "message": "..."}}
  ],
  "top_recommendations": [
    "<recomendación 1 específica y accionable>",
    "<recomendación 2>",
    "<recomendación 3>"
  ]
}}

Sin markdown, sin explicaciones, sin texto adicional."""


def audit_cv(profile_payload: dict) -> dict:
    """Audita el CV y devuelve el dict con score + categorías + recomendaciones.

    `profile_payload` es un dict normalizado con los campos del perfil
    (lo construye la view). Side effect: 1 llamada HTTP a Gemini (~3-5s).
    Raises `AuditError` con mensaje legible si falla.
    """
    if not settings.GEMINI_API_KEY:
        raise AuditError("Gemini no está configurado en este servidor.")

    profile_json = json.dumps(profile_payload, ensure_ascii=False, indent=2)
    prompt = _PROMPT_TEMPLATE.format(profile_json=profile_json[:8000])

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
    except Exception as exc:
        logger.warning("Gemini CV audit failed: %s", exc)
        raise AuditError(
            "No pudimos analizar tu CV en este momento. Intentá en un minuto."
        ) from exc

    raw = _strip_markdown_fences((response.text or "").strip())
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Gemini audit devolvió JSON inválido: %s", raw[:300])
        raise AuditError(
            "La respuesta del modelo no es válida. Intentá regenerar."
        ) from exc

    return _normalize_audit(data)


def _strip_markdown_fences(text: str) -> str:
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text


def _normalize_audit(data: Any) -> dict:
    """Defensiva: asegura el contrato que el frontend espera.

    Si Gemini omite una categoría, la rellenamos con severity='warning'
    y mensaje neutro. Si omite el score o lo manda fuera de rango, lo
    capeamos. Esto evita que el modal del frontend tire por un campo
    faltante después de 5s de loading.
    """
    if not isinstance(data, dict):
        raise AuditError("Estructura de respuesta inválida.")

    # Score
    score = data.get("score")
    try:
        score_int = int(score)
    except (TypeError, ValueError):
        score_int = 50
    score_int = max(0, min(100, score_int))

    overall = (data.get("overall") or "").strip()[:500]
    if not overall:
        overall = "Análisis completado."

    # Categories — rellenar las que falten
    raw_cats = data.get("categories", [])
    by_key = {}
    if isinstance(raw_cats, list):
        for entry in raw_cats:
            if not isinstance(entry, dict):
                continue
            key = entry.get("key")
            if key in CATEGORIES:
                by_key[key] = entry

    categories = []
    for key in CATEGORIES:
        entry = by_key.get(key, {})
        severity = entry.get("severity", "warning")
        if severity not in SEVERITIES:
            severity = "warning"
        message = (entry.get("message") or "Sin análisis para esta sección.").strip()
        message = re.sub(r"\s+", " ", message)[:500]
        categories.append(
            {
                "key": key,
                "label": entry.get("label") or _DEFAULT_LABELS[key],
                "severity": severity,
                "message": message,
            }
        )

    # Top recommendations — max 3
    raw_recs = data.get("top_recommendations", [])
    recs: list[str] = []
    if isinstance(raw_recs, list):
        for r in raw_recs:
            if isinstance(r, str) and r.strip():
                recs.append(re.sub(r"\s+", " ", r).strip()[:300])
            if len(recs) >= 3:
                break

    return {
        "score": score_int,
        "overall": overall,
        "categories": categories,
        "top_recommendations": recs,
    }


_DEFAULT_LABELS = {
    "summary": "Resumen profesional",
    "experience": "Experiencia",
    "skills": "Habilidades",
    "education": "Educación",
    "contact": "Datos de contacto",
    "length": "Largo del CV",
}


def profile_to_audit_payload(profile) -> dict:
    """Convierte una instancia de UserProfile (Django) al dict que consume
    `audit_cv`. Separado para que la view se mantenga simple y para
    testear el shape sin tocar la DB."""
    experience_value = profile.experience
    if isinstance(experience_value, str) and experience_value.strip().startswith("["):
        try:
            experience_value = json.loads(experience_value)
        except json.JSONDecodeError:
            pass
    education_value = profile.education
    if isinstance(education_value, str) and education_value.strip().startswith("["):
        try:
            education_value = json.loads(education_value)
        except json.JSONDecodeError:
            pass

    return {
        "full_name": f"{profile.first_name} {profile.last_name}".strip(),
        "professional_title": profile.professional_title or "",
        "city": profile.city or "",
        "phone": bool(profile.phone),
        "email": bool(profile.user.email if hasattr(profile, "user") else False),
        "linkedin_url": profile.linkedin_url or "",
        "portfolio_url": profile.portfolio_url or "",
        "summary": profile.summary or "",
        "skills": profile.skills or "",
        "experience": experience_value or "",
        "education": education_value or "",
    }
