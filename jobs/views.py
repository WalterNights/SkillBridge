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
        for job in jobs:
            offer_skill = job.keywords.split(',')
            matched_skills = [kw for kw in offer_skill if kw.strip() and kw in user_skills.lower()]
            missing_skills = [kw for kw in offer_skill if kw.strip() not in user_skills.lower()]
            if len([kw for kw in offer_skill if kw.strip()]) !=0:
                match_percentage = round((len(matched_skills) / len(offer_skill)) *100)
                if match_percentage >= 60:
                    job.matched_skills = matched_skills
                    job.missing_skills = missing_skills
                    job.match_percentage = match_percentage
                    filter_jobs.append(job)
        serializer = JobOfferSerializer(filter_jobs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
class JobOfferDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get (self, request, pk):
        user = request.user
        try:
            job = JobOffer.objects.get(pk=pk)
        except JobOffer.DoesNotExist:
            return Response({'error': "No existe"}, status=404)
        serializer = JobOfferSerializer(job)
        return Response(serializer.data)