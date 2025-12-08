from django.urls import path, include
from rest_framework.routers import DefaultRouter

from jobs.views import JobOfferViewSet

router = DefaultRouter()
router.register(r'jobs', JobOfferViewSet, basename='job')

urlpatterns = [
    path('', include(router.urls)),
]