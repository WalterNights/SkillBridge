from django.core.cache import cache
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from jobs.models import JobOffer
from jobs.serializers import JobOfferSerializer
from jobs.services.job_service import JobService
from jobs.services.matching_service import JobMatchingService
from users.models import UserProfile

# Rate limit del scrape — caro (3 portales en paralelo + Gemini calls).
# Implementado via cache propio porque django_ratelimit no es trivial de
# aplicar a un @action de ViewSet (decoradores compuestos).
_SCRAPE_RATE_WINDOW_SECONDS = 60 * 60  # 1h
_SCRAPE_RATE_MAX_PER_USER = 5


class JobOfferViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para operaciones de lectura de ofertas de trabajo.

    Endpoints:
    - GET /jobs/ - Lista todas las ofertas (enriquecidas con match del usuario)
    - GET /jobs/{id}/ - Detalle de una oferta (enriquecido con match del usuario)
    - GET /jobs/matched/ - Ofertas filtradas por matching con usuario
    - GET /jobs/scrape/ - Ejecuta scraping de nuevas ofertas
    """

    queryset = JobOffer.objects.all()
    serializer_class = JobOfferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Optimiza queries con select_related"""
        return JobOffer.objects.all().order_by("-created_at")

    def _enrich_with_user_match(self, offers):
        """Adjunta match_percentage / matched_skills / missing_skills usando
        el perfil del usuario autenticado. Es no-op si el usuario no tiene
        perfil completo todavía.
        """
        try:
            profile = self.request.user.profile
        except UserProfile.DoesNotExist:
            return
        JobMatchingService.enrich_with_match(offers, profile)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            self._enrich_with_user_match(page)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        offers = list(queryset)
        self._enrich_with_user_match(offers)
        serializer = self.get_serializer(offers, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._enrich_with_user_match([instance])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def matched(self, request):
        """
        Retorna ofertas que coinciden con las skills del usuario.
        Query params:
        - min_match: porcentaje mínimo de match (default: 50)
        """
        try:
            user_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

        min_match = int(request.query_params.get("min_match", 50))

        # Usar servicio de matching
        jobs = JobService.get_all_jobs()
        filtered_jobs = JobMatchingService.filter_jobs_by_skills(
            jobs, user_profile, min_match_percentage=min_match
        )

        serializer = self.get_serializer(filtered_jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def scrape(self, request):
        """
        Ejecuta scraping de nuevas ofertas basado en el perfil del usuario.

        SEGURIDAD: rate limit propio de 5/hora por usuario. Sin esto,
        un cliente malicioso podía drenar la cuota de Gemini AI y/o
        hacer flood al rate limit de DDG/LinkedIn como proxy involuntario.
        """
        # Rate limit per-user via cache. Devolvemos 429 sin tocar
        # los portales si el usuario excedió la cuota.
        cache_key = f"scrape_ratelimit:{request.user.id}"
        current = cache.get(cache_key, 0)
        if current >= _SCRAPE_RATE_MAX_PER_USER:
            return Response(
                {
                    "error": (
                        "Demasiadas búsquedas en la última hora. "
                        "Esperá un rato e intentá de nuevo."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        # TTL solo en el primer hit; siguientes incrementan sin renovar
        # (cache.incr no resetea TTL en redis), así la ventana es estricta.
        if current == 0:
            cache.set(cache_key, 1, timeout=_SCRAPE_RATE_WINDOW_SECONDS)
        else:
            cache.incr(cache_key)

        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

        query = profile.professional_title
        location = profile.city

        if not query or not location:
            # El frontend muestra `err.error.error` como toast cuando el
            # status es 400 — usamos esa convención para que el usuario
            # vea de inmediato qué le falta, no un genérico "sin novedades".
            missing = []
            if not query:
                missing.append("título profesional")
            if not location:
                missing.append("ciudad")
            return Response(
                {
                    "error": (
                        f"Completá tu perfil con {', '.join(missing)} para "
                        "obtener ofertas personalizadas."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Scrapea TODOS los portales registrados en paralelo
            new_offers, scrape_stats = JobService.scrape_all_portals_with_stats(
                query, location
            )

            # Filtrar por matching (cargo + skills, ver matching_service)
            filtered_offers = JobMatchingService.filter_jobs_by_skills(
                new_offers, profile, min_match_percentage=25
            )

            serializer = self.get_serializer(filtered_offers, many=True)
            return Response(
                {"offers": serializer.data, "scrape_stats": scrape_stats},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Scraping failed: {e!s}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
