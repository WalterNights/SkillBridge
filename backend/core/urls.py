from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.views import CustomTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/jobs/", include("jobs.urls")),
    path("api/dashboard/", include("dashboard.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("tips.urls")),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/login/", CustomTokenObtainPairView.as_view(), name="custom_token_obtain_pair"),
]

# Sirve archivos subidos (profile photos, resumes) en dev. En prod los
# sirve Nginx/Whitenoise directamente desde MEDIA_ROOT.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
