"""
Servicio para gestión de perfiles de usuario.
"""

import logging

from django.contrib.auth.models import User

from users.models import UserProfile

logger = logging.getLogger(__name__)


class ProfileService:
    """Servicio para operaciones con perfiles de usuario"""

    @staticmethod
    def get_profile_by_user(user: User) -> UserProfile | None:
        """
        Obtiene el perfil de un usuario.

        Args:
            user: Instancia de User

        Returns:
            UserProfile o None si no existe
        """
        try:
            return UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            logger.warning(f"Profile not found for user {user.username}")
            return None

    # NOTA: `create_profile` y `update_profile` fueron removidas porque
    # mapeaban a columnas inexistentes (`title`, `full_name`, `country`)
    # y descartaban ~10 campos válidos del modelo. La persistencia
    # ahora se hace via `UserProfileSerializer` desde la view.
    # Si necesitás guardar un perfil programáticamente, instanciá el
    # serializer con `data=...` y llamá `.save(user=user)`.

    @staticmethod
    def profile_exists(user: User) -> bool:
        """
        Verifica si un usuario tiene perfil.

        Args:
            user: Instancia de User

        Returns:
            True si existe, False en caso contrario
        """
        return UserProfile.objects.filter(user=user).exists()

    @staticmethod
    def delete_profile(user: User) -> bool:
        """
        Elimina el perfil de un usuario.

        Args:
            user: Instancia de User

        Returns:
            True si se eliminó, False si no existía
        """
        try:
            profile = UserProfile.objects.get(user=user)
            profile.delete()
            logger.info(f"Profile deleted for user {user.username}")
            return True
        except UserProfile.DoesNotExist:
            logger.warning(f"No profile to delete for user {user.username}")
            return False
