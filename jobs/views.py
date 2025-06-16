from .models import JobOffer
from django.db.models import Q
from rest_framework import status
from django.shortcuts import render
from rest_framework.views import APIView
from .serializers import JobOfferSerializer
from rest_framework.response import Response
from .utils.scraper import run_scraper_and_store_results


class JobScrapingView(APIView):
    def get(self, request):
        query = request.GET.get('q', 'desarrollador')
        new_offers = run_scraper_and_store_results(query)
        serializer = JobOfferSerializer(new_offers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)