"""Query expansion pre-scrape.

Devuelve la lista de queries a scrapear para un user, expandiendo el rol
principal a variantes hermanas dentro del mismo vertical. Sin esto, un
user "Full Stack Developer" solo ve ofertas con esos tokens en el título
y pierde matches obvios como "Backend Developer" o "Desarrollador
Frontend".

Diseño en `docs/role-expander-plan.md`.

Comportamiento:
  - Si `settings.ROLE_EXPANSION_ENABLED = False`, devolvemos solo el rol
    principal — feature flag de rollback rápido.
  - Cap por `settings.ROLE_EXPANSION_MAX_QUERIES` para no explotar
    volumen de scraping ni gatillar rate-limits.
  - Cero side effects. Función pura, testeable sin DB ni HTTP.

Fuentes de expansión (en orden de prioridad):
  1. Rol principal normalizado (siempre incluido).
  2. Sinónimo bidireccional ES ↔ EN sobre el rol principal.
  3. Roles hermanos por dict curado por vertical.

La lista final se dedupea case-insensitive preservando el orden — el
rol principal siempre queda primero, respetando la prioridad del user.
"""

from __future__ import annotations

import re

from django.conf import settings
from unidecode import unidecode

from jobs.services.matching_service import _extract_primary_role


# Traducciones ES → EN de tokens comunes en títulos profesionales.
# La dirección inversa (EN → ES) se computa automáticamente. Solo
# entradas neutrales usadas por los portales — evitamos regionalismos.
# Femeninos (`desarrolladora`, `ingeniera`) no se listan explícitamente
# porque los portales tratan masculino/femenino como equivalentes en
# búsquedas — un extra sin recall real y ambigüedad al invertir el mapa.
_ES_TO_EN: dict[str, str] = {
    "desarrollador": "developer",
    "programador": "developer",  # sinónimo de desarrollador
    "ingeniero": "engineer",
    "disenador": "designer",  # sin ñ para lookup normalizado
    "analista": "analyst",
    "arquitecto": "architect",
    "gerente": "manager",
    "lider": "lead",
}
# Dirección inversa — construida manualmente para elegir la traducción
# preferida cuando hay varios ES → mismo EN (ej. tanto "desarrollador"
# como "programador" mapean a "developer"; elegimos "desarrollador"
# como preferido para EN → ES por ser más común en LATAM tech).
_EN_TO_ES: dict[str, str] = {
    "developer": "desarrollador",
    "engineer": "ingeniero",
    "designer": "disenador",
    "analyst": "analista",
    "architect": "arquitecto",
    "manager": "gerente",
    "lead": "lider",
}

# Dict curado de roles hermanos por vertical. Keys normalizadas
# (lowercase + sin tildes) para lookup case/accent-insensitive.
#
# Regla del dict: solo agregar entradas cuando el "hermano" es un rol
# que un HR razonable buscaría al ver un CV del rol principal. NO poner
# roles vagamente relacionados (ej. "Product Manager" ≠ hermano de "UX
# Designer" — son colaboradores, no candidatos intercambiables).
#
# Values NO incluyen la key — la key va siempre primero por
# `_extract_primary_role`.
_ROLE_EXPANSIONS: dict[str, tuple[str, ...]] = {
    # ---- Tech ----
    "full stack developer": (
        "desarrollador full stack",
        "backend developer",
        "frontend developer",
    ),
    # Alias sin espacio — algunos users lo escriben así ("FullStack"). La
    # normalización a lowercase no lo colapsa, es un lookup distinto.
    "fullstack developer": (
        "desarrollador full stack",
        "backend developer",
        "frontend developer",
    ),
    "backend developer": (
        "desarrollador backend",
        "full stack developer",
    ),
    "frontend developer": (
        "desarrollador frontend",
        "full stack developer",
    ),
    "mobile developer": (
        "desarrollador mobile",
        "android developer",
        "ios developer",
        "react native developer",
    ),
    "data scientist": (
        "cientifico de datos",
        "data analyst",
        "ml engineer",
    ),
    "devops engineer": (
        "sre",
        "cloud engineer",
        "platform engineer",
    ),
    "qa engineer": (
        "quality assurance",
        "tester",
        "sdet",
    ),
    # ---- Design ----
    "ui/ux designer": (
        "disenador ui/ux",
        "product designer",
    ),
    "product designer": (
        "disenador de producto",
        "ui/ux designer",
    ),
    # ---- Agro (caso Fabio, cliente real) ----
    "zootecnista": (
        "medico veterinario",
        "ingeniero agronomo",
        "avicultor",
    ),
    "medico veterinario": (
        "veterinario",
        "zootecnista",
    ),
    "ingeniero agronomo": (
        "agronomo",
        "zootecnista",
    ),
    # ---- Marketing ----
    "community manager": (
        "social media manager",
        "marketing digital",
    ),
    "growth marketer": (
        "marketing digital",
        "performance marketing",
    ),
    # ---- Sales / customer ----
    "sales representative": (
        "ejecutivo comercial",
        "asesor comercial",
    ),
    "customer success manager": (
        "account manager",
        "gerente de cuentas",
    ),
}


def _normalize_key(text: str) -> str:
    """Baja a lowercase + saca tildes. Igual normalización que las keys
    del dict — sin esto, `"Zootecnista"` no matchea `"zootecnista"` (case)
    ni `"Médico Veterinario"` matchea `"medico veterinario"` (tilde)."""
    return unidecode(text.strip().lower())


def _swap_es_en(role: str) -> str | None:
    """Devuelve el rol con tokens ES↔EN swapeados, o None si no aplica.

    Tokenizamos por espacios/`/` preservando separadores, chequeamos
    cada token normalizado contra ambos mapas, reemplazamos si matchea.
    Sin doble pass — evita el bug del approach anterior que reprocesaba
    los tokens ya traducidos.

    Ejemplos:
      "Full Stack Developer"    → "Full Stack desarrollador"
      "Desarrollador Backend"   → "developer Backend"
      "Marketing Manager"       → "Marketing gerente"
      "Ingeniero Analista"      → "engineer analyst"
      "Zootecnista"             → None (sin token traducible)
    """
    tokens = re.split(r"([\s/]+)", role)
    changed = False
    new_tokens: list[str] = []
    for tok in tokens:
        norm = _normalize_key(tok)
        if norm in _ES_TO_EN:
            new_tokens.append(_ES_TO_EN[norm])
            changed = True
        elif norm in _EN_TO_ES:
            new_tokens.append(_EN_TO_ES[norm])
            changed = True
        else:
            new_tokens.append(tok)
    if not changed:
        return None
    result = "".join(new_tokens)
    return result if result != role else None


def _dedupe_case_insensitive(queries: list[str]) -> list[str]:
    """Preserva orden pero elimina duplicados normalizados. Sin esto,
    "Full Stack Developer" y "full stack developer" contarían distintas."""
    seen: set[str] = set()
    result: list[str] = []
    for q in queries:
        key = _normalize_key(q)
        if key in seen:
            continue
        seen.add(key)
        result.append(q)
    return result


def expand_role_queries(
    title: str,
    category: str | None = None,
    skills: list[str] | None = None,
) -> list[str]:
    """Devuelve queries a scrapear para un user.

    El rol principal SIEMPRE queda primero (respeta la elección del user).
    Después vienen: sinónimo ES↔EN, hermanos del dict.

    Args:
        title: `professional_title` crudo del user.
        category: categoría macro inferida (`tech`, `agro`, etc). Reservado
            para lógica futura — hoy no se usa porque el dict ya está
            agrupado por vertical implícitamente. La firma acepta el
            parámetro para no romper el llamador cuando lo agreguemos.
        skills: lista de skills declaradas por el user. Reservado para
            stack-based expansion (Fase 5 del plan). Hoy no se usa.

    Returns:
        Lista de queries deduplicada, con cap
        `settings.ROLE_EXPANSION_MAX_QUERIES`. Si el rol principal no
        matchea ningún hermano y no hay sinónimo aplicable, devuelve
        solo `[rol_principal]`.

        Si `settings.ROLE_EXPANSION_ENABLED = False`, devuelve
        `[rol_principal]` sin expandir — rollback rápido para
        emergencias sin necesitar redeploy.
    """
    primary = _extract_primary_role(title or "").strip()
    if not primary:
        return []

    if not getattr(settings, "ROLE_EXPANSION_ENABLED", True):
        return [primary]

    max_queries = getattr(settings, "ROLE_EXPANSION_MAX_QUERIES", 4)

    queries: list[str] = [primary]

    # 1. Sinónimo bidireccional ES↔EN sobre el rol principal
    swapped = _swap_es_en(primary)
    if swapped is not None:
        queries.append(swapped)

    # 2. Hermanos del dict curado. Match case + accent insensitive.
    key = _normalize_key(primary)
    siblings = _ROLE_EXPANSIONS.get(key, ())
    queries.extend(siblings)

    # Dedup y cap
    deduped = _dedupe_case_insensitive(queries)
    return deduped[:max_queries]
