from django.urls import include, path
from rest_framework.routers import DefaultRouter

from system_settings.views import AdminSystemSettingViewSet, PublicFeatureFlagsView

router = DefaultRouter()
router.register(r"admin/feature-flags", AdminSystemSettingViewSet, basename="admin-feature-flags")

urlpatterns = [
    path("feature-flags/", PublicFeatureFlagsView.as_view(), name="public-feature-flags"),
    path("", include(router.urls)),
]
