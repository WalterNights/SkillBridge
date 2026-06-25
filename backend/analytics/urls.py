from django.urls import path

from analytics.views import SummaryView, TrackView

urlpatterns = [
    path("track/", TrackView.as_view(), name="analytics-track"),
    path("summary/", SummaryView.as_view(), name="analytics-summary"),
]
