from rest_framework.routers import DefaultRouter

from applications.views import CoverLetterViewSet, JobApplicationViewSet

router = DefaultRouter()
router.register(r"applications", JobApplicationViewSet, basename="application")
router.register(r"cover-letters", CoverLetterViewSet, basename="cover-letter")

urlpatterns = router.urls
