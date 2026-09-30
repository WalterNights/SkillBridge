"""Views de reseñas.

Endpoints:
  - Public:
      GET    /api/reviews/landing/     → reseñas aptas para el landing
  - Auth required:
      GET    /api/reviews/me/          → elegibilidad + mi reseña (o null)
      PUT    /api/reviews/me/          → crear/editar mi reseña (vuelve a pending)
      DELETE /api/reviews/me/          → borrar mi reseña
  - Admin only (IsAdminUser):
      GET    /api/reviews/admin/       → cola de moderación (?status=)
      PATCH  /api/reviews/admin/{id}/  → publicar/rechazar
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from reviews.models import LANDING_MIN_RATING, Review
from reviews.serializers import (
    ReviewAdminSerializer,
    ReviewLandingSerializer,
    ReviewOwnSerializer,
)
from reviews.services.eligibility import count_real_applications, min_applications_required

# Cuántas reseñas manda el landing (una fila de 3 columnas).
_LANDING_LIMIT = 3


class ReviewLandingView(APIView):
    """GET /api/reviews/landing/ — público. Si la lista viene vacía, el
    frontend sigue mostrando los testimonios estáticos."""

    permission_classes = [AllowAny]

    def get(self, request):
        qs = (
            Review.objects.filter(
                status=Review.STATUS_PUBLISHED,
                rating__gte=LANDING_MIN_RATING,
                allow_public=True,
            )
            .select_related("user__profile")
            .order_by("-rating", "-moderated_at")[:_LANDING_LIMIT]
        )
        serializer = ReviewLandingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


# 10 escrituras por hora sobra para editar la reseña; frena spam de PUTs
# que reencolan moderación. Va sobre los handlers (no `dispatch`) para que
# corra después de la auth JWT de DRF y el bucket sea por usuario.
_write_ratelimit = ratelimit(key="user", rate="10/h", block=True)


@method_decorator(_write_ratelimit, name="put")
@method_decorator(_write_ratelimit, name="delete")
class ReviewMeView(APIView):
    """Reseña del usuario autenticado + su elegibilidad.

    GET response:
      { eligible, applications_count, min_applications, review: {...} | null }
    PUT: 403 si no llegó al mínimo de postulaciones reales.
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _payload(review: Review | None, count: int, minimum: int) -> dict:
        return {
            "eligible": count >= minimum,
            "applications_count": count,
            "min_applications": minimum,
            "review": ReviewOwnSerializer(review).data if review else None,
        }

    def get(self, request):
        review = Review.objects.filter(user=request.user).first()
        count = count_real_applications(request.user)
        return Response(self._payload(review, count, min_applications_required()))

    def put(self, request):
        count = count_real_applications(request.user)
        minimum = min_applications_required()
        if count < minimum:
            return Response(
                {
                    "detail": (
                        f"Necesitas al menos {minimum} postulaciones confirmadas "
                        f"para dejar tu reseña (llevas {count})."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        review = Review.objects.filter(user=request.user).first()
        serializer = ReviewOwnSerializer(review, data=request.data)
        serializer.is_valid(raise_exception=True)
        # Cualquier edición vuelve a moderación: el admin aprobó el texto
        # anterior, no el nuevo.
        review = serializer.save(
            user=request.user,
            status=Review.STATUS_PENDING,
            moderated_by=None,
            moderated_at=None,
            moderation_note="",
        )
        return Response(self._payload(review, count, minimum))

    def delete(self, request):
        Review.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewAdminListView(ListAPIView):
    """GET /api/reviews/admin/?status=pending|published|rejected|all
    (default: pending)."""

    permission_classes = [IsAdminUser]
    serializer_class = ReviewAdminSerializer

    def get_queryset(self):
        qs = Review.objects.select_related("user__profile", "moderated_by").order_by("-updated_at")
        status_filter = self.request.query_params.get("status", Review.STATUS_PENDING)
        if status_filter != "all":
            qs = qs.filter(status=status_filter)
        return qs


class ReviewAdminDetailView(APIView):
    """PATCH /api/reviews/admin/{id}/ — body: {status, moderation_note?}.
    Registra moderated_by + moderated_at cuando cambia el status."""

    permission_classes = [IsAdminUser]

    def patch(self, request, pk: int):
        review = get_object_or_404(Review, pk=pk)
        serializer = ReviewAdminSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        status_changed = "status" in request.data and request.data["status"] != review.status
        instance = serializer.save()
        if status_changed:
            instance.moderated_by = request.user
            instance.moderated_at = timezone.now()
            instance.save(update_fields=["moderated_by", "moderated_at"])
        return Response(ReviewAdminSerializer(instance).data)
