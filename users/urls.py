from .views import *
from django.urls import path

urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('api/user-profiles/', UserProfileCreateView.as_view()),
    path('api/user-check/', UserProfileCheckView.as_view()),
]