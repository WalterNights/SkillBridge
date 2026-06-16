"""Interfaz pública para analizadores de CV.

El backend habla con esta abstracción, NO directamente con el SDK de Gemini.
Eso permite cambiar de proveedor (Gemini → Claude → OpenAI) sin reescribir
la lógica de la vista ni de las tasks de Celery.

Implementaciones disponibles:
  - `users.adapters.gemini_analyzer.GeminiCVAnalyzer` (default)

Para agregar un proveedor nuevo:
  1. Crear un módulo nuevo en `users.adapters/`
  2. Implementar la subclase respetando este contrato
  3. Registrarla en `users.services.cv_analysis_service.get_cv_analyzer`
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class CVAnalyzerError(Exception):
    """Error genérico de un proveedor de análisis de CV."""


class CVAnalyzer(ABC):
    """Contrato que toda implementación de análisis de CV debe respetar."""

    @abstractmethod
    def validate(self, cv_file: Any) -> tuple[bool, Optional[str]]:
        """Valida el archivo antes de gastar cuota de IA.

        Returns:
            `(True, None)` si el archivo es procesable.
            `(False, "razón")` si no lo es.
        """

    @abstractmethod
    def analyze(self, cv_file: Any) -> dict:
        """Extrae datos estructurados del CV.

        Returns:
            Dict con el contrato público actual (ver test_cv_upload.py):
              first_name, last_name, full_name,
              phone_code, phone_number, country, city,
              professional_title, summary, skills,
              education (list), experience (list),
              linkedin_url, portfolio_url

        Raises:
            CVAnalyzerError o subclases ante fallas del proveedor.
        """
