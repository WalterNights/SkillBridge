from .models import *
from django.db.models import Q
from rest_framework import status
from django.shortcuts import render
from users.models import UserProfile
from rest_framework.views import APIView
from rest_framework.response import Response
from jobs.serializers import JobOfferSerializer
from jobs.utils.scraper import scrap_computrabajo
from rest_framework.permissions import IsAuthenticated
from jobs.utils.offer_filter import filter_offers_by_user_skill


class JobScrapingView(APIView):
    def get(self, request):
        user = request.user
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND) 
        
        query = profile.professional_title
        location = profile.city
        new_offers = scrap_computrabajo(query, location)
        filtered_offers = filter_offers_by_user_skill(new_offers, profile.skills)
        
        serializer = JobOfferSerializer(filtered_offers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class JobsOfferViwe(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        jobs = JobOffer.objects.all()
        user_skills = request.user.profile.skills
        filter_jobs = []
        
        for obj in jobs:
            offer_keywords = [kw.replace(',', '') for kw in obj.keywords.split() if kw.replace(',', '') in user_skills]
            if len(obj.keywords.split()) !=0:
                percentage = round((len(offer_keywords) / len(obj.keywords.split())) *100)
                if percentage >= 70:
                    filter_jobs.append(obj)
        
        serializer = JobOfferSerializer(filter_jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)