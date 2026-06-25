from django.urls import path

from faq.views import (
    FaqAdminDetailView,
    FaqAdminListView,
    FaqAdminStatsView,
    FaqAskView,
    FaqCategoryListView,
    FaqPublicListView,
    FaqViewCountView,
)

urlpatterns = [
    # Public
    path("", FaqPublicListView.as_view(), name="faq-public-list"),
    path("categories/", FaqCategoryListView.as_view(), name="faq-categories"),
    path("<int:pk>/view/", FaqViewCountView.as_view(), name="faq-view"),
    # Auth (user submission)
    path("ask/", FaqAskView.as_view(), name="faq-ask"),
    # Admin
    path("admin/", FaqAdminListView.as_view(), name="faq-admin-list"),
    path("admin/stats/", FaqAdminStatsView.as_view(), name="faq-admin-stats"),
    path("admin/<int:pk>/", FaqAdminDetailView.as_view(), name="faq-admin-detail"),
]
