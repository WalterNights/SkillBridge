"""Scraper de Torre.co usando su API JSON pública.

Torre es una bolsa moderna LATAM/global con foco en tech, product,
design y roles digital-native. A diferencia de los portales basados en
HTML, expone una API REST pública que devuelve JSON estructurado — la
parseamos directo sin BeautifulSoup, lo que la hace mucho más resiliente
a redesigns del frontend.

Endpoint: `POST https://search.torre.co/opportunities/_search/`
Body mínimo: `{"skill/role": {"text": "<query>", "experience": "..."}}`

La API permite filtros adicionales (organization, remote, salary, etc.)
pero arrancamos minimalista para no perder recall — el matching
downstream se encarga de decidir si la oferta calza con el usuario.

Notas de robustez:
- Si la API cambia el shape del JSON, devolvemos [] silenciosamente (el
  resto del scrape no se rompe). Loggeamos el problema para diagnóstico.
- Cap a `MAX_RESULTS` para no martillar al portal ni inundar nuestra DB
  con ofertas que el user probablemente nunca abre.
- Sin pagination explícita: la primera "page" de Torre devuelve hasta
  100 resultados, más que suficiente para un scrape per-user.
"""

from __future__ import annotations

import logging

import requests

from jobs.adapters.scrapers.base import (
    JobOfferData,
    JobScraper,
    ScraperError,
    extract_keywords,
)

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

_SEARCH_URL = "https://search.torre.co/opportunities/_search/"
# Cap defensivo. Torre tiende a devolver buenas matches en los primeros
# 30-50 resultados — más allá empieza a meter ofertas con relevancia
# floja que igual van a quedar bajo el threshold de match% downstream.
MAX_RESULTS = 50

# URL canónica de cada oferta. Torre usa `torre.co/jobs/{id}` para el
# detail page público — distinto del endpoint de API. Si la oferta trae
# `slug`, lo concatenamos para una URL legible; sino, solo el id.
_OPPORTUNITY_URL_TEMPLATE = "https://torre.co/jobs/{id}"
_OPPORTUNITY_URL_WITH_SLUG = "https://torre.co/jobs/{id}/{slug}"


class TorreScraper(JobScraper):
    """Scraper de torre.co vía API JSON."""

    portal_name = "torre"
    description = (
        "Bolsa LATAM moderna (torre.co). Fuerte en tech, product y "
        "design — roles UI/UX, product design, frontend, full-stack, "
        "data, growth. API JSON estable (más robusta que scrapers "
        "HTML). Cobertura global pero foco en LATAM y remote."
    )
    # Tech + design + marketing: las verticales que Torre cubre bien.
    # NO usamos 'all' para que el router no la dispare para perfiles
    # blue-collar (limpieza, mantenimiento) donde Torre tiene cero oferta.
    categories = ("tech", "design", "marketing")

    def search(self, query: str, location: str, pages: int = 1) -> list[JobOfferData]:
        if not query:
            raise ScraperError("query es obligatorio")

        logger.info("Torre scrape: query=%r location=%r", query, location)

        try:
            response = requests.post(
                _SEARCH_URL,
                json=self._build_body(query),
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.warning("Torre API request failed: %s", exc)
            return []

        if response.status_code != 200:
            logger.warning(
                "Torre API devolvió %d (body: %r)",
                response.status_code,
                response.text[:200],
            )
            return []

        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning("Torre API: response no es JSON válido (%s)", exc)
            return []

        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            logger.warning("Torre API: shape inesperado, sin `results` lista")
            return []

        offers: list[JobOfferData] = []
        for item in results[:MAX_RESULTS]:
            offer = self._to_offer(item, location_hint=location)
            if offer is not None:
                offers.append(offer)
        logger.info("Torre: %d ofertas parseadas (de %d en respuesta)", len(offers), len(results))
        return offers

    # ---- internals -----------------------------------------------------

    @staticmethod
    def _build_body(query: str) -> dict:
        """Body mínimo para el endpoint `_search`.

        IMPORTANTE: `experience` o `proficiency` es OBLIGATORIO dentro
        de `skill/role` — si falta, la API devuelve 400 BAD_REQUEST.
        Usamos `potential-to-develop` (el más permisivo) para maximizar
        recall: el matching downstream decide qué ofertas son buenas
        según el perfil del user, no filtramos en la fuente.

        Verificado contra la API real el 2026-06-27 con curl —
        responses tipo `{"total": 5282, "results": [...]}`.
        """
        return {
            "skill/role": {
                "text": query.strip(),
                "experience": "potential-to-develop",
            },
        }

    @staticmethod
    def _to_offer(item: dict, location_hint: str) -> JobOfferData | None:
        """Convierte un resultado de la API en `JobOfferData`. Devuelve
        None si faltan campos críticos (id, objective). `location_hint`
        es el location pedido por el caller — sirve de fallback si la
        oferta no trae location estructurado.
        """
        if not isinstance(item, dict):
            return None

        opp_id = item.get("id")
        title = (item.get("objective") or item.get("title") or "").strip()
        if not opp_id or not title:
            return None

        # `organizations` es lista de orgs (un opp puede ser de varias).
        # Tomamos la primera como company.
        orgs = item.get("organizations") or []
        company = ""
        if isinstance(orgs, list) and orgs:
            first = orgs[0]
            if isinstance(first, dict):
                company = (first.get("name") or "").strip()

        # `locations` puede venir como lista de strings o lista de dicts.
        # Normalizamos al primer entry parseable. Si no hay, usamos el
        # location del caller como fallback (no quedar con location vacío
        # rompe la inferencia de country/modality downstream).
        location = ""
        locs = item.get("locations") or []
        if isinstance(locs, list) and locs:
            first_loc = locs[0]
            if isinstance(first_loc, str):
                location = first_loc.strip()
            elif isinstance(first_loc, dict):
                location = (first_loc.get("name") or "").strip()
        if not location and bool(item.get("remote")):
            # `remote=True` sin location estructurado → marker explícito
            # para que extract_modality detecte modalidad remote.
            location = "Remote"
        if not location:
            location = location_hint or ""

        # `skills` es lista de objetos con `name`. Las concatenamos al
        # texto para que extract_keywords levante las que conocemos.
        skills_text = ""
        skills = item.get("skills") or []
        if isinstance(skills, list):
            names = []
            for sk in skills:
                if isinstance(sk, dict):
                    name = sk.get("name")
                    if isinstance(name, str) and name.strip():
                        names.append(name.strip())
                elif isinstance(sk, str):
                    names.append(sk.strip())
            skills_text = ", ".join(names)

        # NOTA: el endpoint `_search` NO devuelve la descripción larga del
        # job (solo title + skills + meta). El detail page tendría más
        # info pero requeriría un GET extra por oferta — caro. Usamos el
        # `tagline` (one-liner de la org) como fallback y rellenamos con
        # skills si todo lo demás falla. El matcher downstream igual
        # funciona porque el match se calcula sobre title + keywords.
        tagline = item.get("tagline") or ""
        if not isinstance(tagline, str):
            tagline = ""
        summary = tagline.strip()

        keywords = extract_keywords(f"{title} {skills_text} {summary}")

        # URL: si la oferta trae `slug`, lo usamos para una URL legible
        # (mejor preview/share). Sino caemos al template solo-id.
        slug = item.get("slug")
        if isinstance(slug, str) and slug.strip():
            url = _OPPORTUNITY_URL_WITH_SLUG.format(id=opp_id, slug=slug.strip())
        else:
            url = _OPPORTUNITY_URL_TEMPLATE.format(id=opp_id)

        return JobOfferData(
            title=title,
            company=company,
            location=location,
            summary=summary or skills_text or title,
            keywords=keywords,
            url=url,
            portal="torre",
        )
