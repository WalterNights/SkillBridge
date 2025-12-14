"""
Servicio de análisis de CV usando Gemini AI
"""
import os
import logging
import json
from typing import Dict, Optional
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)


class GeminiCVService:
    """Servicio para analizar CVs usando Google Gemini AI"""
    
    def __init__(self):
        """Inicializa el servicio con la API key de Gemini"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY no encontrada en las variables de entorno")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def extract_text_from_file(self, cv_file) -> str:
        """
        Extrae el texto del archivo CV (PDF o DOCX).
        
        Args:
            cv_file: Archivo de CV
            
        Returns:
            Texto extraído del CV
        """
        import pdfplumber
        import docx
        
        file_extension = cv_file.name.split('.')[-1].lower()
        text = ""
        
        try:
            # Reiniciar el puntero del archivo
            cv_file.seek(0)
            
            if file_extension == 'pdf':
                with pdfplumber.open(cv_file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            
            elif file_extension == 'docx':
                doc = docx.Document(cv_file)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            
            else:
                raise ValueError(f"Formato de archivo no soportado: {file_extension}")
            
            return text.strip()
        
        except Exception as e:
            logger.error(f"Error extrayendo texto del CV: {str(e)}")
            raise
    
    def analyze_cv(self, cv_file) -> Dict[str, str]:
        """
        Analiza un CV usando Gemini AI y extrae información estructurada.
        
        Args:
            cv_file: Archivo de CV (PDF o DOCX)
            
        Returns:
            Diccionario con los datos extraídos del CV
        """
        try:
            # Extraer texto del archivo
            cv_text = self.extract_text_from_file(cv_file)
            
            if not cv_text or len(cv_text.strip()) < 50:
                raise ValueError("El CV no contiene suficiente texto para analizar")
            
            # Crear el prompt para Gemini
            prompt = self._create_analysis_prompt(cv_text)
            
            # Llamar a Gemini API
            logger.info("Enviando CV a Gemini para análisis...")
            response = self.model.generate_content(prompt)
            
            # Parsear la respuesta JSON
            result_text = response.text.strip()
            
            # Extraer el JSON de la respuesta (a veces viene con markdown)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Parsear el JSON
            extracted_data = json.loads(result_text)
            
            # Validar y normalizar los datos
            normalized_data = self._normalize_extracted_data(extracted_data)
            
            logger.info(f"CV analizado exitosamente: {normalized_data.get('full_name', 'Sin nombre')}")
            return normalized_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta JSON de Gemini: {str(e)}")
            logger.error(f"Respuesta recibida: {result_text[:500]}")
            raise ValueError("No se pudo parsear la respuesta de Gemini AI")
        
        except Exception as e:
            logger.error(f"Error en análisis de CV con Gemini: {str(e)}", exc_info=True)
            raise
    
    def _create_analysis_prompt(self, cv_text: str) -> str:
        """
        Crea el prompt para que Gemini analice el CV.
        
        Args:
            cv_text: Texto completo del CV
            
        Returns:
            Prompt formateado para Gemini
        """
        return f"""Analiza el siguiente CV y extrae la información en formato JSON estrictamente estructurado.

CV:
{cv_text}

Instrucciones:
- Extrae ÚNICAMENTE la información que esté claramente presente en el CV
- Si un campo no está presente, deja el valor vacío ""
- Para las skills, lista solo las más relevantes y técnicas
- El summary debe ser un resumen profesional conciso (máximo 3 líneas)
- El título profesional debe ser la posición o rol principal
- Para educación y experiencia, proporciona un resumen estructurado

Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura exacta:
{{
    "first_name": "nombre",
    "last_name": "apellido",
    "full_name": "nombre completo",
    "phone_code": "código de país con +",
    "phone_number": "número sin código de país",
    "country": "país",
    "city": "ciudad",
    "professional_title": "título profesional o rol principal",
    "summary": "resumen profesional breve",
    "skills": "skill1, skill2, skill3, ...",
    "education": "resumen de educación",
    "experience": "resumen de experiencia laboral",
    "linkedin_url": "URL de LinkedIn si existe",
    "portfolio_url": "URL de portafolio o GitHub si existe"
}}

Responde SOLO con el JSON, sin texto adicional, sin markdown, sin explicaciones."""
    
    def _normalize_extracted_data(self, data: Dict) -> Dict[str, str]:
        """
        Normaliza y valida los datos extraídos.
        
        Args:
            data: Datos extraídos de Gemini
            
        Returns:
            Datos normalizados
        """
        # Campos esperados con valores por defecto
        expected_fields = {
            'first_name': '',
            'last_name': '',
            'full_name': '',
            'phone_code': '',
            'phone_number': '',
            'country': '',
            'city': '',
            'professional_title': '',
            'title': '',  # Alias para compatibilidad
            'summary': '',
            'skills': '',
            'education': '',
            'experience': '',
            'linkedin_url': '',
            'portfolio_url': '',
        }
        
        # Combinar datos extraídos con valores por defecto
        normalized = {key: data.get(key, default).strip() if data.get(key) else default 
                     for key, default in expected_fields.items()}
        
        # Si no hay full_name pero hay first_name y last_name, combinarlos
        if not normalized['full_name'] and (normalized['first_name'] or normalized['last_name']):
            normalized['full_name'] = f"{normalized['first_name']} {normalized['last_name']}".strip()
        
        # Copiar professional_title a title para compatibilidad con código existente
        if not normalized['title'] and normalized['professional_title']:
            normalized['title'] = normalized['professional_title']
        elif normalized['title'] and not normalized['professional_title']:
            normalized['professional_title'] = normalized['title']
        
        # Limpiar URLs
        for url_field in ['linkedin_url', 'portfolio_url']:
            if normalized[url_field] and not normalized[url_field].startswith('http'):
                normalized[url_field] = ''
        
        return normalized
    
    @staticmethod
    def validate_cv_file(cv_file) -> tuple[bool, Optional[str]]:
        """
        Valida que el archivo de CV sea válido.
        
        Args:
            cv_file: Archivo a validar
            
        Returns:
            Tupla (is_valid, error_message)
        """
        if not cv_file:
            return False, "No se proporcionó ningún archivo"
        
        # Validar extensión
        allowed_extensions = ['pdf', 'docx']
        file_extension = cv_file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            return False, f"Formato no permitido. Use: {', '.join(allowed_extensions)}"
        
        # Validar tamaño (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB en bytes
        if cv_file.size > max_size:
            return False, "El archivo excede el tamaño máximo de 10MB"
        
        return True, None
