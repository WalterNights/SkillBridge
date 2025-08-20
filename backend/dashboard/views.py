from users.models import *
from rest_framework import status
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from users.serializers import UserProfileSerializer
from rest_framework.permissions import IsAuthenticated


class dashboardUserList(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        users = UserProfile.objects.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
class dashboardUserData(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.daya, status=status.HTTP_200_OK)
        
