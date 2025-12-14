"""
Tareas asíncronas para el módulo de users.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(name='users.analyze_cv_async')
def analyze_cv_async(cv_file_path: str, user_id: int):
    """
    Tarea asíncrona para análisis de CV usando Gemini AI.
    
    Args:
        cv_file_path: Ruta del archivo CV guardado temporalmente
        user_id: ID del usuario propietario del CV
        
    Returns:
        Dict con datos extraídos del CV
    """
    from users.services.gemini_cv_service import GeminiCVService
    from users.services.profile_service import ProfileService
    from users.models import User
    
    logger.info(f"Starting async CV analysis with Gemini for user {user_id}")
    
    try:
        # Inicializar servicio de Gemini
        gemini_service = GeminiCVService()
        
        # Abrir archivo CV
        with open(cv_file_path, 'rb') as cv_file:
            # Crear objeto similar a UploadedFile para compatibilidad
            class FileWrapper:
                def __init__(self, file, filename):
                    self.file = file
                    self.name = filename
                    self.size = 0
                
                def seek(self, pos):
                    return self.file.seek(pos)
                
                def read(self):
                    return self.file.read()
            
            file_wrapper = FileWrapper(cv_file, cv_file_path)
            
            # Analizar CV con Gemini
            extracted_data = gemini_service.analyze_cv(file_wrapper)
            
            # Actualizar perfil del usuario si existe
            try:
                user = User.objects.get(id=user_id)
                profile = ProfileService.get_profile_by_user(user)
                
                if profile:
                    ProfileService.update_profile(profile, extracted_data)
                    logger.info(f"Profile updated for user {user_id} after CV analysis")
                else:
                    ProfileService.create_profile(user, extracted_data)
                    logger.info(f"Profile created for user {user_id} after CV analysis")
                    
            except User.DoesNotExist:
                logger.warning(f"User {user_id} not found")
        
        logger.info(f"CV analysis completed with Gemini for user {user_id}")
        
        return {
            'status': 'success',
            'user_id': user_id,
            'data': extracted_data
        }
        
    except Exception as e:
        logger.error(f"CV analysis task failed for user {user_id}: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'user_id': user_id,
            'error': str(e)
        }
