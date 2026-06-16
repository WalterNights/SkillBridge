"""Interfaz común para scrapers de portales de empleo.

Cada scraper concreto (Computrabajo, InfoJobs, Indeed, etc.) implementa
`JobScraper` y devuelve `JobOfferData` (DTO puro, sin Django ORM).

La persistencia es responsabilidad de `JobService.save_new_offers` —
así los scrapers son testeables sin DB y se pueden ejecutar en paralelo
desde tasks de Celery sin tocar el modelo.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from common.skills_taxonomy import all_recognizable, normalize


class ScraperError(Exception):
    """Falla genérica de un scraper (red, parser, anti-bot, etc.)."""


@dataclass(frozen=True)
class JobOfferData:
    """DTO devuelto por cada scraper. Reemplaza el dict ad-hoc anterior."""

    title: str
    company: str
    location: str
    summary: str
    url: str
    keywords: str
    portal: str = "other"


class JobScraper(ABC):
    """Contrato que toda implementación de scraper debe respetar."""

    #: identificador en kebab-case usado por el `ScraperRegistry`.
    portal_name: str = ""

    #: timeout HTTP por request, en segundos. Subclases pueden override.
    request_timeout_seconds: int = 30

    @abstractmethod
    def search(self, query: str, location: str, pages: int = 2) -> list[JobOfferData]:
        """Devuelve las ofertas que matchean `query` en `location`.

        El scraper NO persiste nada. Devolver siempre DTOs; la decisión
        de cuáles son "nuevas" vs "ya conocidas" la toma el servicio.
        """


def extract_keywords(text: str) -> str:
    """Detecta skills conocidas en `text` y devuelve sus nombres canónicos.

    Comparte la taxonomía única (`common.skills_taxonomy`). Recorre todos
    los términos reconocibles (skills canónicas + aliases) y para cada hit
    con word-boundary devuelve la versión canónica, dedupada y ordenada.
    """
    if not text:
        return ""
    text_lower = text.lower()
    found = {
        normalize(kw)
        for kw in all_recognizable()
        if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", text_lower)
    }
    return ", ".join(sorted(found))
