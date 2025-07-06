from .models import *
from .serializers import *
from rest_framework import status
from django.shortcuts import render
from users.utils.cv_analyzer import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class UserRegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Usuario creado exitosamente", "data": serializer.data}, status=status.HTTP_201_CREATED)
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
 
class AnalyzerResumeView(APIView):
    parser_classes = [MultiPartParser]
    def post(self, request, *args, **kwargs):
        file = request.FILES.get("resume")
        if not file:
            return Response({"error": "No hay archivo"}, status=status.HTTP_400_BAD_REQUEST)
        file_type = file.name.split('.')[-1].lower()
        if file_type not in ['pdf', 'docx']:
            return Response({"error": "Formato de arcgivo no compatible"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            analyst_result = analyze_cv(file, filetype=file_type)
            default_fields = {
                "first_name": "",
                "last_name": "",
                "number_id": "",
                "phone_code": "",
                "phone_number": "",
                "city": "",
                "professional_title": "",
                "summary": "",
                "education": "",
                "skills": "",
                "experience": "",
                "linkedin_url": "",
                "portfolio_url": "",
            }
            response_data = {**default_fields, **analyst_result}
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            print("❌ Error al analizar el archivo CV:", str(e))
            return Response({"error": "Error al analizar el archivo"}, status=status.HTTP_400_BAD_REQUEST)
    

class UserProfileCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        data = request.data.copy() 
        try:
            profile = user.profile
            serializer = UserProfileSerializer(profile, data=data, partial=True)
        except UserProfile.DoesNotExist:
            serializer = UserProfileSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class UserProfileCheckView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile = request.user.profile
        if not profile.full_name or not profile.city or not profile.phone:
            return Response({"profile_complete": False})
        return Response({"profile_complete": True})
    

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user_id'] = user.id
        data['username'] = user.username
        data['email'] = user.email
        data['rol'] = user.rol
        data['is_profile_complete'] = user.profile.number_id is not None
        return data
    
    
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer