from django.urls import path

from dashboard.views import dashboardStats, dashboardUserList

urlpatterns = [
    path("", dashboardUserList.as_view(), name="dashboard-users"),
    path("stats/", dashboardStats.as_view(), name="dashboard-stats"),
]
