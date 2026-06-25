from django.urls import path

from dashboard.views import UserRoleUpdateView, dashboardStats, dashboardUserList

urlpatterns = [
    path("", dashboardUserList.as_view(), name="dashboard-users"),
    path("stats/", dashboardStats.as_view(), name="dashboard-stats"),
    path(
        "users/<int:user_id>/role/",
        UserRoleUpdateView.as_view(),
        name="dashboard-user-role",
    ),
]
