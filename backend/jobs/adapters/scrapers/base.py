"""Interfaz común para scrapers de portales de empleo.

Cada scraper concreto (Computrabajo, InfoJobs, Indeed, etc.) implementa
`JobScraper` y devuelve `JobOfferData` (DTO puro, sin Django ORM).

La persistencia es responsabilidad de `JobService.save_new_offers` —
así los scrapers son testeables sin DB y se pueden ejecutar en paralelo
desde tasks de Celery sin tocar el modelo.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import requests

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
    #: Fecha de cierre publicada por el portal (JSON-LD `validThrough`,
    #: `deadline` de Torre). None si el portal no la publica.
    expires_at: datetime | None = None


def parse_iso_datetime(raw: object) -> datetime | None:
    """Parsea una fecha ISO 8601 de un portal a datetime con zona horaria.

    Acepta "2026-10-30", "2026-10-30T23:59:59Z" o con offset. Fechas sin
    zona se asumen UTC. Devuelve None si viene vacía o malformada — una
    fecha rota no debe tumbar el scrape de la oferta.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _host_is_public(host: str) -> bool:
    """True si TODAS las IPs a las que resuelve `host` son públicas."""
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def is_public_http_url(url: str) -> bool:
    """SEGURIDAD (SSRF): True si `url` es http(s) y su host resuelve solo a
    IPs públicas. Bloquea 127.0.0.1, redes privadas y el endpoint de
    metadata de cloud (169.254.169.254). False ante cualquier duda."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    return _host_is_public(parsed.hostname.lower())


_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECTS = 5


def safe_get(url: str, **kwargs) -> requests.Response | None:
    """`requests.get` que valida cada salto contra SSRF.

    Sigue las redirecciones a mano (máx. 5) para chequear con
    `is_public_http_url` cada destino: con `allow_redirects=True`, un
    portal (o una URL de un resultado de búsqueda) podría redirigir al
    backend hacia una IP interna. Devuelve None si algún salto no es
    seguro. La respuesta final trae `history` y `url` como `requests`.
    """
    history: list[requests.Response] = []
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        if not is_public_http_url(current):
            return None
        response = requests.get(current, allow_redirects=False, **kwargs)
        location = (
            response.headers.get("location")
            if response.status_code in _REDIRECT_STATUSES
            else None
        )
        if not location:
            if history:
                response.history = history
            return response
        history.append(response)
        response.close()
        current = urljoin(current, location)
    return None


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
    #: Países (ISO-2) cuyas ofertas trae el portal. ("all",) = global o
    #: remoto. El router no lo corre para perfiles de otro país: InfoJobs
    #: (solo España) no tiene sentido para alguien en Colombia, y al revés.
    countries: tuple[str, ...] = ("all",)
    #: Tope de queries expandidas por scrape (None = todas). 1 para los
    #: que ignoran el query (sitemaps) o tienen un costo/riesgo alto por
    #: request (buscadores con anti-bot).
    max_queries: int | None = None

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
# 14 días: los emails de "empleos similares" de LinkedIn suelen sugerir
# ofertas de 1–3 semanas de antigüedad y el user espera verlas en el feed.
# El umbral anterior de 7 días descartaba muchas legítimas. Ofertas mucho
# más viejas ya suelen estar cerradas — el probe diario las apaga.
MAX_OFFER_AGE_DAYS = 14

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
