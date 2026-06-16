"""Factory de `CVAnalyzer` — punto único de entrada para vistas y tasks.

Selecciona la implementación correcta según `CV_ANALYZER_PROVIDER` en `.env`.
Hoy solo está implementado `gemini`. Si en el futuro agregamos `claude` o
`openai`, basta con crear el adapter respectivo y mapearlo aquí.
"""

from __future__ import annotations

from decouple import config

from users.adapters.cv_analyzer_base import CVAnalyzer, CVAnalyzerError


def get_cv_analyzer() -> CVAnalyzer:
    """Devuelve una instancia del analizador configurado en el entorno.

    Por defecto: Gemini. Para cambiar de proveedor, setear
    `CV_ANALYZER_PROVIDER=claude` (o el que toque) y reiniciar el servicio.
    """
    provider = config("CV_ANALYZER_PROVIDER", default="gemini").lower()

    if provider == "gemini":
        from users.adapters.gemini_analyzer import GeminiCVAnalyzer

        return GeminiCVAnalyzer(
            api_key=config("GEMINI_API_KEY", default=None),
            model_name=config("GEMINI_MODEL", default="gemini-2.0-flash-exp"),
        )

    raise CVAnalyzerError(
        f"CV_ANALYZER_PROVIDER='{provider}' no implementado. " f"Opciones válidas: gemini"
    )
