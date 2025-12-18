from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.mail import send_mail
from django.conf import settings

from users.models import User, UserProfile, PasswordResetToken
from users.serializers import (
    UserSerializer, 
    UserProfileSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer
)
from users.services.profile_service import ProfileService
from users.services.gemini_cv_service import GeminiCVService


class UserRegisterView(APIView):
    """Vista para registro de nuevos usuarios"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Usuario creado exitosamente", "data": serializer.data}, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
 
class AnalyzerResumeView(APIView):
    """Vista para analizar CVs y extraer información usando Gemini AI"""
    parser_classes = [MultiPartParser]
    permission_classes = [AllowAny]  # Permitir acceso sin autenticación
    
    def post(self, request, *args, **kwargs):
        file = request.FILES.get("resume")
        
        if not file:
            return Response(
                {"error": "No se proporcionó ningún archivo"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Initialize Gemini service
            gemini_service = GeminiCVService()
            
            # Validate file
            is_valid, error_message = gemini_service.validate_cv_file(file)
            if not is_valid:
                return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
            
            # Analyze CV with Gemini AI
            extracted_data = gemini_service.analyze_cv(file)
            
            # Formatear respuesta para mantener compatibilidad con el frontend
            response_data = {
                "first_name": extracted_data.get('first_name', ''),
                "last_name": extracted_data.get('last_name', ''),
                "number_id": "",  # Este campo se llena manualmente
                "phone_code": extracted_data.get('phone_code', ''),
                "phone_number": extracted_data.get('phone_number', ''),
                "country": extracted_data.get('country', ''),
                "city": extracted_data.get('city', ''),
                "professional_title": extracted_data.get('professional_title', ''),
                "summary": extracted_data.get('summary', ''),
                "education": extracted_data.get('education', []),  # Puede ser array o string
                "skills": extracted_data.get('skills', ''),
                "experience": extracted_data.get('experience', []),  # Puede ser array o string
                "linkedin_url": extracted_data.get('linkedin_url', ''),
                "portfolio_url": extracted_data.get('portfolio_url', ''),
                "full_name": extracted_data.get('full_name', ''),
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as ve:
            return Response(
                {"error": str(ve)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Log error for debugging but don't expose details to client
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"CV analysis error: {str(e)}", exc_info=True)
            return Response(
                {"error": "Error al analizar el archivo"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de perfiles de usuario.
    
    Endpoints:
    - GET /users/profiles/ - Obtener perfil del usuario autenticado
    - POST /users/profiles/ - Crear o actualizar perfil
    - GET /users/profiles/check/ - Verificar si perfil está completo
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Retorna solo el perfil del usuario autenticado"""
        return UserProfile.objects.filter(user=self.request.user).select_related('user')
    
    def create(self, request):
        """Crea o actualiza el perfil del usuario"""
        user = request.user
        profile_data = request.data.copy()
        
        # Usar servicio de perfil
        if ProfileService.profile_exists(user):
            profile = ProfileService.get_profile_by_user(user)
            updated_profile = ProfileService.update_profile(profile, profile_data)
            serializer = self.get_serializer(updated_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            new_profile = ProfileService.create_profile(user, profile_data)
            serializer = self.get_serializer(new_profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def check(self, request):
        """Verifica si el perfil del usuario está completo"""
        if not ProfileService.profile_exists(request.user):
            return Response(
                {"error": "Profile not found", "profile_complete": False}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        profile = ProfileService.get_profile_by_user(request.user)
        is_complete = all([
            profile.first_name,
            profile.last_name,
            profile.city,
            profile.phone
        ])
        
        return Response({"profile_complete": is_complete}, status=status.HTTP_200_OK)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personalizado para incluir datos de perfil en token"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        
        data['user_id'] = user.id
        data['username'] = user.username
        data['email'] = user.email
        data['rol'] = user.rol
        
        # Usar servicio de perfil
        profile = ProfileService.get_profile_by_user(user)
        if profile:
            data['is_profile_complete'] = profile.number_id is not None
            data['user_name'] = profile.first_name
        else:
            data['is_profile_complete'] = False
            
        return data
    
    
class CustomTokenObtainPairView(TokenObtainPairView):
    """Vista personalizada para obtención de tokens JWT"""
    serializer_class = CustomTokenObtainPairSerializer


class PasswordResetRequestView(APIView):
    """Vista para solicitar restablecimiento de contraseña"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Generar código de 6 dígitos
        code = PasswordResetToken.generate_code()
        
        # Crear token
        token = PasswordResetToken.objects.create(user=user, code=code)
        
        # Enviar email
        subject = 'Código de restablecimiento de contraseña - SkillBridge'
        message = f'''
Hola {user.username},

Has solicitado restablecer tu contraseña en SkillBridge.

Tu código de verificación es: {code}

Este código expirará en 10 minutos.

Si no solicitaste este cambio, ignora este mensaje.

Saludos,
El equipo de SkillBridge
        '''
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return Response({
                "message": "Código de verificación enviado a tu correo",
                "email": email
            }, status=status.HTTP_200_OK)
        except Exception as e:
            # If sending fails, delete the created token
            token.delete()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Email sending error: {type(e).__name__}", exc_info=True)
            return Response({
                "error": "Error al enviar el correo. Intenta nuevamente."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetVerifyView(APIView):
    """Vista para verificar código y restablecer contraseña"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener usuario y token validados
        user = serializer.validated_data['user']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        # Cambiar contraseña
        user.set_password(new_password)
        user.save()
        
        # Marcar token como usado
        token.is_used = True
        token.save()
        
        return Response({
            "message": "Contraseña restablecida exitosamente"
        }, status=status.HTTP_200_OK)