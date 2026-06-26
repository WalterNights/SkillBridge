"""URLs del lado empresa del marketplace.

Montadas en `/api/companies/` desde core/urls.py. Separadas de
`users/urls.py` para que el split conceptual quede limpio:

  /api/users/           → endpoints del lado profesional
  /api/companies/       → endpoints del lado empresa

Las views viven en `users.views` para reusar el setup de auth/JWT;
solo el routing está separado por dominio.
"""

from django.urls import path

from users.views import (
    CompanyMeView,
    CompanyRegisterView,
    CompanySearchProfilesView,
)

urlpatterns = [
    path("register/", CompanyRegisterView.as_view(), name="company-register"),
    path("me/", CompanyMeView.as_view(), name="company-me"),
    path(
        "search-profiles/",
        CompanySearchProfilesView.as_view(),
        name="company-search-profiles",
    ),
]
