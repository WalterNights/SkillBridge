"""Celery tasks del módulo tips.

`generate_weekly_tips` corre 1 vez por semana (lunes 06:00 UTC). Cada
semana le toca generar tips para UNA vertical profesional distinta —
roto por número ISO de semana sobre las verticales no-tech, para que el
pool crezca balanceado. Las tech ya están bien cubiertas por el seed
manual, así que las saltea.

Si la API key falta, falla la llamada o el output no parsea, el task se
loguea y termina sin tirar — el pool de tips manuales sigue funcionando.
"""

import json
import logging
import re
from datetime import date

from celery import shared_task
from decouple import config

from tips.models import Tip

logger = logging.getLogger(__name__)


# Verticales que rotamos en generación AI. Excluye 'tech' (cubierta por
# seed manual) y 'all' (genérico — los tips universales del seed bastan).
# El orden importa porque rotamos por week number mod len.
_ROTATION_SCOPES: list[str] = [
    "design",
    "marketing",
    "sales",
    "finance",
    "hr",
    "operations",
    "education",
    "health",
    "legal",
]


# Hint para que Gemini hable como nativo de esa vertical.
_SCOPE_CONTEXT: dict[str, str] = {
    "design": "diseñadores UX/UI, gráficos, producto, ilustradores",
    "marketing": "marketers digitales, community managers, copywriters, brand",
    "sales": "vendedores B2B/B2C, account executives, SDRs, customer success",
    "finance": "contadores, analistas financieros, controllers, auditores",
    "hr": "reclutadores, generalistas de RRHH, people ops, talento",
    "operations": "operaciones, supply chain, logística, planeación",
    "education": "docentes, tutores, coordinadores académicos, edtech",
    "health": "personal de salud: médicos, enfermería, terapeutas",
    "legal": "abogados, paralegals, compliance officers, asesores",
}


_PROMPT_TEMPLATE = """Eres un experto en orientación laboral para profesionales en LATAM.

Tu tarea: generar EXACTAMENTE 5 tips nuevos en JSON, específicamente dirigidos a {audience}.

REGLAS DE ESTILO:
- Voseo argentino, tono accionable.
- Empezá cada tip con verbo en imperativo (Personalizá, Sumá, Pedí, Guardá, Investigá).
- Entre 80 y 160 caracteres por tip.
- Una idea por tip — si necesita "y además", partilo en dos.
- Sin emojis, sin markdown, sin comillas dentro del texto.

REGLAS DE CONTENIDO:
- Los tips deben ser ESPECÍFICOS a la vertical "{scope}", no genéricos.
  Ej: para marketing mencioná funnel, CTR, attribution, no "buscá empleo activamente".
- Cada tip debe ser ÚNICO — no repitas conceptos ya cubiertos en la lista de abajo.
- Categorías permitidas para el field "category": cv, search, interview, networking, soft, tech, product, wellness.

TIPS YA EXISTENTES (no los dupliques en idea):
{existing_tips}

OUTPUT (JSON puro, sin ```, sin texto extra):
[
  {{"category": "search", "text": "..."}},
  ...
]
"""


def _pick_scope_for_week(today: date) -> str:
    """Devuelve la vertical objetivo para la semana actual. Rotación
    determinística por número ISO de semana — cada semana le toca otra
    vertical, ciclo completo en ~9 semanas."""
    iso_week = today.isocalendar()[1]
    return _ROTATION_SCOPES[iso_week % len(_ROTATION_SCOPES)]


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

    # Scope objetivo de la semana — rotamos por nº ISO de semana.
    target_scope = _pick_scope_for_week(date.today())
    audience = _SCOPE_CONTEXT.get(target_scope, target_scope)

    # Limito el contexto de existentes a los tips de la misma vertical +
    # los universales, no a todos. Sino el prompt explota al pedo y le
    # decimos al modelo "no dupliques temas de tech" cuando es para
    # finanzas — pierde foco.
    existing_qs = Tip.objects.filter(
        profession_scope__in=[target_scope, "all"]
    ).values_list("text", flat=True)
    existing = "\n".join(f"- {t}" for t in existing_qs)
    prompt = _PROMPT_TEMPLATE.format(
        audience=audience, scope=target_scope, existing_tips=existing
    )

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
            defaults={
                "category": category,
                "source": "ai",
                "profession_scope": target_scope,
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            skipped += 1

    logger.info(
        "Weekly tip generation: scope=%s, created=%d, skipped=%d",
        target_scope, created, skipped,
    )
    return {
        "status": "success",
        "scope": target_scope,
        "created": created,
        "skipped": skipped,
    }
