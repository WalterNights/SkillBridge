"""
Tareas asíncronas para el módulo de users.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="users.analyze_cv_async")
def analyze_cv_async(cv_file_path: str, user_id: int):
    """
    Tarea asíncrona para análisis de CV usando Gemini AI.

    Args:
        cv_file_path: Ruta del archivo CV guardado temporalmente
        user_id: ID del usuario propietario del CV

    Returns:
        Dict con datos extraídos del CV
    """
    from users.models import User
    from users.services.cv_analysis_service import get_cv_analyzer
    from users.services.profile_service import ProfileService

    logger.info(f"Starting async CV analysis for user {user_id}")

    try:
        analyzer = get_cv_analyzer()

        # Abrir archivo CV
        with open(cv_file_path, "rb") as cv_file:
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
            extracted_data = analyzer.analyze(file_wrapper)

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

        return {"status": "success", "user_id": user_id, "data": extracted_data}

    except Exception as e:
        logger.error(f"CV analysis task failed for user {user_id}: {e!s}", exc_info=True)
        return {"status": "error", "user_id": user_id, "error": str(e)}
