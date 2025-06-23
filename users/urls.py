from .views import *
from django.urls import path

urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('profile/', UserProfileCreateView.as_view()),
    path('profile/check/', UserProfileCheckView.as_view()),
    path('resume/analyzer/', AnalyzerResumeView.as_view(), name="analyzer-resume")
]