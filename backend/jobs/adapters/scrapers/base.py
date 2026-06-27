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

    #: Descripción humana del portal — qué categorías de empleo cubre y
    #: dónde. La consume el `PortalRouterService` para que el LLM decida
    #: si tiene sentido scrapearlo para un perfil dado. Una línea, ES,
    #: sin floreo: "qué + dónde + restricciones notables".
    description: str = ""

    #: Categorías macro que el portal cubre, alineadas con
    #: `users.services.profession_classifier`. `'all'` = generalista (sirve
    #: para cualquier perfil). El router las usa como fallback determinístico
    #: cuando el LLM no está disponible.
    categories: tuple[str, ...] = ("all",)

    @abstractmethod
    def search(self, query: str, location: str, pages: int = 2) -> list[JobOfferData]:
        """Devuelve las ofertas que matchean `query` en `location`.

        El scraper NO persiste nada. Devolver siempre DTOs; la decisión
        de cuáles son "nuevas" vs "ya conocidas" la toma el servicio.
        """


# Tokens administrativos que rompen las URLs de portales tipo
# Computrabajo cuando aparecen en el city. "Bogotá D.C." → la URL queda
# con "bogota-d.c." y el portal devuelve 0 ofertas (página vacía con
# 200 OK, peor que un 404). Truncamos el city al primer token útil
# antes de cualquiera de estos.
_CITY_ADMIN_STOPS: frozenset[str] = frozenset({
    "d.c.", "dc", "df", "d.f.",
    "sa", "s.a.", "lp", "l.p.",
    "rm", "r.m.",
    "cdmx",  # Ciudad de México: si lo escriben sólo así, queda.
})


def clean_city_for_slug(city: str) -> str:
    """Limpia el `city` antes de convertirlo en slug para URLs de
    portales. Devuelve la versión "nombre puro de ciudad" sin sufijos
    administrativos.

    Reglas:
      - Trunca al primer token que sea un sufijo administrativo conocido
        (D.C., DF, etc.) o que contenga un punto (típico de
        abreviaturas: "S.A.", "L.P.").
      - Si todos los tokens son válidos, devuelve el city sin cambios.
      - Si NINGÚN token es válido (edge case), devuelve el original.

    Casos:
      >>> clean_city_for_slug("Bogotá D.C.")
      'Bogotá'
      >>> clean_city_for_slug("Ciudad de México")
      'Ciudad de México'
      >>> clean_city_for_slug("Buenos Aires")
      'Buenos Aires'
      >>> clean_city_for_slug("Lima")
      'Lima'
      >>> clean_city_for_slug("")
      ''
    """
    if not city:
        return city
    parts = city.split()
    clean: list[str] = []
    for token in parts:
        if token.lower() in _CITY_ADMIN_STOPS:
            break
        if "." in token:
            break
        clean.append(token)
    return " ".join(clean) if clean else city


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


# Compartido entre scrapers para filtrar ofertas viejas al parse time.
# Ofertas con >7 días tienen mucha menos probabilidad de respuesta del HR.
MAX_OFFER_AGE_DAYS = 7

_AGE_PATTERN = re.compile(
    r"\b(?:hace|posted|publicado(?:\s+hace)?)\s+"
    r"(\d+)\s+"
    r"(d[íi]a|day|semana|week|mes|month|hour|hora|minute|minuto)",
    re.IGNORECASE,
)

# Palabras sueltas que indican "hoy" / "ayer" — comunes en HTML de
# Computrabajo/Bumeran que muestran "Hoy" arriba de la card sin "hace".
_RECENT_WORDS = re.compile(r"\b(hoy|ayer|today|yesterday)\b", re.IGNORECASE)


def extract_age_days(text: str) -> int | None:
    """Estima días desde publicación. Devuelve None si no detecta nada
    (caller asume "reciente"; no descartar).

    Solo la PRIMERA mención cuenta — las ofertas suelen poner la fecha
    al inicio del snippet ("hace 2 días · Empresa X · …").
    """
    if not text:
        return None
    lowered = text.lower()
    if _RECENT_WORDS.search(lowered):
        # Prioridad sobre "hace N días" que podría aparecer también en el
        # cuerpo (ej. "requisito: experiencia hace 5 años").
        return 0 if ("hoy" in lowered or "today" in lowered) else 1
    match = _AGE_PATTERN.search(text)
    if not match:
        return None
    qty = int(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith(("min", "hour", "hora")):
        return 0
    if unit.startswith(("d", "day")):
        return qty
    if unit.startswith(("semana", "week")):
        return qty * 7
    if unit.startswith(("mes", "month")):
        return qty * 30
    return None
