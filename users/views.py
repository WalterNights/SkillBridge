import fitz
from .models import *
from .serializers import *
from rest_framework import status
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from users.utils.cv_parser import extract_text_from_resume
from users.utils.cv_analyzer import simple_profile_parser
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
    def post(self, request):
        file = request.FILES.get("resume")
        print("Archivo recibido", file)
        if not file:
            return Response({"error": "No se ha proporcionado un archiv"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            file_data = file.read()
            if not file_data:
                return Response({"error": "El archivo está vacío"}, status=status.HTTP_400_BAD_REQUEST)
            doc = fitz.open(stream=file_data, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            print("🧾 Texto extraído del CV:")
            print(text[:300])
            profile_data = simple_profile_parser(text)
            print("✅ Datos extraídos:", profile_data)    
        except Exception as e:
            print("❌ Error al analizar el archivo CV:", str(e))
            return Response({"error": "Error al analizar el archivo"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(profile_data, status=status.HTTP_200_OK)
    

class UserProfileCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        data = request.data.copy() 
        
        if "resume" in request.FILES:
            resume_text = extract_text_from_resume(request.FILES["resume"])
            parsed_data = simple_profile_parser(resume_text)
            data.update(parsed_data)
        
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