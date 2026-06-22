from django.urls import path

from tips.views import TipOfTheDayView

urlpatterns = [
    path("tips/today/", TipOfTheDayView.as_view(), name="tip-today"),
]
