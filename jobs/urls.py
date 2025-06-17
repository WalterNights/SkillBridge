from django.urls import path
from .views import JobScrapingView

urlpatterns = [
    path('api/scrap-jobs/', JobScrapingView.as_view()),
]