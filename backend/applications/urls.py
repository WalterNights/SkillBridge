from rest_framework.routers import DefaultRouter

from applications.views import JobApplicationViewSet

router = DefaultRouter()
router.register(r"applications", JobApplicationViewSet, basename="application")

urlpatterns = router.urls
