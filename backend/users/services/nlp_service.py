"""
Servicio de NLP usando spaCy para análisis avanzado de texto.
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class NLPService:
    """Servicio para procesamiento de lenguaje natural"""
    
    _nlp = None
    
    @classmethod
    def get_nlp_model(cls):
        """
        Obtiene el modelo de spaCy (lazy loading).
        Descarga el modelo en primer uso si no existe.
        """
        if cls._nlp is None:
            try:
                import spacy
                try:
                    cls._nlp = spacy.load("en_core_web_sm")
                    logger.info("spaCy model loaded successfully")
                except OSError:
                    logger.info("Downloading spaCy model en_core_web_sm...")
                    import subprocess
                    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
                    cls._nlp = spacy.load("en_core_web_sm")
                    logger.info("spaCy model downloaded and loaded")
            except Exception as e:
                logger.error(f"Failed to load spaCy model: {str(e)}")
                cls._nlp = None
        return cls._nlp
    
    @classmethod
    def extract_entities(cls, text: str) -> Dict[str, List[str]]:
        """
        Extrae entidades nombradas del texto (personas, organizaciones, lugares, etc).
        
        Args:
            text: Texto a analizar
            
        Returns:
            Dict con entidades agrupadas por tipo
        """
        nlp = cls.get_nlp_model()
        if not nlp or not text:
            return {}
        
        try:
            doc = nlp(text)
            entities = {}
            
            for ent in doc.ents:
                entity_type = ent.label_
                if entity_type not in entities:
                    entities[entity_type] = []
                if ent.text not in entities[entity_type]:
                    entities[entity_type].append(ent.text)
            
            return entities
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return {}
    
    @classmethod
    def extract_skills_nlp(cls, text: str) -> List[str]:
        """
        Extrae skills técnicas del texto usando NLP.
        Identifica sustantivos y términos técnicos.
        
        Args:
            text: Texto del CV
            
        Returns:
            Lista de skills identificadas
        """
        nlp = cls.get_nlp_model()
        if not nlp or not text:
            return []
        
        try:
            doc = nlp(text.lower())
            skills = []
            
            # Lista de skills técnicas comunes
            technical_skills = {
                'python', 'java', 'javascript', 'typescript', 'react', 'angular',
                'vue', 'node', 'django', 'flask', 'spring', 'docker', 'kubernetes',
                'aws', 'azure', 'gcp', 'sql', 'nosql', 'mongodb', 'postgresql',
                'mysql', 'redis', 'git', 'ci/cd', 'jenkins', 'terraform', 'ansible',
                'linux', 'windows', 'macos', 'api', 'rest', 'graphql', 'microservices',
                'agile', 'scrum', 'html', 'css', 'sass', 'webpack', 'babel',
                'testing', 'jest', 'pytest', 'selenium', 'cypress'
            }
            
            # Extraer tokens que coinciden con skills técnicas
            for token in doc:
                if token.text in technical_skills and token.text not in skills:
                    skills.append(token.text)
            
            # Extraer entidades de organización que pueden ser tecnologías
            entities = cls.extract_entities(text)
            for org in entities.get('ORG', []):
                org_lower = org.lower()
                if org_lower in technical_skills and org_lower not in skills:
                    skills.append(org_lower)
            
            return skills
        except Exception as e:
            logger.error(f"Error extracting skills with NLP: {str(e)}")
            return []
    
    @classmethod
    def calculate_text_similarity(cls, text1: str, text2: str) -> float:
        """
        Calcula similaridad semántica entre dos textos usando vectores de spaCy.
        
        Args:
            text1: Primer texto
            text2: Segundo texto
            
        Returns:
            Float entre 0 y 1 indicando similaridad (1 = idénticos)
        """
        nlp = cls.get_nlp_model()
        if not nlp or not text1 or not text2:
            return 0.0
        
        try:
            doc1 = nlp(text1)
            doc2 = nlp(text2)
            
            return doc1.similarity(doc2)
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    @classmethod
    def extract_key_phrases(cls, text: str, top_n: int = 10) -> List[str]:
        """
        Extrae frases clave del texto usando análisis de chunks nominales.
        
        Args:
            text: Texto a analizar
            top_n: Número de frases clave a retornar
            
        Returns:
            Lista de frases clave
        """
        nlp = cls.get_nlp_model()
        if not nlp or not text:
            return []
        
        try:
            doc = nlp(text)
            phrases = []
            
            # Extraer chunks nominales
            for chunk in doc.noun_chunks:
                phrase = chunk.text.strip()
                if len(phrase.split()) >= 2 and phrase not in phrases:  # Al menos 2 palabras
                    phrases.append(phrase)
            
            return phrases[:top_n]
        except Exception as e:
            logger.error(f"Error extracting key phrases: {str(e)}")
            return []
    
    @classmethod
    def generate_summary(cls, text: str, max_sentences: int = 3) -> str:
        """
        Genera un resumen del texto seleccionando las oraciones más relevantes.
        
        Args:
            text: Texto completo
            max_sentences: Número máximo de oraciones en el resumen
            
        Returns:
            Texto resumido
        """
        nlp = cls.get_nlp_model()
        if not nlp or not text:
            return ""
        
        try:
            doc = nlp(text)
            sentences = [sent.text.strip() for sent in doc.sents]
            
            if len(sentences) <= max_sentences:
                return text
            
            # Seleccionar las primeras N oraciones
            # Puede mejorar con análisis de importancia más sofisticado
            summary_sentences = sentences[:max_sentences]
            
            return ' '.join(summary_sentences)
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return text[:500]  # Fallback: primeros 500 caracteres
