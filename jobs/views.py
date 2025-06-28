from django.db.models import Q
from rest_framework import status
from django.shortcuts import render
from users.models import UserProfile
from rest_framework.views import APIView
from rest_framework.response import Response
from jobs.serializers import JobOfferSerializer
from jobs.utils.scraper import scrap_computrabajo
from jobs.utils.offer_filter import filter_offers_by_user_skill
from jobs.utils.query_generator import extract_search_query_from_summary


class JobScrapingView(APIView):
    def get(self, request):
        user = request.user
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND) 
        query = extract_search_query_from_summary(profile.summary or "")
        new_offers = scrap_computrabajo(query=query)
        filtered_offers = filter_offers_by_user_skill(new_offers, profile.skills)
        serializer = JobOfferSerializer(filtered_offers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)