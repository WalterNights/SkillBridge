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
