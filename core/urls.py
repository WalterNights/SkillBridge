from django.contrib import admin
from django.urls import path, include
from users.views import CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/jobs/', include('jobs.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='tokee_refresh'),
    path('api/token/login/', CustomTokenObtainPairView.as_view(), name='custom_token_obtain_pair')
]