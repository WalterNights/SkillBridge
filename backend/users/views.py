from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from users.models import User, UserProfile
from users.serializers import UserSerializer, UserProfileSerializer
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
    
    def post(self, request, *args, **kwargs):
        file = request.FILES.get("resume")
        
        try:
            # Inicializar servicio de Gemini
            gemini_service = GeminiCVService()
            
            # Validar archivo
            is_valid, error_message = gemini_service.validate_cv_file(file)
            if not is_valid:
                return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
            
            # Analizar CV con Gemini AI
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
                "education": extracted_data.get('education', ''),
                "skills": extracted_data.get('skills', ''),
                "experience": extracted_data.get('experience', ''),
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
            return Response(
                {"error": f"Error al analizar el archivo: {str(e)}"}, 
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