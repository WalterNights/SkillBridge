from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from jobs.models import JobOffer
from jobs.serializers import JobOfferSerializer
from jobs.services.job_service import JobService
from jobs.services.matching_service import JobMatchingService
from users.models import UserProfile


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
        """
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

        query = profile.professional_title
        location = profile.city

        if not query or not location:
            # En lugar de retornar error, retornar lista vacía con mensaje informativo
            missing_fields = []
            if not query:
                missing_fields.append("título profesional")
            if not location:
                missing_fields.append("ciudad")
            return Response(
                {
                    "message": f"Completa tu perfil con {', '.join(missing_fields)} para obtener ofertas personalizadas",
                    "jobs": [],
                },
                status=status.HTTP_200_OK,
            )

        try:
            # Scrapea TODOS los portales registrados en paralelo
            new_offers = JobService.scrape_all_portals(query, location)

            # Filtrar por matching
            filtered_offers = JobMatchingService.filter_jobs_by_skills(
                new_offers, profile, min_match_percentage=30
            )

            serializer = self.get_serializer(filtered_offers, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Scraping failed: {e!s}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
