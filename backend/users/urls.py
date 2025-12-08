from django.urls import path, include
from rest_framework.routers import DefaultRouter

from users.views import (
    UserRegisterView,
    UserProfileViewSet,
    AnalyzerResumeView
)

router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='profile')

urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('resume-analyzer/', AnalyzerResumeView.as_view(), name="analyzer-resume"),
    path('', include(router.urls)),
]