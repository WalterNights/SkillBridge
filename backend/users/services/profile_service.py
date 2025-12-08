"""
Servicio para gestión de perfiles de usuario.
"""
import logging
from typing import Optional, Dict
from django.contrib.auth.models import User

from users.models import UserProfile

logger = logging.getLogger(__name__)


class ProfileService:
    """Servicio para operaciones con perfiles de usuario"""
    
    @staticmethod
    def get_profile_by_user(user: User) -> Optional[UserProfile]:
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
    
    @staticmethod
    def create_profile(user: User, profile_data: Dict) -> UserProfile:
        """
        Crea un nuevo perfil de usuario.
        
        Args:
            user: Instancia de User
            profile_data: Diccionario con datos del perfil
            
        Returns:
            UserProfile creado
        """
        logger.info(f"Creating profile for user {user.username}")
        
        profile = UserProfile.objects.create(
            user=user,
            title=profile_data.get('title', ''),
            skills=profile_data.get('skills', ''),
            city=profile_data.get('city', ''),
            summary=profile_data.get('summary', ''),
            country=profile_data.get('country', ''),
            full_name=profile_data.get('full_name', '')
        )
        
        logger.info(f"Profile created successfully for user {user.username}")
        return profile
    
    @staticmethod
    def update_profile(profile: UserProfile, profile_data: Dict) -> UserProfile:
        """
        Actualiza un perfil existente.
        
        Args:
            profile: Instancia de UserProfile
            profile_data: Diccionario con nuevos datos
            
        Returns:
            UserProfile actualizado
        """
        logger.info(f"Updating profile for user {profile.user.username}")
        
        # Actualizar campos si existen en profile_data
        fields_to_update = ['title', 'skills', 'city', 'summary', 'country', 'full_name']
        
        for field in fields_to_update:
            if field in profile_data:
                setattr(profile, field, profile_data[field])
        
        profile.save()
        logger.info(f"Profile updated successfully for user {profile.user.username}")
        return profile
    
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
