"""Scraper de las vacantes de Mercado Libre vía Eightfold PCS-X.

MELI publica sus ofertas en `mercadolibre.eightfold.ai/careers` (el
dominio `careers-meli.mercadolibre.com` es un link tree que redirige
al mismo lugar). El buscador es una SPA que consume una API JSON:
`GET /api/pcsx/search`. Verificado contra producción 2026-07-01.

Diferencia crítica con Torre: Eightfold rebota 401 "Please try again
later" si no hay cookies de sesión. Solución: hacemos primero un
`GET /careers` con una `requests.Session()`; Eightfold devuelve dos
cookies (`_vs`, `_vscid`) y con eso el `GET /api/pcsx/search` responde
200. No hace falta CSRF token ni auth.

Shape de la respuesta (subset relevante):
    {"status": 200, "data": {"count": <int>, "positions": [
        {"id", "name", "locations", "creationTs", "postedTs",
         "department", "workLocationOption", "positionUrl", ...}
    ]}}

`positions[].positionUrl` es relativo (`/careers/job/{id}`) — le
prependemos el dominio para el usuario final.

Notas de diseño:
  - No hay `description` en el listado (igual que Torre). Usamos
    `department + workLocationOption` como summary de fallback y
    `extract_keywords` sobre el título para las skills. El detail
    page daría más info pero requiere 1 GET extra por oferta — caro.
  - MELI publica en Argentina, Brasil, Colombia, México, Chile, Perú,
    Uruguay. El scraper no filtra por país; el matching downstream
    se encarga (el user solo ve ofertas cercanas a su city).
  - `_MAX_AGE_DAYS = 30` — MELI a veces deja aperturas "vivas" por
    varias semanas; con 7 días perdíamos muchas ofertas legítimas.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

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

_ORIGIN = "https://mercadolibre.eightfold.ai"
_BOOTSTRAP_URL = f"{_ORIGIN}/careers"
_SEARCH_URL = f"{_ORIGIN}/api/pcsx/search"

# Eightfold ignora `num` — siempre devuelve 10 positions por request,
# verificado contra prod 2026-07-01 (pedimos num=25, respondió 10).
# Paginamos con `start` en incrementos de 10.
_PAGE_SIZE = 10
_MAX_PAGES = 4  # ~40 ofertas por scrape (MELI reporta ~50 totales por query)
_MAX_RESULTS = 40

# MELI deja aperturas vivas por semanas — 7 días descartaba casi todo.
# 30 días alinea con Torre y da recall razonable.
_MAX_AGE_DAYS = 30


class MeliScraper(JobScraper):
    """Scraper directo al ATS Eightfold que usa Mercado Libre."""

    portal_name = "meli"
    description = (
        "Mercado Libre (fintech + marketplace LATAM). Vacantes propias "
        "en Argentina, Brasil, Colombia, México, Chile, Perú, Uruguay. "
        "Fuerte en tech (backend, frontend, data, SRE, security), "
        "producto, diseño, marketing, ventas y operaciones. Un solo "
        "empleador — volumen medio pero calidad alta y proceso serio."
    )
    # MELI cubre casi todo excepto verticales muy específicas (agro,
    # salud clínica, oficios). No usamos `all` para evitar que aparezca
    # en feeds de perfiles blue-collar / rurales donde no aplica.
    categories = (
        "tech",
        "design",
        "marketing",
        "sales",
        "finance",
        "hr",
        "operations",
        "legal",
        "admin",
    )

    def search(self, query: str, location: str, pages: int = 1) -> list[JobOfferData]:
        """Pagina el endpoint PCS-X con las cookies de la sesión bootstrap.

        El parámetro `pages` del interface se ignora — usamos `_MAX_PAGES`
        internamente porque el cap real es `_MAX_RESULTS`.
        """
        if not query:
            raise ScraperError("query es obligatorio")

        logger.info("MELI scrape: query=%r location=%r", query, location)

        session = self._new_session()
        if session is None:
            # Fallo del bootstrap = no hay cookies = las requests van a
            # dar 401. Cortamos temprano sin ruido en los logs.
            return []

        offers: list[JobOfferData] = []
        seen_ids: set[int] = set()

        for page in range(_MAX_PAGES):
            start = page * _PAGE_SIZE
            positions = self._fetch_positions(session, query, start)
            if positions is None:
                break

            new_count = 0
            for item in positions:
                pid = item.get("id")
                if not isinstance(pid, int) or pid in seen_ids:
                    continue
                seen_ids.add(pid)
                offer = self._to_offer(item, location_hint=location)
                if offer is not None:
                    offers.append(offer)
                    new_count += 1
                if len(offers) >= _MAX_RESULTS:
                    break

            logger.info(
                "MELI page %d: %d positions, %d new (offers=%d)",
                page,
                len(positions),
                new_count,
                len(offers),
            )

            if len(offers) >= _MAX_RESULTS:
                break
            if len(positions) < _PAGE_SIZE:
                # Última página del set — no hay más resultados.
                break
            if new_count == 0:
                # Eightfold sirviéndonos duplicados: no insistir.
                break

        logger.info("MELI scrape complete: %d ofertas", len(offers))
        return offers

    # ---- HTTP ----------------------------------------------------------

    def _new_session(self) -> requests.Session | None:
        """Crea una `Session` y hace el GET /careers de bootstrap.

        Eightfold setea las cookies `_vs` y `_vscid` en esa respuesta.
        Sin ellas, `GET /api/pcsx/search` devuelve 401. Devuelve None
        si el bootstrap falla (network, 5xx) — el caller debe abortar.
        """
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            }
        )
        try:
            resp = session.get(
                _BOOTSTRAP_URL,
                headers={"Accept": "text/html,application/xhtml+xml,*/*"},
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.warning("MELI bootstrap failed: %s", exc)
            return None
        if resp.status_code != 200:
            logger.warning(
                "MELI bootstrap: %d (%r)", resp.status_code, resp.text[:200]
            )
            return None
        return session

    def _fetch_positions(
        self, session: requests.Session, query: str, start: int
    ) -> list[dict] | None:
        """Devuelve `data.positions` para (query, start), o None si falla."""
        try:
            resp = session.get(
                _SEARCH_URL,
                params={
                    "domain": "mercadolibre.com",
                    "start": str(start),
                    "num": str(_PAGE_SIZE),
                    "query": query,
                },
                headers={
                    "Accept": "application/json",
                    "Referer": _BOOTSTRAP_URL,
                },
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.warning("MELI search fetch failed (start=%d): %s", start, exc)
            return None

        if resp.status_code != 200:
            logger.warning(
                "MELI search returned %d (start=%d, body=%r)",
                resp.status_code,
                start,
                resp.text[:200],
            )
            return None

        try:
            payload = resp.json()
        except ValueError as exc:
            logger.warning("MELI search: respuesta no-JSON (%s)", exc)
            return None

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            logger.warning("MELI search: shape inesperado, sin `data`")
            return None
        positions = data.get("positions")
        if not isinstance(positions, list):
            logger.warning("MELI search: sin `positions` lista")
            return None
        return positions

    # ---- Parsing -------------------------------------------------------

    @staticmethod
    def _is_fresh(item: dict) -> bool:
        """`creationTs` (o `postedTs` como fallback) es un unix ts en
        segundos. Descartamos > `_MAX_AGE_DAYS`.

        Devuelve True si el TS es válido y la oferta está dentro del
        rango; False si falta o supera el threshold.
        """
        ts_raw = item.get("creationTs") or item.get("postedTs")
        if not isinstance(ts_raw, (int, float)) or ts_raw <= 0:
            return False
        try:
            created = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return False
        age_days = (datetime.now(timezone.utc) - created).days
        return age_days <= _MAX_AGE_DAYS

    @staticmethod
    def _format_location(item: dict, hint: str) -> str:
        """Normaliza `locations` a un string legible.

        - Eightfold devuelve strings tipo `"Medellín,Colombia"` (SIN
          espacio tras la coma). Reponemos el espacio.
        - Si el `workLocationOption` es `remote`, prependemos "Remote"
          para que `extract_modality` lo detecte.
        - Fallback al hint del caller si no hay location estructurado.
        """
        locs = item.get("locations")
        modality = (item.get("workLocationOption") or "").lower()

        location = ""
        if isinstance(locs, list) and locs:
            first = locs[0]
            if isinstance(first, str) and first.strip():
                location = ", ".join(
                    part.strip() for part in first.split(",") if part.strip()
                )

        if modality == "remote":
            # Marker para que extract_modality detecte remote; conservamos
            # el location si existe (empresa suele acompañar con ciudad
            # base incluso en remotos).
            location = f"Remote — {location}" if location else "Remote"

        if not location:
            location = hint or ""
        return location

    @staticmethod
    def _to_offer(item: dict, location_hint: str) -> JobOfferData | None:
        """Convierte un position de Eightfold → JobOfferData. Devuelve
        None si el item no pasa filtros de calidad (freshness, campos
        críticos ausentes).
        """
        if not isinstance(item, dict):
            return None
        if not MeliScraper._is_fresh(item):
            return None

        pid = item.get("id")
        title = (item.get("name") or "").strip()
        if not pid or not title:
            return None

        location = MeliScraper._format_location(item, location_hint)
        department = (item.get("department") or "").strip()
        modality = (item.get("workLocationOption") or "").strip().lower()

        # No hay description en el listado — armamos un summary desde
        # los campos que sí trae. Frontend puede linkear al detail page
        # (`positionUrl`) si el user quiere más.
        summary_parts = [title]
        if department:
            summary_parts.append(f"Área: {department}")
        if modality:
            summary_parts.append(f"Modalidad: {modality}")
        summary = " · ".join(summary_parts)

        keywords = extract_keywords(f"{title} {department}")

        # `positionUrl` viene relativo (`/careers/job/40834727`). Lo
        # prependemos con el origin canónico.
        position_url = item.get("positionUrl") or ""
        if isinstance(position_url, str) and position_url.startswith("/"):
            url = f"{_ORIGIN}{position_url}"
        else:
            url = f"{_ORIGIN}/careers/job/{pid}"

        return JobOfferData(
            title=title,
            company="Mercado Libre",
            location=location,
            summary=summary,
            keywords=keywords,
            url=url,
            portal="meli",
        )
