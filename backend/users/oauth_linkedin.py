"""LinkedIn OAuth 2.0 / OpenID Connect — sign-in flow.

Flujo completo:
  1. GET  /api/auth/linkedin/start/   → genera `state` random, lo guarda
                                        en cache 10 min, redirige al
                                        authorize URL de LinkedIn.
  2. User autoriza en LinkedIn → LinkedIn redirige a:
     GET  /api/auth/linkedin/callback/?code=X&state=Y
  3. Callback valida `state` (anti-CSRF), intercambia `code` por
     `access_token` via LinkedIn token endpoint, fetcha userinfo
     (email + nombre + sub), find_or_create User, emite par JWT, y
     redirige al frontend a `LINKEDIN_FRONTEND_COMPLETE_URL` con los
     tokens en query string (one-shot, el frontend los lee y limpia).

Seguridad:
  - State token CSRF guardado en cache (no en cookie) — sin riesgo de
    leak a JS si el browser tiene XSS en otro origin.
  - Si el user con ese email ya existe pero sin `linkedin_user_id`,
    LINKEA las cuentas (set sub al user existente). Evita duplicados.
  - Usuario nuevo tiene password unusable — se debe loguear con
    LinkedIn siempre. Si quiere password, lo setea con el flow de
    reset password normal.

Si las settings de LinkedIn no están configuradas (LINKEDIN_CLIENT_ID
vacío), los endpoints devuelven 503 con mensaje claro. El front igual
puede renderear el botón pero el click da error explicativo.
"""

from __future__ import annotations

import logging
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

User = get_user_model()


# LinkedIn OAuth endpoints — públicos, documentados en linkedin.com/docs.
_AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

# Scopes del producto "Sign In with LinkedIn using OpenID Connect".
# Mínimo necesario para login — NO pedimos contactos, posts, ni
# connections. Privacy first.
_SCOPES = "openid profile email"

# Cache key prefix + TTL del state token (10 min — suficiente para
# que el user complete el flow en LinkedIn, no tan largo como para
# que un state robado siga siendo válido).
_STATE_CACHE_PREFIX = "linkedin_oauth_state:"
_STATE_TTL_SECONDS = 600

_HTTP_TIMEOUT_SECONDS = 15


def _config_missing_response() -> Response:
    """503 + mensaje cuando LINKEDIN_CLIENT_ID/SECRET no están en el .env."""
    return Response(
        {
            "error": "linkedin_oauth_not_configured",
            "detail": "Login con LinkedIn no disponible. Vuelve a intentarlo más tarde.",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class LinkedInStartView(APIView):
    """GET /api/auth/linkedin/start/ → redirige al authorize URL."""

    permission_classes = [AllowAny]

    def get(self, request: Request):
        if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
            return _config_missing_response()

        # State token random, guardado en cache para validar en callback.
        # Usamos token_urlsafe (CSPRNG) — `secrets`, no `random`.
        state = secrets.token_urlsafe(32)
        cache.set(f"{_STATE_CACHE_PREFIX}{state}", "pending", _STATE_TTL_SECONDS)

        params = {
            "response_type": "code",
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
            "scope": _SCOPES,
            "state": state,
        }
        return redirect(f"{_AUTHORIZE_URL}?{urlencode(params)}")


class LinkedInCallbackView(APIView):
    """GET /api/auth/linkedin/callback/?code=...&state=...

    Termina el flow OAuth, crea/recupera al user, emite JWT pair y
    redirige al frontend con los tokens en query string.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request):
        if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
            return _config_missing_response()

        # LinkedIn manda `error` y `error_description` si el user
        # cancela o el OAuth falla. Lo respetamos y redirigimos al
        # frontend con el error.
        if request.query_params.get("error"):
            err = request.query_params.get("error", "oauth_failed")
            return self._redirect_to_frontend(error=err)

        code = request.query_params.get("code", "")
        state = request.query_params.get("state", "")
        if not code or not state:
            # Log diagnóstico: querer ver exactamente qué llegó. Si LinkedIn
            # manda algo que no estamos esperando (ej: nuevo param de error
            # no documentado, o el flow se cortó), esto nos lo dice.
            logger.warning(
                "LinkedIn callback missing code/state. query_params=%s",
                dict(request.query_params),
            )
            return self._redirect_to_frontend(error="missing_params")

        # Validar state contra cache (anti-CSRF) — y borrarlo
        # inmediatamente para que no se pueda reusar (replay protection).
        cache_key = f"{_STATE_CACHE_PREFIX}{state}"
        if cache.get(cache_key) is None:
            return self._redirect_to_frontend(error="invalid_state")
        cache.delete(cache_key)

        # Step 1 — intercambiar code por access_token
        try:
            token_response = requests.post(
                _TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
                    "client_id": settings.LINKEDIN_CLIENT_ID,
                    "client_secret": settings.LINKEDIN_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=_HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.warning("LinkedIn token exchange failed: %s", exc)
            return self._redirect_to_frontend(error="linkedin_unreachable")

        if token_response.status_code != 200:
            logger.warning(
                "LinkedIn token endpoint returned %d: %s",
                token_response.status_code,
                token_response.text[:200],
            )
            return self._redirect_to_frontend(error="token_exchange_failed")

        access_token = token_response.json().get("access_token")
        if not access_token:
            return self._redirect_to_frontend(error="no_access_token")

        # Step 2 — fetch userinfo (OIDC standard endpoint)
        try:
            userinfo_response = requests.get(
                _USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=_HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.warning("LinkedIn userinfo failed: %s", exc)
            return self._redirect_to_frontend(error="userinfo_failed")

        if userinfo_response.status_code != 200:
            return self._redirect_to_frontend(error="userinfo_failed")

        userinfo = userinfo_response.json()
        sub = userinfo.get("sub")
        email = (userinfo.get("email") or "").lower().strip()
        if not sub or not email:
            return self._redirect_to_frontend(error="incomplete_userinfo")

        # Step 3 — find or create user
        user = self._find_or_create_user(
            linkedin_sub=sub,
            email=email,
            given_name=userinfo.get("given_name", ""),
            family_name=userinfo.get("family_name", ""),
        )

        # Step 4 — emit JWT pair y redirigir al frontend
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_str = str(refresh)
        return self._redirect_to_frontend(access=access, refresh=refresh_str)

    @staticmethod
    def _find_or_create_user(
        linkedin_sub: str, email: str, given_name: str, family_name: str
    ):
        """Idempotente. Tres caminos:
          1. User con `linkedin_user_id=sub` ya existe → return
          2. User con email ya existe pero sin linkedin_user_id → link
          3. Sin user previo → create con username derivado del email.
             Password unusable (debe loguear con LinkedIn siempre, o
             usar el flow de reset password para setear uno).
        """
        # Path 1 — por sub
        user = User.objects.filter(linkedin_user_id=linkedin_sub).first()
        if user is not None:
            return user

        # Path 2 — por email, linkear
        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            user.linkedin_user_id = linkedin_sub
            user.save(update_fields=["linkedin_user_id"])
            return user

        # Path 3 — crear nuevo
        # Username = local-part del email, dedupando con sufijo numérico
        # si ya está tomado.
        base_username = email.split("@")[0][:30] or f"lkin_{linkedin_sub[:10]}"
        username = base_username
        suffix = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username[:25]}{suffix}"
            suffix += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=None,  # unusable password — solo OAuth
            first_name=given_name[:30],
            last_name=family_name[:30],
        )
        user.linkedin_user_id = linkedin_sub
        user.set_unusable_password()
        user.save(update_fields=["linkedin_user_id", "password"])
        return user

    @staticmethod
    def _redirect_to_frontend(
        access: str | None = None,
        refresh: str | None = None,
        error: str | None = None,
    ):
        """Redirige al `LINKEDIN_FRONTEND_COMPLETE_URL` con query params.

        El frontend hace `?access=X&refresh=Y` → guarda tokens en
        storage, redirige a /dashboard o /profile según corresponda.
        Si hay `?error=Z` muestra mensaje y vuelve al login.
        """
        params: dict[str, str] = {}
        if access:
            params["access"] = access
        if refresh:
            params["refresh"] = refresh
        if error:
            params["error"] = error
        return redirect(f"{settings.LINKEDIN_FRONTEND_COMPLETE_URL}?{urlencode(params)}")
