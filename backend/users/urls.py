from django.urls import include, path
from rest_framework.routers import DefaultRouter

from users.views import (
    AnalyzerResumeView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    QuantifyAchievementView,
    UserProfileViewSet,
    UserRegisterView,
)

router = DefaultRouter()
router.register(r"profiles", UserProfileViewSet, basename="profile")

urlpatterns = [
    path("register/", UserRegisterView.as_view(), name="user-register"),
    path("resume-analyzer/", AnalyzerResumeView.as_view(), name="analyzer-resume"),
    path(
        "password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"
    ),
    path("password-reset/verify/", PasswordResetVerifyView.as_view(), name="password-reset-verify"),
    path("cv/quantify/", QuantifyAchievementView.as_view(), name="cv-quantify"),
    path("", include(router.urls)),
]
