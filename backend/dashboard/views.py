from users.models import *
from rest_framework import status
from django.shortcuts import render
from rest_framework.views import APIView
from users.serializers import UserProfileSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class dashboardUserList(APIView):
    
    def get(self, request):
        users = UserProfile.objects.all()
        
        for user in users:
            print(user.user.email)
        
        serializer = UserProfileSerializer(users, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
