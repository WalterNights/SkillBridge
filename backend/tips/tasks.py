"""Celery tasks del módulo tips.

`generate_weekly_tips` corre 1 vez por semana (lunes 06:00 UTC) y le
pide a Gemini 5 tips nuevos que NO dupliquen los que ya tenemos. Si la
API key falta, falla la llamada o el output no parsea, el task se
loguea y termina sin tirar — el pool de tips manuales sigue funcionando.
"""

import json
import logging
import re

from celery import shared_task
from decouple import config

from tips.models import Tip

logger = logging.getLogger(__name__)


_PROMPT_TEMPLATE = """Eres un experto en orientación laboral para developers y profesionales tech en LATAM.
Generá EXACTAMENTE 5 tips nuevos en JSON para una plataforma de matching de empleos.

REGLAS:
- Voseo argentino, tono accionable.
- Empezá cada tip con verbo en imperativo (Personalizá, Sumá, Pedí, Guardá, Investigá).
- Entre 80 y 160 caracteres por tip.
- Una idea por tip — si necesita "y además", partilo en dos.
- Sin emojis, sin markdown, sin comillas dentro del texto.
- Cada tip debe ser ÚNICO — no repitas conceptos ya cubiertos abajo.
- Categorías permitidas: cv, search, interview, networking, soft, tech, product, wellness.

TIPS YA EXISTENTES (no los dupliques en idea, solo evitalos):
{existing_tips}

OUTPUT (JSON puro, sin ```, sin texto extra):
[
  {{"category": "search", "text": "..."}},
  ...
]
"""


@shared_task(name="tips.generate_weekly_tips")
def generate_weekly_tips():
    """Pide 5 tips nuevos a Gemini. Idempotente — si la API devuelve un
    texto que ya existe, `get_or_create` lo ignora.
    """
    api_key = config("GEMINI_API_KEY", default=None)
    if not api_key:
        logger.warning("Skipping tip generation: GEMINI_API_KEY not configured")
        return {"status": "skipped", "reason": "no_api_key"}

    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai SDK not installed; skipping")
        return {"status": "skipped", "reason": "sdk_missing"}

    # Sample de los tips existentes para que el modelo no los duplique.
    # Cabe el set entero (~50) en el prompt — Gemini Flash maneja ~1M tokens.
    existing = "\n".join(f"- {t}" for t in Tip.objects.values_list("text", flat=True))
    prompt = _PROMPT_TEMPLATE.format(existing_tips=existing)

    try:
        genai.configure(api_key=api_key)
        model_name = config("GEMINI_MODEL", default="gemini-2.5-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        raw = response.text or ""
    except Exception as exc:
        logger.error("Gemini call failed during tip generation: %s", exc, exc_info=True)
        return {"status": "error", "reason": str(exc)}

    # Robustez: el modelo a veces envuelve el JSON en ```json…```.
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        items = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned non-JSON output: %s | raw=%r", exc, raw[:500])
        return {"status": "error", "reason": "invalid_json"}

    if not isinstance(items, list):
        logger.error("Expected JSON array, got %s", type(items).__name__)
        return {"status": "error", "reason": "expected_array"}

    valid_categories = {c for c, _ in Tip.CATEGORY_CHOICES}
    created = 0
    skipped = 0
    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        text = (raw_item.get("text") or "").strip()
        category = (raw_item.get("category") or "other").strip()
        # Filtros básicos. Largo entre 40-280 para tolerar variabilidad del modelo
        # pero descartar outputs degenerados (1 palabra o párrafos).
        if not (40 <= len(text) <= 280):
            skipped += 1
            continue
        if category not in valid_categories:
            category = "other"
        # `get_or_create` por text (unique) — si el modelo repite, no se duplica.
        _, was_created = Tip.objects.get_or_create(
            text=text,
            defaults={"category": category, "source": "ai", "is_active": True},
        )
        if was_created:
            created += 1
        else:
            skipped += 1

    logger.info("Weekly tip generation: created=%d, skipped=%d", created, skipped)
    return {"status": "success", "created": created, "skipped": skipped}
