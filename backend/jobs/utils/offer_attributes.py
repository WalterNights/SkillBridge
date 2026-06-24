"""Extractores heurísticos para los atributos derivados de una oferta.

Se usan en dos lugares:
  1. Scrapers / `JobService.save_new_offers` al momento de persistir.
  2. Migración de backfill — pasa por todas las filas existentes con
     los mismos extractores para que el filtro funcione retroactivamente.

Mantener TODA la lógica acá — si cambia un país o se agrega una
heurística de modalidad, un solo punto de modificación.
"""

from __future__ import annotations

import re
from unidecode import unidecode


# Códigos ISO 3166-1 alpha-2 que cubrimos. Si una oferta no calza con
# ninguno → 'XX' (desconocido), que el filtro respeta.
COUNTRY_UNKNOWN = "XX"

# Modalidad — enum cerrado. 'unknown' default cuando ninguna keyword
# clara aparece en location ni en summary.
MODALITY_REMOTE = "remote"
MODALITY_HYBRID = "hybrid"
MODALITY_ONSITE = "onsite"
MODALITY_UNKNOWN = "unknown"

VALID_MODALITIES = (MODALITY_REMOTE, MODALITY_HYBRID, MODALITY_ONSITE, MODALITY_UNKNOWN)


# Heurística country por substring. Ordenamos del más específico al más
# genérico — si una location es "Buenos Aires, Argentina", el match de
# 'argentina' es claro y prioritario sobre la ciudad. Las ciudades grandes
# están como fallback para cuando el portal omite el país (común en
# computrabajo/elempleo locales).
_COUNTRY_RULES: list[tuple[str, tuple[str, ...]]] = [
    # (ISO, list of substrings to look for — todos en lowercase + sin tildes)
    ("MX", ("mexico", "ciudad de mexico", "cdmx", "guadalajara", "monterrey", "puebla", "queretaro", "merida", "leon ", " df ", "mx,", " mx ", "mx)")),
    ("CO", ("colombia", "bogota", "medellin", "cali", "barranquilla", "cartagena", "bucaramanga", "cundinamarca", "antioquia")),
    ("AR", ("argentina", "buenos aires", "caba ", "cordoba", "rosario", "mendoza", "tucuman", "la plata")),
    ("CL", ("chile", "santiago", "valparaiso", "concepcion", "vina del mar", "providencia")),
    ("PE", ("peru", " lima ", "lima,", "arequipa", "trujillo", "cusco")),
    ("UY", ("uruguay", "montevideo")),
    ("PY", ("paraguay", "asuncion")),
    ("BO", ("bolivia", "la paz", "santa cruz")),
    ("EC", ("ecuador", "quito", "guayaquil")),
    ("VE", ("venezuela", "caracas", "maracaibo")),
    ("CR", ("costa rica", "san jose")),
    ("PA", ("panama",)),
    ("DO", ("republica dominicana", "santo domingo", "dominican")),
    ("GT", ("guatemala",)),
    ("ES", ("espana", "spain", "madrid", "barcelona", "valencia", "sevilla", "bilbao")),
    ("US", ("united states", "estados unidos", "usa,", " usa ", " us ", "us,", "new york", "san francisco", "miami", "austin", "remote-us")),
]


def extract_country(location: str | None) -> str:
    """Detecta el país desde el string de location.

    Devuelve código ISO o `COUNTRY_UNKNOWN`. Insensible a mayúsculas
    y tildes — la mayoría de los portales escriben "México" con tilde
    pero algunos no, y el comparador normalize es trivial.
    """
    if not location:
        return COUNTRY_UNKNOWN

    # Normalizamos: lowercase + sin tildes + padding con espacios para
    # que los word-boundaries naive (" mx ") funcionen aunque el match
    # esté al borde del string.
    normalized = " " + unidecode(location.lower()) + " "
    for iso, patterns in _COUNTRY_RULES:
        for pat in patterns:
            if pat in normalized:
                return iso
    return COUNTRY_UNKNOWN


# Modalidad — regexes que buscamos primero en location, después en summary.
# Damos prioridad a "remoto" (explicit > implicit) y "híbrido" (formato
# mixto) sobre "presencial" para evitar misclasificar "presencial o
# híbrido" como onsite.
_MODALITY_REMOTE_PATTERN = re.compile(
    r"\b("
    r"remot[oa]s?"          # remoto/remota
    r"|remote(?:[\s-]*work)?"
    r"|teletrabajo"
    r"|home[\s-]?office"
    r"|trabajo\s+desde\s+casa"
    r"|100\s*%\s*remoto"
    r"|work\s+from\s+home"
    r"|wfh\b"
    r")\b",
    re.IGNORECASE,
)

_MODALITY_HYBRID_PATTERN = re.compile(
    r"\b("
    r"h[ií]brido?"
    r"|hybrid"
    r"|mixt[oa]"
    r")\b",
    re.IGNORECASE,
)

_MODALITY_ONSITE_PATTERN = re.compile(
    r"\b("
    r"presencial(?:es)?"
    r"|on[\s-]?site"
    r"|in[\s-]?office"
    r"|en\s+oficina"
    r")\b",
    re.IGNORECASE,
)


def extract_modality(location: str | None, summary: str | None = None) -> str:
    """Detecta modalidad. Busca primero en location (señal fuerte),
    fallback a summary. Prioridad: remote > hybrid > onsite.
    """
    haystack = " ".join(filter(None, [location or "", summary or ""]))
    if not haystack:
        return MODALITY_UNKNOWN

    if _MODALITY_REMOTE_PATTERN.search(haystack):
        return MODALITY_REMOTE
    if _MODALITY_HYBRID_PATTERN.search(haystack):
        return MODALITY_HYBRID
    if _MODALITY_ONSITE_PATTERN.search(haystack):
        return MODALITY_ONSITE
    return MODALITY_UNKNOWN
