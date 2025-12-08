from django.urls import path

from dashboard.views import dashboardUserList

urlpatterns = [
    path('', dashboardUserList.as_view())
]