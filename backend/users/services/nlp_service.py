"""Servicio de NLP usando spaCy.

Después del Commit 4 mantiene solo lo que tiene un caller real:
  - `calculate_text_similarity` (usado por `matching_service` en modo semántico)
  - `extract_entities` (primitiva útil para futuras features)

Las funciones `extract_skills_nlp`, `extract_key_phrases` y `generate_summary`
se borraron porque:
  - `extract_skills_nlp`: la cubre `users.adapters.gemini_analyzer` con mejor precisión
  - `extract_key_phrases`: no tenía callers
  - `generate_summary`: solo tomaba las primeras N oraciones (truncado disfrazado)

TODO: migrar el modelo a `es_core_news_md` — CVs y ofertas son en español y
el modelo inglés `en_core_web_sm` no tiene vectores entrenados, lo que hace
que `calculate_text_similarity` devuelva valores casi aleatorios.
"""

import logging

logger = logging.getLogger(__name__)


class NLPService:
    """Servicio para procesamiento de lenguaje natural"""

    _nlp = None
    _SPACY_MODEL = "en_core_web_sm"

    @classmethod
    def get_nlp_model(cls):
        """Lazy loader del modelo spaCy. Si el modelo no está instalado,
        loguea el error y devuelve None — las funciones que dependan de él
        degradan a su valor default sin romper la app.
        """
        if cls._nlp is None:
            try:
                import spacy

                cls._nlp = spacy.load(cls._SPACY_MODEL)
                logger.info("spaCy model %s loaded", cls._SPACY_MODEL)
            except OSError:
                logger.warning(
                    "spaCy model %s no instalado — el matching semántico "
                    "se desactiva. Instalar con: python -m spacy download %s",
                    cls._SPACY_MODEL,
                    cls._SPACY_MODEL,
                )
                cls._nlp = None
            except Exception as e:
                logger.error("Failed to load spaCy model: %s", e)
                cls._nlp = None
        return cls._nlp

    @classmethod
    def extract_entities(cls, text: str) -> dict[str, list[str]]:
        """Extrae entidades nombradas (personas, organizaciones, lugares).

        Returns:
            Dict con entidades agrupadas por tipo (PERSON, ORG, GPE, etc.).
            Dict vacío si el modelo no está disponible o el texto está vacío.
        """
        nlp = cls.get_nlp_model()
        if not nlp or not text:
            return {}

        try:
            doc = nlp(text)
            entities: dict[str, list[str]] = {}
            for ent in doc.ents:
                bucket = entities.setdefault(ent.label_, [])
                if ent.text not in bucket:
                    bucket.append(ent.text)
            return entities
        except Exception as e:
            logger.error("Error extracting entities: %s", e)
            return {}

    @classmethod
    def calculate_text_similarity(cls, text1: str, text2: str) -> float:
        """Similaridad semántica entre dos textos (0.0 a 1.0).

        Usado por `JobMatchingService._find_semantic_matches`.
        Devuelve 0.0 si el modelo no está disponible o no tiene vectores.
        """
        nlp = cls.get_nlp_model()
        if not nlp or not text1 or not text2:
            return 0.0

        try:
            return nlp(text1).similarity(nlp(text2))
        except Exception as e:
            logger.error("Error calculating similarity: %s", e)
            return 0.0
