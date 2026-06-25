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
from datetime import date
from typing import Any

import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class ImproveError(Exception):
    """Falla al mejorar. La view la traduce a 502/503."""


_PROMPT_TEMPLATE = """Sos un coach de CV especializado en LATAM. Tu trabajo: tomar un CV existente y reescribirlo con MÁS IMPACTO — sin inventar trayectorias nuevas.

PERFIL ACTUAL (JSON):
{profile_json}

IDIOMA OBLIGATORIO DE LA RESPUESTA: {language_name} ({language_code}).
Reescribí TODO el texto (summary, skills, soft_skills, professional_title,
descriptions de experiencia, location, etc) en {language_name}. Si el CV
original está en {language_name}, mantenelo. Si está en otro idioma, lo
detectamos mal — respondé igual en {language_name}. NO TRADUZCAS si el
original ya está en {language_name}.

CONTEXTO TEMPORAL: la fecha de hoy es {today}. Cualquier fecha posterior es FUTURO y casi siempre indica un error de tipeo (ej. "2025" cuando quisieron decir "2024"). NO debe haber `end_date` en el futuro salvo si es explícitamente "Presente"/"Actual"/"Current"/"Present".

REGLAS OBLIGATORIAS:
- NO INVENTES empresas, títulos, instituciones, idiomas, ni roles enteros. Esa parte del CV es sagrada.
- NO TRADUZCAS — respondé en el mismo idioma del input. Si el summary del input dice "Over 3 years of experience…" devolvé summary en INGLÉS, no "Más de 3 años de experiencia…". Lo mismo para skills, bullets, todo.
- FECHAS: podés CORREGIRLAS si están claramente rotas:
    a) `start_date` posterior a `end_date` → invertilas si tiene sentido, o ajustá la que parezca tipeada mal (el otro context — el rol anterior/siguiente — ayuda a inferir).
    b) `end_date` en el futuro (después de hoy) Y el user NO indicó "Presente"/"Actual"/"Present" → ajustá a "Presente"/"Present" (en el idioma del CV) si es el rol más reciente, o al mes anterior al siguiente trabajo si no.
    c) Solapamientos imposibles (2 jobs fulltime mismo período en empresas distintas) → ajustá las fechas más sospechosas (las que tienen año futuro o no encajan con la cronología).
  Si las fechas se ven OK, NO las toques. NO inventes meses ni años con cero evidencia.
- PRESERVÁ el número exacto de entries en `experience` y `education`. Si el CV tiene 3 trabajos, devolvé 3 trabajos.
- Para cada entry de `experience`, `description` debe MANTENER UN BULLET POR LÍNEA con prefijo "• ". PRESERVÁ EL NÚMERO de bullets — si la entry tenía 12 bullets, devolvé 12 mejorados (no 4, no 15).
- Cada bullet reescrito debe ser ACCIONABLE: empezar con verbo en pasado (en español: Lideré, Implementé, Reduje, Diseñé, Optimicé; en inglés: Led, Implemented, Reduced, Designed, Optimized), incluir un número/métrica cuando sea razonable inferirlo (marcado con + o ~ si es estimación), evitar la voz pasiva ("Fue responsable de" → "Lideré", "Was responsible for" → "Led").
- `summary`: reescribilo en 3-5 oraciones que vendan al candidato. Hook → contexto → diferenciador. Sin clichés ("apasionado", "team player puro", "go-getter", "passionate", "rockstar").
- `skills`: comma-separated, podés reordenar las más relevantes primero pero NO agregar nuevas. NO descartar ninguna que esté en el original.
- `soft_skills`: idem, no agregar nuevas.
- `professional_title`: respetá el actual a menos que sea claramente ambiguo (en cuyo caso ajustalo a algo más estándar — ej "Dev Full Stack" → "Full Stack Developer"). En el mismo idioma del input.

Devolvé ÚNICAMENTE un JSON válido con esta forma exacta (mismas keys que el input, mismos counts):
{{
  "summary": "<resumen mejorado, 3-5 oraciones>",
  "professional_title": "<igual al original o ajuste menor>",
  "skills": "<las mismas habilidades, posiblemente reordenadas>",
  "soft_skills": "<las mismas habilidades blandas>",
  "experience": [
    {{
      "company": "<MISMA empresa — NO cambiar>",
      "position": "<MISMO puesto — NO cambiar>",
      "start_date": "<fecha original O corregida si estaba rota>",
      "end_date": "<fecha original O corregida si estaba rota>",
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
    # Detectar idioma del CV upfront — sin esto, Gemini ve un prompt en
    # español y asume que debe responder en español aunque el CV input
    # esté en inglés. La detección es heurística (stopwords) pero
    # suficiente para distinguir es vs en, que cubren ~99% de nuestros
    # users en LATAM/EEUU.
    lang_code = _detect_cv_language(profile_payload)
    lang_name = "Spanish (español)" if lang_code == "es" else "English"
    prompt = _PROMPT_TEMPLATE.format(
        profile_json=profile_json,
        today=date.today().isoformat(),
        language_code=lang_code,
        language_name=lang_name,
    )

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


# Stopwords de cada idioma — palabras de muy alta frecuencia que casi
# nunca aparecen en el otro idioma. Para CVs de developers (a veces con
# stack en inglés "React, Node") evitamos contar los términos técnicos
# y nos enfocamos en conectores comunes que delatan la prosa.
_ES_STOPWORDS = frozenset({
    "el", "la", "los", "las", "de", "del", "en", "con", "para", "por",
    "y", "o", "pero", "como", "que", "qué", "más", "este", "esta",
    "estos", "estas", "un", "una", "unos", "unas", "ser", "fue", "es",
    "son", "soy", "tiene", "tienen", "su", "sus", "mi", "mis", "nos",
    "se", "le", "lo", "al",
})
_EN_STOPWORDS = frozenset({
    "the", "of", "and", "to", "in", "for", "with", "on", "at", "by",
    "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "but", "or", "if",
    "this", "that", "these", "those", "an", "a", "i", "we", "you",
    "my", "our", "their",
})


def _detect_cv_language(payload: dict) -> str:
    """Devuelve 'es' o 'en' según los stopwords más frecuentes en el
    texto libre del CV. Mira summary + descripciones de experience
    (skills suele tener jerga técnica en inglés siempre, no es señal).
    Default 'es' si ninguno gana o no hay texto suficiente.
    """
    chunks = [payload.get("summary", "") or ""]
    for exp in payload.get("experience", []) or []:
        if isinstance(exp, dict):
            chunks.append(exp.get("description", "") or "")
    text = " ".join(chunks).lower()
    if len(text) < 30:
        return "es"
    tokens = re.findall(r"[a-záéíóúñ]+", text)
    es_hits = sum(1 for t in tokens if t in _ES_STOPWORDS)
    en_hits = sum(1 for t in tokens if t in _EN_STOPWORDS)
    if en_hits > es_hits:
        return "en"
    return "es"


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
        # Mergeamos cada entry:
        #   - company / position / location_* → SIEMPRE del original
        #     (Gemini puede haber inventado a pesar de la instrucción).
        #   - start_date / end_date → del nuevo SI parecen razonables
        #     (string corto, no vacío, distinto del original = el modelo
        #     identificó un error y lo corrigió). Sino del original.
        #   - description → del nuevo si trae algo no-vacío.
        merged_exp = []
        for orig, new in zip(original_exp, improved_exp):
            merged = dict(orig)
            new_desc = new.get("description")
            if isinstance(new_desc, str) and new_desc.strip():
                merged["description"] = new_desc.strip()
            for date_field in ("start_date", "end_date"):
                new_date = new.get(date_field)
                if (
                    isinstance(new_date, str)
                    and new_date.strip()
                    and len(new_date) <= 50  # fechas razonables son cortas
                ):
                    merged[date_field] = new_date.strip()
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
