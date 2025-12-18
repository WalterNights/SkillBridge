"""
Servicio para análisis de CVs y extracción de información.
"""
import logging
from typing import Dict, Optional

from users.utils.cv_analyzer import analyze_cv
from users.services.nlp_service import NLPService

logger = logging.getLogger(__name__)


class CVAnalyzerService:
    """Servicio para análisis y extracción de datos de CVs"""
    
    @staticmethod
    def analyze_cv(cv_file, use_nlp: bool = True) -> Dict[str, str]:
        """
        Analiza un CV y extrae información relevante.
        
        Args:
            cv_file: Archivo de CV (PDF o DOCX)
            use_nlp: Si True, usa NLP para mejorar extracción (default: True)
            
        Returns:
            Diccionario con datos extraídos
        """
        logger.info(f"Starting CV analysis for file: {cv_file.name}")
        
        try:
            # Determinar tipo de archivo
            file_extension = cv_file.name.split('.')[-1].lower()
            
            # Extraer información usando utilidad existente
            extracted_data = analyze_cv(cv_file, filetype=file_extension)
            
            # Mapear campos al formato esperado por el servicio
            service_data = {
                'title': extracted_data.get('professional_title', ''),
                'skills': extracted_data.get('skills', ''),
                'city': extracted_data.get('city', ''),
                'summary': extracted_data.get('summary', ''),
                'country': extracted_data.get('phone_code', ''),  # País basado en código
                'full_name': f"{extracted_data.get('first_name', '')} {extracted_data.get('last_name', '')}".strip(),
                'first_name': extracted_data.get('first_name', ''),
                'last_name': extracted_data.get('last_name', ''),
                'phone': f"{extracted_data.get('phone_code', '')} {extracted_data.get('phone_number', '')}".strip(),
                'education': extracted_data.get('education', []),  # Ahora puede ser array o string
                'experience': extracted_data.get('experience', []),  # Ahora puede ser array o string
                'linkedin_url': extracted_data.get('linkedin_url', ''),
                'portfolio_url': extracted_data.get('portfolio_url', ''),
            }
            
            # Mejorar con NLP si está habilitado
            if use_nlp:
                try:
                    service_data = CVAnalyzerService.enhance_with_nlp(service_data, cv_file)
                except Exception as nlp_error:
                    logger.warning(f"NLP enhancement failed: {str(nlp_error)}")
                    # Continuar con datos básicos si NLP falla
            
            logger.info(f"CV analysis completed successfully: {service_data.get('full_name')}")
            return service_data
            
        except Exception as e:
            logger.error(f"Error analyzing CV: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def enhance_with_nlp(extracted_data: Dict[str, str], cv_file) -> Dict[str, str]:
        """
        Mejora los datos extraídos usando NLP.
        
        Args:
            extracted_data: Datos básicos extraídos
            cv_file: Archivo CV para re-analizar con NLP
            
        Returns:
            Datos mejorados con NLP
        """
        # Leer todo el contenido del CV para NLP
        from pdfplumber import open as open_pdf
        from docx import Document
        
        full_text = ""
        file_extension = cv_file.name.split('.')[-1].lower()
        
        try:
            # Reiniciar el puntero del archivo
            cv_file.seek(0)
            
            if file_extension == 'pdf':
                with open_pdf(cv_file) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            full_text += text + " "
            elif file_extension == 'docx':
                doc = Document(cv_file)
                for para in doc.paragraphs:
                    full_text += para.text + " "
            
            # Mejorar summary con NLP si no existe
            if not extracted_data.get('summary') and full_text:
                extracted_data['summary'] = NLPService.generate_summary(full_text, max_sentences=3)
            
            # Extraer skills adicionales con NLP
            nlp_skills = NLPService.extract_skills_nlp(full_text)
            if nlp_skills:
                existing_skills = extracted_data.get('skills', '').lower().split(',')
                existing_skills = [s.strip() for s in existing_skills if s.strip()]
                
                # Agregar skills nuevas encontradas por NLP
                for skill in nlp_skills:
                    if skill not in existing_skills:
                        existing_skills.append(skill)
                
                extracted_data['skills'] = ', '.join(existing_skills)
            
            # Extraer full_name con NLP si no existe
            if not extracted_data.get('full_name') or extracted_data.get('full_name').strip() == '':
                entities = NLPService.extract_entities(full_text)
                persons = entities.get('PERSON', [])
                if persons:
                    extracted_data['full_name'] = persons[0]  # Primera persona encontrada
            
        except Exception as e:
            logger.error(f"Error in NLP enhancement: {str(e)}")
        
        return extracted_data
    
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
        
        # Validar tamaño (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB en bytes
        if cv_file.size > max_size:
            return False, "El archivo excede el tamaño máximo de 5MB"
        
        return True, None
    
    @staticmethod
    def extract_skills_list(cv_file) -> list:
        """
        Extrae las skills del CV como lista.
        
        Args:
            cv_file: Archivo de CV
            
        Returns:
            Lista de skills
        """
        try:
            file_extension = cv_file.name.split('.')[-1].lower()
            extracted_data = analyze_cv(cv_file, filetype=file_extension)
            skills_str = extracted_data.get('skills', '')
            
            if not skills_str:
                return []
            
            # Separar por comas y limpiar
            return [
                skill.strip() 
                for skill in skills_str.split(',') 
                if skill.strip()
            ]
        except Exception as e:
            logger.error(f"Error extracting skills list: {str(e)}")
            return []
    @staticmethod
    def extract_skills_list(cv_file) -> list:
        """
        Extrae las skills del CV como lista.
        
        Args:
            cv_file: Archivo de CV
            
        Returns:
            Lista de skills
        """
        skills_str = extract_skills(cv_file)
        if not skills_str:
            return []
        
        # Separar por comas y limpiar
        return [
            skill.strip() 
            for skill in skills_str.split(',') 
            if skill.strip()
        ]
