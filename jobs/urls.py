from django.urls import path
from .views import JobScrapingView

urlpatterns = [
    path('scrap-jobs/', JobScrapingView.as_view()),
]