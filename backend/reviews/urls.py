from django.urls import path

from reviews.views import (
    ReviewAdminDetailView,
    ReviewAdminListView,
    ReviewLandingView,
    ReviewMeView,
)

urlpatterns = [
    path("landing/", ReviewLandingView.as_view(), name="reviews-landing"),
    path("me/", ReviewMeView.as_view(), name="reviews-me"),
    path("admin/", ReviewAdminListView.as_view(), name="reviews-admin-list"),
    path("admin/<int:pk>/", ReviewAdminDetailView.as_view(), name="reviews-admin-detail"),
]
