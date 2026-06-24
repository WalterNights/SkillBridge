"""URL patterns para auth via OAuth proveedores externos.

Separado de `users/urls.py` (mountado en /api/users/) para que los
endpoints OAuth vivan en /api/auth/* — más natural y matcheable con
el redirect_uri registrado en cada proveedor (LinkedIn, futuros Google,
GitHub, etc.).
"""

from django.urls import path

from users.oauth_linkedin import LinkedInCallbackView, LinkedInStartView


urlpatterns = [
    path("linkedin/start/", LinkedInStartView.as_view(), name="linkedin-start"),
    path("linkedin/callback/", LinkedInCallbackView.as_view(), name="linkedin-callback"),
]
