from django.urls import path
from .views import *

urlpatterns = [
    path('', dashboardUserList.as_view())
]