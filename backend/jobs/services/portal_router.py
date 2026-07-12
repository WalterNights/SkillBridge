"""Servicio que decide en qué portales scrapear, para qué query, dado un
perfil de usuario.

ARQUITECTURA (rediseño 2026-06-27):
El path crítico (lo que se ejecuta cada vez que un user toca "Obtener
ofertas") es 100% determinístico — NO llama a Gemini. Usa
`infer_profession_category(professional_title)` para clasificar el
perfil y matchea contra las `categories` que cada scraper declara.
Resultado: latencia <1ms, cero costo de API, predictible.

Motivos del cambio:
- Gemini Flash es barato pero igual aporta latencia (200-500ms) en el
  path interactivo donde el user ya está esperando 15-30s del scrape.
- El fallback determinístico cubre bien los casos típicos (perfiles
  tech / design / marketing / sales / agro / etc. que tienen título
  claro y matchean alguna categoría conocida).
- Sin Gemini en el path, el rate limit del scrape pasa a depender solo
  del costo real (compute del VPS + bans de portales externos), no de
  la cuota de Gemini.

AI queda RESERVADA para:
- Análisis y mejora de CV (`users.adapters.gemini_analyzer`,
  `users.services.cv_improver`). Uso bajo, alto valor por call.
- Generación de cartas de presentación (`applications.cover_letter_generator`).
- FAQs (`faq.services.faq_responder`).
- Futuro: optimización diaria por cron (precomputar planes ideales por
  user) o trigger admin manual via `PortalRouterService.preview_with_ai()`.
  Estos paths son one-shot, no se ejecutan por cada scrape.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import google.generativeai as genai
from django.conf import settings

from jobs.adapters.scrapers.registry import _REGISTRY, available_portals
from jobs.services.matching_service import _extract_primary_role
from users.models import UserProfile
from users.services.profession_classifier import infer_profession_category

logger = logging.getLogger(__name__)


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

        Path determinístico: `infer_profession_category` + las
        `categories` de cada scraper + expansión de queries via
        `role_expander`. <1ms, sin AI, sin red.

        El `query` de cada plan es una variante del rol principal
        expandida por `expand_role_queries`. Ejemplo: un user
        "FullStack Developer" genera queries para "FullStack Developer",
        "desarrollador full stack", "backend developer", "frontend
        developer" — así el scrape trae también ofertas hermanas del
        mismo vertical, no solo las que matchean tokens del título
        crudo. Cap por `settings.ROLE_EXPANSION_MAX_QUERIES`. Feature
        flag `ROLE_EXPANSION_ENABLED=False` desactiva la expansión y
        vuelve al comportamiento previo (1 query por portal).

        Titulos largos multi-rol se manejan por `_extract_primary_role`
        (dentro de `expand_role_queries`) — normaliza al primer rol
        antes de expandir, evitando explotar el volumen.

        NUNCA devuelve [] si el perfil tiene título — si no hay match
        por categoría (caso muy raro), cae a "todos los portales".
        """
        # Import local para evitar ciclos y facilitar el override del
        # feature flag en tests (`settings.ROLE_EXPANSION_ENABLED = ...`).
        from jobs.services.role_expander import expand_role_queries

        category = infer_profession_category(profile.professional_title)
        location = profile.city or ""

        # Skills tipeadas como lista para expand_role_queries. Split simple
        # por coma — igual estrategia que `matching_service.enrich_with_match`.
        skills = [
            s.strip()
            for s in (profile.skills or "").split(",")
            if s.strip()
        ]

        queries = expand_role_queries(
            profile.professional_title or "",
            category=category,
            skills=skills,
        )
        if not queries:
            # Sin título → sin queries → sin planes. Antes devolvía 1 plan
            # con query vacío por portal; los scrapers que exigen query
            # rebotaban con ScraperError. Ahora explicitamos el vacío para
            # que el caller (JobService) sepa que no hay nada que hacer.
            logger.info(
                "PortalRouter: sin queries expandidas para user=%s (título vacío)",
                profile.user_id,
            )
            return []

        plans: list[PortalPlan] = []
        for portal_name, scraper_cls in _REGISTRY.items():
            cats = scraper_cls.categories
            if "all" in cats or category in cats:
                for query in queries:
                    plans.append(
                        PortalPlan(portal=portal_name, query=query, location=location)
                    )

        if not plans:
            # Fallback de último recurso: ningún scraper declaró categoría
            # 'all' ni la categoría inferida. No debería pasar pero igual
            # devolvemos algo para no tirar el scrape entero. Un plan por
            # portal por query.
            logger.warning(
                "PortalRouter: ningún scraper matchea categoría %r — usando todos",
                category,
            )
            plans = [
                PortalPlan(portal=p, query=q, location=location)
                for p in available_portals()
                for q in queries
            ]

        logger.info(
            "PortalRouter: %d planes para user=%s (categoría=%s, queries=%d)",
            len(plans),
            profile.user_id,
            category,
            len(queries),
        )
        return plans

    # ---- AI-assisted preview (opt-in) ---------------------------------
    # Reservado para herramientas admin / crons de optimización diaria.
    # NO se llama desde `suggest_portals` para mantener el path crítico
    # libre de Gemini y de latencia de red.

    @classmethod
    def preview_with_ai(cls, profile: UserProfile) -> list[PortalPlan]:
        """Pide a Gemini que elija portales para `profile`.

        Devuelve [] si:
          - GEMINI_API_KEY no está configurada.
          - la llamada falla / timeout.
          - la respuesta no es JSON válido o no tiene portales válidos.

        Pensado para:
          - Endpoint admin "/api/jobs/router/preview/<user_id>/" que
            permite comparar la sugerencia AI vs el plan determinístico.
          - Cron de optimización diaria (futuro) que precomputa planes
            ideales para users activos.

        NUNCA llamar desde el path interactivo del user — agrega latencia
        + costo de API. Usar `suggest_portals()` ahí.
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
            logger.warning("PortalRouter.preview_with_ai: Gemini call failed: %s", exc)
            return []

        raw = _strip_markdown_fences(raw)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "PortalRouter.preview_with_ai: JSON inválido (%s)", exc
            )
            logger.debug("Raw response (truncated): %r", raw[:500])
            return []

        return _parse_plans(data, fallback_location=profile.city or "")


# ---- prompt template + helpers (usados solo por preview_with_ai) ----

_PROMPT_TEMPLATE = """Sos un experto en bolsas de empleo de LATAM. Decidí en qué portales buscar ofertas para este perfil.

PERFIL
- Título: {title}
- Skills: {skills}
- Ciudad: {city}

CATÁLOGO
{catalog}

REGLAS
1. Subset corto y certero, no amplio y ruidoso.
2. Perfil NO-TECH (diseño, marketing, salud, ventas, agro, etc.) NO usa portales tech-only (hireline).
3. Query corto (1-4 palabras), en el idioma del portal (ES para LATAM, EN para WeWorkRemotely). Para no-tech usá el oficio en ES neutro ("diseñador UX", "zootecnista", "veterinario") antes que herramientas sueltas.
4. Location: ciudad o país para LATAM, vacío para globales/remotos.

OUTPUT
Respondé SOLO con el JSON array a continuación. Sin texto antes, sin texto después, sin markdown, sin explicaciones. Si dudás, devolvé el JSON igual.

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
