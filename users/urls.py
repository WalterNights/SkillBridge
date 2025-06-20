from .views import *
from django.urls import path

urlpatterns = [
    path('api/users/register/', UserRegisterView.as_view(), name='user-register'),
    path('api/users/profiles/', UserProfileCreateView.as_view()),
    path('api/users/profile/check/', UserProfileCheckView.as_view()),
    path('api/users/resume/analyzer/', AnalyzerResumeView.as_view(), name="analyzer-resume")
]