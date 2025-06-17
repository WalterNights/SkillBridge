from .models import *
from .serializers import *
from rest_framework import status
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class UserRegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Usuario creado exitosamente", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.error, status=status.HTTP_400_BAD_REQUEST)
    

class UserProfileCreateView(APIView):
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