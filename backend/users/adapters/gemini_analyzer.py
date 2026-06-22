"""Implementación de `CVAnalyzer` usando Google Gemini AI.

Mueve aquí toda la lógica que vivía en `users.services.gemini_cv_service`
para que el `CVAnalyzer` quede como un adapter puro al SDK externo.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import google.generativeai as genai

from users.adapters.cv_analyzer_base import CVAnalyzer, CVAnalyzerError

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = ("pdf", "docx")
MIN_TEXT_LENGTH = 50

# domain.tld optionally followed by /path — matches "linkedin.com/in/x" but
# not free text like "ver mi LinkedIn". Used to rescue schemeless URLs that
# the LLM forgot to prefix with https://.
_URL_LIKE = re.compile(r"^[\w.-]+\.[a-z]{2,}(?:/.*)?$", re.IGNORECASE)

_PROMPT_TEMPLATE = """Analiza el siguiente CV y extrae la información en formato JSON estrictamente estructurado.

CV:
{cv_text}

Instrucciones:
- Extrae ÚNICAMENTE la información que esté claramente presente en el CV
- Si un campo no está presente, deja el valor vacío "" o array vacío []
- Para las skills, lista solo las más relevantes y técnicas separadas por coma
- El summary debe ser un resumen profesional conciso (máximo 3 líneas)
- El título profesional debe ser la posición o rol principal
- Para educación y experiencia, proporciona arrays con objetos estructurados
- Las fechas deben estar en formato "Mes Año" (ej: "Marzo 2022")
- Si la fecha de fin es actual, usa "Actual" o "Presente"

Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura exacta:
{{
    "first_name": "nombre",
    "last_name": "apellido",
    "full_name": "nombre completo",
    "email": "dirección de correo electrónico",
    "phone_code": "código de país con +",
    "phone_number": "número sin código de país",
    "country": "país",
    "city": "ciudad",
    "professional_title": "título profesional o rol principal",
    "summary": "resumen profesional breve",
    "skills": "skill1, skill2, skill3, ...",
    "education": [
        {{
            "institution": "nombre de la institución",
            "title": "título o carrera obtenida",
            "start_date": "Mes Año",
            "end_date": "Mes Año o Actual",
            "location_city": "ciudad",
            "location_country": "país"
        }}
    ],
    "experience": [
        {{
            "company": "nombre de la empresa",
            "position": "cargo o puesto",
            "start_date": "Mes Año",
            "end_date": "Mes Año o Actual",
            "location_city": "ciudad",
            "location_country": "país",
            "description": "descripción breve de responsabilidades y logros"
        }}
    ],
    "linkedin_url": "URL de LinkedIn si existe (incluye https://)",
    "portfolio_url": "URL de portafolio o GitHub si existe (incluye https://)"
}}

Responde SOLO con el JSON, sin texto adicional, sin markdown, sin explicaciones."""


class GeminiCVAnalyzer(CVAnalyzer):
    """Analiza CVs delegando en la API de Google Gemini."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        if not api_key:
            raise CVAnalyzerError("GEMINI_API_KEY no provista")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)

    # ---- API pública del contrato ---------------------------------------

    def validate(self, cv_file: Any) -> tuple[bool, str | None]:
        if not cv_file:
            return False, "No se proporcionó ningún archivo"

        ext = cv_file.name.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Formato no permitido. Use: {', '.join(ALLOWED_EXTENSIONS)}"

        if cv_file.size > MAX_FILE_SIZE_BYTES:
            return (
                False,
                f"El archivo excede el tamaño máximo de {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
            )

        return True, None

    def analyze(self, cv_file: Any) -> dict:
        cv_text = self._extract_text(cv_file)
        if len(cv_text.strip()) < MIN_TEXT_LENGTH:
            raise CVAnalyzerError("El CV no contiene suficiente texto para analizar")

        logger.info("Enviando CV a Gemini para análisis...")
        response = self._model.generate_content(_PROMPT_TEMPLATE.format(cv_text=cv_text))

        raw = _strip_markdown_fences(response.text.strip())
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("Respuesta de Gemini no es JSON válido: %s", e)
            logger.debug("Snippet: %s", raw[:500])
            raise CVAnalyzerError("Respuesta de Gemini inválida") from e

        return _normalize_extracted_data(parsed)

    # ---- Helpers privados -----------------------------------------------

    def _extract_text(self, cv_file: Any) -> str:
        """Extrae texto plano de un PDF o DOCX. Lectura local, sin red."""
        import docx
        import pdfplumber

        ext = cv_file.name.rsplit(".", 1)[-1].lower()
        cv_file.seek(0)

        if ext == "pdf":
            with pdfplumber.open(cv_file) as pdf:
                return "\n".join((page.extract_text() or "") for page in pdf.pages).strip()

        if ext == "docx":
            doc = docx.Document(cv_file)
            return "\n".join(p.text for p in doc.paragraphs).strip()

        raise CVAnalyzerError(f"Formato no soportado: {ext}")


# ---- Module-level helpers (reutilizables y testeables sin instanciar) ----


def _strip_markdown_fences(text: str) -> str:
    """Gemini a veces envuelve el JSON en ```json ... ```. Lo limpiamos."""
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text


def _normalize_extracted_data(data: dict) -> dict:
    """Asegura el contrato público del endpoint /resume-analyzer/."""
    text_fields = (
        "first_name",
        "last_name",
        "full_name",
        "email",
        "phone_code",
        "phone_number",
        "country",
        "city",
        "professional_title",
        "title",
        "summary",
        "skills",
        "linkedin_url",
        "portfolio_url",
    )
    out: dict = {}
    for key in text_fields:
        value = data.get(key, "")
        out[key] = value.strip() if isinstance(value, str) else ""

    # Listas o strings (Gemini a veces devuelve string en lugar de lista)
    for key in ("education", "experience"):
        value = data.get(key, [])
        if isinstance(value, list):
            out[key] = value
        elif isinstance(value, str):
            out[key] = value.strip()
        else:
            out[key] = []

    # full_name fallback
    if not out["full_name"] and (out["first_name"] or out["last_name"]):
        out["full_name"] = f"{out['first_name']} {out['last_name']}".strip()

    # title ↔ professional_title (compat con frontend viejo)
    if not out["title"] and out["professional_title"]:
        out["title"] = out["professional_title"]
    elif out["title"] and not out["professional_title"]:
        out["professional_title"] = out["title"]

    # URLs deben ser absolutas. Si Gemini devuelve algo schemeless pero
    # claramente URL-like (linkedin.com/in/x, github.com/y) le prependemos
    # https:// en vez de tirarlo — el caso del usuario que pone su LinkedIn
    # como "linkedin.com/in/usuario" en el CV es el común, no el raro.
    for url_key in ("linkedin_url", "portfolio_url"):
        val = out[url_key]
        if not val or val.startswith("http"):
            continue
        if _URL_LIKE.match(val):
            out[url_key] = f"https://{val}"
        else:
            out[url_key] = ""

    return out
