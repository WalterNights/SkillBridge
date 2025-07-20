from django.urls import path
from .views import *

urlpatterns = [
    path('scrap-jobs/', JobScrapingView.as_view()),
    path('jobs-offer/', JobsOfferViwe.as_view())
]