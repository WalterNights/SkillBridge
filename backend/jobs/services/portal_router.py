"""Servicio que decide en qué portales scrapear, para qué query, dado un
perfil de usuario.

Antes del router (junio 2026) el endpoint `/scrape/` disparaba TODOS los
portales del registry con `query=profile.professional_title` y
`location=profile.city`. Eso traía cientos de ofertas off-topic para
perfiles no-tech (un diseñador UI/UX recibía "Líder de Mantenimiento" y
"Asesor de Ventas" porque Trabajos Colombia las publica todo el tiempo).
Con el threshold de match al 60% (Fase 1 del rediseño) muchas eran
descartadas, pero el costo en tiempo y rate-limit de los portales seguía.

Este servicio resuelve el problema con un LLM (Gemini) que recibe:
  - el perfil del usuario (título + skills + ciudad/país).
  - el catálogo de portales disponibles, con su descripción y categorías.

…y devuelve una lista de `PortalPlan` indicando qué portales tienen
sentido para ese perfil Y con qué query refinar la búsqueda (por ejemplo
"diseñador UX" en vez de "UI/UX Designer Diseñador 3D Animador Web" que
era el título crudo del usuario y rompía la búsqueda en LinkedIn).

Diseño:
  - Cache 24h por user_id (los planes cambian poco mientras el perfil no
    cambie). Invalidado en `UserProfile.save()` via signal.
  - Fail-open: si Gemini no está configurado / responde malformado /
    timeout → fallback determinístico basado en
    `users.services.profession_classifier` + las `categories` de cada
    scraper. Nunca devolvemos una lista vacía si el perfil es válido.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass

import google.generativeai as genai
from django.conf import settings
from django.core.cache import cache

from jobs.adapters.scrapers.registry import _REGISTRY, available_portals
from users.models import UserProfile
from users.services.profession_classifier import infer_profession_category

logger = logging.getLogger(__name__)

# TTL del cache de planes. 24h porque el perfil del usuario cambia poco;
# si cambia, la invalidación vía signal en UserProfile.save() refresca
# antes de que expire el TTL.
_CACHE_TTL_SECONDS = 24 * 3600

# Bump del prefix cuando cambian (a) la lista de portales del registry,
# (b) las descripciones que Gemini ve en el prompt, o (c) las categorías
# que clasifican cada scraper. Sin bump, perfiles con plan cacheado siguen
# viendo el catálogo viejo durante 24h después del deploy y nunca
# disparan los portales nuevos. Historial:
#   v1 — inicial (8 portales, sin Torre, WebSearch sin pasada creative)
#   v2 — 2026-06-27: +Torre, +pasadas creative en WebSearch (Domestika,
#        Behance, Workana, Dribbble), descripciones más detalladas para
#        que el LLM filtre mejor por categoría profesional.
#   v3 — 2026-06-27: +Freelancer en el grupo creative del WebSearch para
#        cubrir proyectos freelance cortos (diseñadores que toman gigs
#        mientras buscan full-time).
_CACHE_PREFIX = "portal_router:v3:"


@dataclass(frozen=True)
class PortalPlan:
    """Receta para scrapear un portal puntual: cuál + query + dónde.

    El router devuelve una lista de estos; el `JobService.scrape_for_profile`
    los itera en paralelo y consolida resultados.
    """

    portal: str
    query: str
    location: str


class PortalRouterService:
    """Resuelve qué portales scrapear para un perfil dado."""

    @classmethod
    def suggest_portals(cls, profile: UserProfile) -> list[PortalPlan]:
        """Devuelve la lista de planes de scrape para `profile`.

        Cache hit → devuelve cacheado. Cache miss → consulta a Gemini;
        si Gemini falla, fallback determinístico. NUNCA devuelve [] si
        el perfil tiene título — siempre hay un plan razonable.
        """
        cache_key = f"{_CACHE_PREFIX}{profile.user_id}"
        cached = cache.get(cache_key)
        if cached:
            return [PortalPlan(**p) for p in cached]

        plans = cls._call_gemini(profile)
        if not plans:
            plans = cls._fallback(profile)
            logger.info(
                "PortalRouter: usando fallback determinístico para user=%s (%d portales)",
                profile.user_id,
                len(plans),
            )
        else:
            logger.info(
                "PortalRouter: Gemini sugirió %d portales para user=%s",
                len(plans),
                profile.user_id,
            )

        cache.set(cache_key, [asdict(p) for p in plans], timeout=_CACHE_TTL_SECONDS)
        return plans

    @classmethod
    def invalidate(cls, user_id: int) -> None:
        """Invalida el cache para `user_id`. Llamar cuando el perfil cambia
        (signal en UserProfile.save). Idempotente — no falla si no había
        nada cacheado.
        """
        cache.delete(f"{_CACHE_PREFIX}{user_id}")

    # ---- internals ----------------------------------------------------

    @classmethod
    def _call_gemini(cls, profile: UserProfile) -> list[PortalPlan]:
        """Pide a Gemini que elija portales. Devuelve [] si:
          - GEMINI_API_KEY no está configurada
          - la llamada falla / timeout
          - la respuesta no es JSON válido
        En todos esos casos el caller usa el fallback determinístico.
        """
        if not settings.GEMINI_API_KEY:
            return []

        prompt = _PROMPT_TEMPLATE.format(
            title=profile.professional_title or "(no especificado)",
            skills=(profile.skills or "(no especificadas)")[:800],
            city=profile.city or "(no especificada)",
            catalog=_catalog_for_prompt(),
        )

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            response = model.generate_content(prompt)
            raw = (response.text or "").strip()
        except Exception as exc:
            logger.warning("PortalRouter: Gemini call failed: %s", exc)
            return []

        raw = _strip_markdown_fences(raw)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("PortalRouter: Gemini devolvió JSON inválido (%s)", exc)
            logger.debug("Raw response (truncated): %r", raw[:500])
            return []

        return _parse_plans(data, fallback_location=profile.city or "")

    @classmethod
    def _fallback(cls, profile: UserProfile) -> list[PortalPlan]:
        """Sin Gemini disponible: matcheamos `infer_profession_category`
        contra `scraper.categories`. Portales `all` van siempre.
        Si no hay match alguno (cosa rara), devolvemos todos los portales
        — peor inundar un poco que devolver un feed vacío sin razón.
        """
        category = infer_profession_category(profile.professional_title)
        query = profile.professional_title or ""
        location = profile.city or ""

        plans: list[PortalPlan] = []
        for portal_name, scraper_cls in _REGISTRY.items():
            cats = scraper_cls.categories
            if "all" in cats or category in cats:
                plans.append(PortalPlan(portal=portal_name, query=query, location=location))

        if plans:
            return plans
        return [
            PortalPlan(portal=p, query=query, location=location)
            for p in available_portals()
        ]


# ---- prompt template + helpers --------------------------------------

_PROMPT_TEMPLATE = """Eres un experto en bolsas de empleo de LATAM y debes decidir en qué portales tiene sentido buscar ofertas para el siguiente perfil profesional.

PERFIL DEL USUARIO
- Título profesional: {title}
- Skills: {skills}
- Ciudad: {city}

CATÁLOGO DE PORTALES DISPONIBLES
{catalog}

REGLAS
1. Elegí ÚNICAMENTE los portales que tengan probabilidad real de cubrir este perfil. Mejor un subset corto y certero que uno amplio y ruidoso.
2. Si el perfil es claramente NO-TECH (diseño, marketing, salud, ventas, etc.) NO incluyas portales tech-only (ej. hireline). Si es tech, sí.
3. Para cada portal elegido, sugerí un `query` corto (1-4 palabras) optimizado para ese portal. Usá el idioma típico del portal (español para LATAM, inglés para WeWorkRemotely). Para diseñadores/marketing usá términos del oficio en español neutro ("diseñador UX", "diseñador gráfico") antes que tecnologías sueltas ("Figma", "Photoshop").
4. El `location` para portales LATAM debe ser la ciudad o el país del usuario. Para portales globales/remotos podés pasar string vacío.
5. No incluyas explicaciones ni texto adicional. Solo el JSON.

FORMATO DE SALIDA
Devolvé ÚNICAMENTE un JSON array con esta forma exacta:
[
  {{"portal": "nombre_del_portal", "query": "query corto", "location": "ciudad o pais o vacio"}}
]
"""


def _catalog_for_prompt() -> str:
    """Serializa el catálogo de scrapers para el prompt — una línea por
    portal con `nombre [categorías]: descripción`. Nombres canónicos para
    que el LLM no invente variantes (`linkedIn-jobs` etc.).
    """
    lines = []
    for portal_name, scraper_cls in _REGISTRY.items():
        desc = scraper_cls.description or "(sin descripción)"
        cats = ", ".join(scraper_cls.categories) if scraper_cls.categories else "all"
        lines.append(f"- {portal_name} [{cats}]: {desc}")
    return "\n".join(lines)


def _strip_markdown_fences(text: str) -> str:
    """Algunos modelos envuelven JSON en ```json ... ``` aunque pidamos
    texto plano. Los limpiamos defensivamente."""
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text


def _parse_plans(data, fallback_location: str) -> list[PortalPlan]:
    """Valida la respuesta del LLM antes de aceptarla. Descartamos
    silenciosamente:
      - items que no son dict.
      - portales que no están en el registry (el LLM inventó nombres).
      - queries vacías.
    Si la lista entera queda vacía después de validar, el caller usa
    el fallback determinístico.
    """
    if not isinstance(data, list):
        return []
    valid_portals = set(_REGISTRY.keys())
    plans: list[PortalPlan] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        portal = (item.get("portal") or "").strip().lower()
        if portal not in valid_portals:
            logger.debug("PortalRouter: descartando portal desconocido %r", portal)
            continue
        query = (item.get("query") or "").strip()
        if not query:
            continue
        location = (item.get("location") or "").strip() or fallback_location
        plans.append(PortalPlan(portal=portal, query=query, location=location))
    return plans
