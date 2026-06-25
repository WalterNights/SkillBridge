from django.urls import include, path
from rest_framework.routers import DefaultRouter

from users.views import (
    AnalyzerResumeView,
    ChangePasswordView,
    CvAuditView,
    CvImproveView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    QuantifyAchievementView,
    TwoFactorActivateView,
    TwoFactorDisableView,
    TwoFactorSetupView,
    TwoFactorStatusView,
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
    path("me/change-password/", ChangePasswordView.as_view(), name="user-change-password"),
    path("cv/quantify/", QuantifyAchievementView.as_view(), name="cv-quantify"),
    path("cv/audit/", CvAuditView.as_view(), name="cv-audit"),
    path("cv/improve/", CvImproveView.as_view(), name="cv-improve"),
    path("2fa/status/", TwoFactorStatusView.as_view(), name="2fa-status"),
    path("2fa/setup/", TwoFactorSetupView.as_view(), name="2fa-setup"),
    path("2fa/activate/", TwoFactorActivateView.as_view(), name="2fa-activate"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="2fa-disable"),
    path("", include(router.urls)),
]
