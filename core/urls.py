from django.urls import path
from django.contrib import admin
from jobs.views import JobScrapingView
from users.views import UserProfileCreateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/user-profiles/', UserProfileCreateView.as_view()),
    path('api/scrap-jobs/', JobScrapingView.as_view()),
]
