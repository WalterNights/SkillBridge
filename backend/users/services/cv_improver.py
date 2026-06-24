"""Mejorador de CV con AI.

Toma el perfil actual y devuelve una versión mejorada — summary
reescrito con más impacto, bullets de experiencia cuantificados,
skills reordenadas. La view la persiste solo si el user confirma.

Diferencias con `cv_auditor.py`:
  - auditor → analiza y reporta (no modifica)
  - improver → reescribe (proponer cambios concretos al perfil)

Reglas estrictas:
  - NO inventar empresas, fechas, títulos.
  - PRESERVAR el número de entries de experiencia y educación.
  - PRESERVAR el número de bullets por entry — solo reescribirlos.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class ImproveError(Exception):
    """Falla al mejorar. La view la traduce a 502/503."""


_PROMPT_TEMPLATE = """Sos un coach de CV especializado en LATAM. Tu trabajo: tomar un CV existente y reescribirlo con MÁS IMPACTO — sin inventar nada nuevo, sin agregar empresas ni roles, sin cambiar fechas.

PERFIL ACTUAL (JSON):
{profile_json}

REGLAS OBLIGATORIAS:
- NO INVENTES: empresas, títulos, fechas, instituciones, idiomas. Solo reescribís texto.
- PRESERVÁ el número exacto de entries en `experience` y `education`. Si el CV tiene 3 trabajos, devolvé 3 trabajos.
- Para cada entry de `experience`, `description` debe MANTENER UN BULLET POR LÍNEA con prefijo "• ". PRESERVÁ EL NÚMERO de bullets — si la entry tenía 12 bullets, devolvé 12 mejorados (no 4, no 15).
- Cada bullet reescrito debe ser ACCIONABLE: empezar con verbo en pasado (Lideré, Implementé, Reduje, Diseñé, Optimicé, etc), incluir un número/métrica cuando sea razonable inferirlo (marcado con + o ~ si es estimación), evitar la voz pasiva ("Fue responsable de" → "Lideré").
- `summary`: reescribilo en 3-5 oraciones que vendan al candidato. Hook → contexto → diferenciador. Sin clichés ("apasionado", "team player puro", "go-getter").
- `skills`: comma-separated, podés reordenar las más relevantes primero pero NO agregar nuevas. NO descartar ninguna que esté en el original.
- `soft_skills`: idem, no agregar nuevas.
- `professional_title`: respetá el actual a menos que sea claramente ambiguo (en cuyo caso ajustalo a algo más estándar — ej "Dev Full Stack" → "Full Stack Developer").
- Mantené el idioma del CV original.

Devolvé ÚNICAMENTE un JSON válido con esta forma exacta (mismas keys que el input, mismos counts):
{{
  "summary": "<resumen mejorado, 3-5 oraciones>",
  "professional_title": "<igual al original o ajuste menor>",
  "skills": "<las mismas habilidades, posiblemente reordenadas>",
  "soft_skills": "<las mismas habilidades blandas>",
  "experience": [
    {{
      "company": "<MISMA empresa>",
      "position": "<MISMO puesto>",
      "start_date": "<MISMA fecha>",
      "end_date": "<MISMA fecha>",
      "location_city": "<igual>",
      "location_country": "<igual>",
      "description": "• Bullet 1 reescrito con verbo + métrica\\n• Bullet 2\\n• Bullet 3 (MISMO COUNT que el input)"
    }}
  ]
}}

Sin markdown, sin explicaciones, sin texto adicional fuera del JSON."""


def improve_cv(profile_payload: dict) -> dict:
    """Devuelve un dict con los campos mejorados del CV.

    Solo incluye los campos que se reescriben — el caller hace merge
    con el perfil original al persistir (vía PATCH).

    Raises `ImproveError` con mensaje legible si falla.
    """
    if not settings.GEMINI_API_KEY:
        raise ImproveError("Gemini no está configurado en este servidor.")

    # Cap el payload para no superar el contexto del modelo. Los CVs muy
    # largos (10+ trabajos) se truncan al sample de input — el resto se
    # preserva intacto post-merge.
    profile_json = json.dumps(profile_payload, ensure_ascii=False, indent=2)[:12000]
    prompt = _PROMPT_TEMPLATE.format(profile_json=profile_json)

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
    except Exception as exc:
        logger.warning("Gemini CV improve failed: %s", exc)
        raise ImproveError(
            "No pudimos generar mejoras en este momento. Intentá en un minuto."
        ) from exc

    raw = _strip_markdown_fences((response.text or "").strip())
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Gemini improve devolvió JSON inválido: %s", raw[:300])
        raise ImproveError(
            "La respuesta del modelo no es válida. Intentá regenerar."
        ) from exc

    if not isinstance(data, dict):
        raise ImproveError("Estructura de respuesta inválida.")

    return _normalize_improved(data, profile_payload)


def _strip_markdown_fences(text: str) -> str:
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text


def _normalize_improved(improved: dict, original: dict) -> dict:
    """Defensive: si Gemini omite un campo o devuelve algo inutilizable,
    caemos al valor original (no perdemos datos)."""
    out: dict[str, Any] = {}

    for key in ("summary", "professional_title", "skills", "soft_skills"):
        value = improved.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = re.sub(r"\s+", " ", value).strip()
        else:
            out[key] = original.get(key, "")

    # Experience: validar mismo count, sino caemos al original entero
    improved_exp = improved.get("experience")
    original_exp = original.get("experience", [])
    if (
        isinstance(improved_exp, list)
        and isinstance(original_exp, list)
        and len(improved_exp) == len(original_exp)
        and all(isinstance(e, dict) for e in improved_exp)
    ):
        # Mergeamos cada entry: preservamos company/position/dates del
        # ORIGINAL (Gemini puede haber inventado a pesar de la instrucción)
        # y reemplazamos solo `description`.
        merged_exp = []
        for orig, new in zip(original_exp, improved_exp):
            merged = dict(orig)
            new_desc = new.get("description")
            if isinstance(new_desc, str) and new_desc.strip():
                merged["description"] = new_desc.strip()
            merged_exp.append(merged)
        out["experience"] = merged_exp
    else:
        # Si el count no cuadra, descartamos las mejoras de experience
        # — preferimos NO MODIFICAR antes que perder roles.
        out["experience"] = original_exp
        logger.warning(
            "CV improve: experience count mismatch (orig=%d, new=%s) — falling back to original",
            len(original_exp) if isinstance(original_exp, list) else -1,
            len(improved_exp) if isinstance(improved_exp, list) else "not-list",
        )

    return out


def profile_to_improve_payload(profile) -> dict:
    """Convierte un UserProfile a dict para mandar a Gemini.

    Reusa la misma lógica de parsing que cv_auditor para que el shape
    sea consistente entre features. Diferencia: incluye `id` para que
    el caller pueda hacer el PATCH al volver del modal."""
    experience_value = profile.experience
    if isinstance(experience_value, str) and experience_value.strip().startswith("["):
        try:
            experience_value = json.loads(experience_value)
        except json.JSONDecodeError:
            pass

    return {
        "id": profile.id,
        "professional_title": profile.professional_title or "",
        "summary": profile.summary or "",
        "skills": profile.skills or "",
        "soft_skills": profile.soft_skills or "",
        "experience": experience_value or [],
    }
