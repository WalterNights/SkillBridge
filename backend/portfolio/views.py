"""Views del portafolio.

Endpoints:

- `GET  /api/portfolio/<slug>/`              — público, sin auth
- `PUT  /api/portfolio/<slug>/`              — IsAdminUser
- `GET  /api/portfolio/<slug>/images/`       — IsAdminUser (listado gestión)
- `POST /api/portfolio/<slug>/images/`       — IsAdminUser (upload)
- `DELETE /api/portfolio/<slug>/images/<id>/` — IsAdminUser

Notas de diseño:

- Sin creación por API. Los portafolios se crean por data migration o
  via el admin de Django. Rationale: el slug se resuelve desde URL, y
  permitir POST /api/portfolio/ abriría spam de slugs.
- El PUT sobreescribe `content` y `content_en` completos (no PATCH parcial).
  El editor manda siempre el árbol completo — así evitamos race
  conditions con edits parciales concurrentes.
- Las imágenes se listan implícitamente en el GET público (dentro del
  payload de Portfolio). El endpoint separado de imágenes es solo para
  la gestión (subir/borrar) desde el editor.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.generics import (
    RetrieveUpdateAPIView,
    ListCreateAPIView,
    DestroyAPIView,
)
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from portfolio.models import Portfolio, PortfolioImage
from portfolio.serializers import (
    PortfolioAdminSerializer,
    PortfolioImageSerializer,
    PortfolioImageUploadSerializer,
    PortfolioPublicSerializer,
)

logger = logging.getLogger(__name__)

# Servicio público que scrapea la contribución de un usuario. Fallback
# cuando GITHUB_TOKEN no está seteado — solo ve contribuciones públicas.
_GH_CONTRIB_API = "https://github-contributions-api.jogruber.de/v4/{username}"
# GitHub GraphQL — precisión real, incluye privadas si el token tiene
# `read:user` y el user tiene "Include private contributions" activo.
_GH_GRAPHQL_URL = "https://api.github.com/graphql"
_GH_CACHE_TTL_SECONDS = 3600
_GH_HTTP_TIMEOUT_SECONDS = 8
# Validación defensiva del username antes de embed en URL.
_GH_USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")

_GH_CONTRIB_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

# GraphQL devuelve el nivel como enum string; el frontend espera 0-4.
_GH_LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def _fetch_github_via_graphql(username: str, token: str) -> dict:
    """Consulta GraphQL oficial. Incluye contribuciones privadas si el
    token tiene scope `read:user` y el user activó "Include private
    contributions on my profile".

    Raise `requests.RequestException` o `ValueError` en cualquier error;
    la view los captura y responde 502.
    """
    resp = requests.post(
        _GH_GRAPHQL_URL,
        json={"query": _GH_CONTRIB_QUERY, "variables": {"login": username}},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "skiltak-portfolio",
        },
        timeout=_GH_HTTP_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    body = resp.json()

    # GraphQL puede devolver 200 con errores en el body — hay que chequear.
    if body.get("errors"):
        raise ValueError(f"GitHub GraphQL errors: {body['errors']}")

    user_node = (body.get("data") or {}).get("user")
    if not user_node:
        raise ValueError(f"GitHub user '{username}' no encontrado")

    calendar = user_node["contributionsCollection"]["contributionCalendar"]
    total = calendar["totalContributions"]

    contributions = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            contributions.append({
                "date": day["date"],
                "count": day["contributionCount"],
                "level": _GH_LEVEL_MAP.get(day["contributionLevel"], 0),
            })

    return {
        "username": username,
        "total": {"lastYear": total},
        "contributions": contributions,
    }


def _fetch_github_via_jogruber(username: str) -> dict:
    """Fallback público: consulta el proxy jogruber. Solo ve contribuciones
    en repos públicos — el número puede ser menor al que muestra GitHub
    en el profile si el user tiene contribuciones privadas.
    """
    resp = requests.get(
        _GH_CONTRIB_API.format(username=username),
        params={"y": "last"},
        timeout=_GH_HTTP_TIMEOUT_SECONDS,
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "username": username,
        "total": data.get("total", {}),
        "contributions": data.get("contributions", []),
    }


class PortfolioPublicView(APIView):
    """`GET /api/portfolio/<slug>/` — payload público del portafolio.

    Devuelve 404 si el slug no existe: el frontend cae al bundle estático
    de i18n (fallback graceful) y el sitio no queda en blanco.
    """

    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            portfolio = Portfolio.objects.prefetch_related("images").get(slug=slug)
        except Portfolio.DoesNotExist:
            return Response(
                {"detail": "Portafolio no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PortfolioPublicSerializer(portfolio, context={"request": request})
        return Response(serializer.data)


class PortfolioAdminView(RetrieveUpdateAPIView):
    """`GET/PUT/PATCH /api/portfolio/<slug>/admin/` — vista admin del
    contenido. GET expone lo mismo que la pública + timestamps de
    edición. PUT/PATCH sobreescribe `content` y `content_en`."""

    permission_classes = [IsAdminUser]
    serializer_class = PortfolioAdminSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Portfolio.objects.prefetch_related("images").all()


class PortfolioImageListCreateView(ListCreateAPIView):
    """`GET/POST /api/portfolio/<slug>/images/` — gestión de covers.

    POST espera multipart: `image` (file), `project_id` (str), `alt_text`
    (str opcional). Devuelve el objeto creado con la URL absoluta.
    """

    permission_classes = [IsAdminUser]

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return PortfolioImage.objects.filter(portfolio__slug=slug)

    def get_serializer_class(self):
        # POST/PUT necesitan aceptar `image` como upload; GET devuelve
        # `url` computada. Separamos serializers para no exponer el
        # ImageField en la respuesta (donde queremos URL, no path).
        if self.request.method == "POST":
            return PortfolioImageUploadSerializer
        return PortfolioImageSerializer

    def create(self, request, *args, **kwargs):
        try:
            portfolio = Portfolio.objects.get(slug=self.kwargs["slug"])
        except Portfolio.DoesNotExist:
            return Response(
                {"detail": "Portafolio no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.save(portfolio=portfolio)
        # Respondemos con el serializer de lectura (incluye URL absoluta).
        out = PortfolioImageSerializer(image, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)


def _extract_github_username(sidebar: dict) -> str | None:
    """Deriva el username de GitHub del social link con id='github'.

    Acepta URLs tipo `https://github.com/foo`, `https://github.com/foo/`,
    `https://github.com/foo/repo`, o solo `foo`. Devuelve None si no
    encuentra un valor válido — la view responde 404 en ese caso.
    """
    socials = sidebar.get("socials") if isinstance(sidebar, dict) else None
    if not isinstance(socials, list):
        return None

    for item in socials:
        if not isinstance(item, dict) or item.get("id") != "github":
            continue
        raw = (item.get("url") or "").strip()
        if not raw:
            return None
        # Aceptamos URL completa o solo username.
        candidate = raw
        if "://" in raw or raw.startswith("//") or raw.startswith("github.com"):
            parsed = urlparse(raw if "://" in raw else f"https://{raw}")
            # Primera parte del path — descartamos /repo, /?tab=..., etc.
            candidate = parsed.path.strip("/").split("/", 1)[0]
        if _GH_USERNAME_RE.match(candidate):
            return candidate
        return None
    return None


class PortfolioGithubContributionsView(APIView):
    """`GET /api/portfolio/<slug>/github-contributions/`

    Público (sin auth). Deriva el username del social link `id='github'`
    del portfolio, consulta el servicio externo, cachea 1h. Si el social
    no existe o el servicio falla, devuelve 404 — el frontend oculta
    la sección graceful.

    El shape del response matchea lo que devuelve jogruber:
    { total: {"lastYear": int}, contributions: [{date, count, level}, ...] }
    """

    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            portfolio = Portfolio.objects.get(slug=slug)
        except Portfolio.DoesNotExist:
            return Response(
                {"detail": "Portafolio no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        sidebar = portfolio.content.get("sidebar") if isinstance(portfolio.content, dict) else None
        username = _extract_github_username(sidebar or {})
        if not username:
            return Response(
                {"detail": "El portafolio no tiene un link de GitHub configurado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Cache key incluye la fuente — si el admin agrega el GITHUB_TOKEN
        # después de un fetch por jogruber, no devolvemos el conteo bajo
        # cacheado, forzamos refresh via GraphQL.
        token = getattr(settings, "GITHUB_TOKEN", "") or ""
        source = "graphql" if token else "jogruber"
        cache_key = f"portfolio:github-contrib:{source}:{username}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        try:
            if token:
                normalized = _fetch_github_via_graphql(username, token)
            else:
                normalized = _fetch_github_via_jogruber(username)
        except requests.RequestException as exc:
            logger.warning(
                "portfolio: fallo GitHub contributions [%s] para %s: %s",
                source, username, exc,
            )
            return Response(
                {"detail": "No se pudo cargar la contribución de GitHub."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError as exc:
            logger.warning(
                "portfolio: respuesta inválida de GitHub [%s] para %s: %s",
                source, username, exc,
            )
            return Response(
                {"detail": "Respuesta inválida del servicio externo."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        cache.set(cache_key, normalized, timeout=_GH_CACHE_TTL_SECONDS)
        return Response(normalized)


class PortfolioImageDeleteView(DestroyAPIView):
    """`DELETE /api/portfolio/<slug>/images/<id>/` — remueve una cover.

    El ImageField borra el archivo físico al borrar el registro solo si
    se configura signal — Django default NO borra el archivo. Aceptamos
    que quede huérfano en MEDIA_ROOT: es un portafolio, no una tabla
    con millones de rows. Se limpia manualmente si hace falta.
    """

    permission_classes = [IsAdminUser]

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return PortfolioImage.objects.filter(portfolio__slug=slug)
