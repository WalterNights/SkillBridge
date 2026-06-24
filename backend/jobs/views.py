import logging

from django.core.cache import cache
from django.db.models import Count
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
from jobs.utils.offer_attributes import VALID_MODALITIES
from notifications.models import Notification
from users.models import UserProfile

# Umbral arriba del cual una oferta nueva dispara notif de match. Por
# debajo de esto consideramos que la coincidencia es débil y no vale la
# pena spamear al usuario — el feed igual la muestra ordenada.
_NOTIF_MATCH_THRESHOLD = 70

logger = logging.getLogger(__name__)

# Rate limit del scrape — caro (3 portales en paralelo + Gemini calls).
# Implementado via cache propio porque django_ratelimit no es trivial de
# aplicar a un @action de ViewSet (decoradores compuestos).
_SCRAPE_RATE_WINDOW_SECONDS = 60 * 60  # 1h
_SCRAPE_RATE_MAX_PER_USER = 5


def _check_and_bump_scrape_rate(user_id: int) -> bool:
    """Devuelve True si se permite seguir, False si excedió el límite.

    SEGURIDAD/RESILIENCIA: si el cache backend (Redis) no responde,
    fail-open — logueamos el problema y dejamos pasar la request en
    vez de devolver 500. Lo mismo que `RATELIMIT_FAIL_OPEN` hace para
    django-ratelimit, replicado a mano acá porque este path usa cache
    directo. Sin esto, una caída de Redis tumba el endpoint completo.
    """
    cache_key = f"scrape_ratelimit:{user_id}"
    try:
        current = cache.get(cache_key, 0)
        if current >= _SCRAPE_RATE_MAX_PER_USER:
            return False
        # TTL solo en el primer hit; siguientes incrementan sin renovar
        # (cache.incr no resetea TTL en redis), así la ventana es estricta.
        if current == 0:
            cache.set(cache_key, 1, timeout=_SCRAPE_RATE_WINDOW_SECONDS)
        else:
            cache.incr(cache_key)
    except Exception as exc:
        logger.warning("Scrape rate-limit cache unavailable, failing open: %s", exc)
    return True


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
        """Aplica filtros del dashboard (?country=, ?modality=).

        Por default filtra `is_active=True` — solo mostramos ofertas que
        siguen disponibles en el portal de origen. Las marcadas como
        inactivas (vía sync por sitemap o probe HTTP) quedan ocultas
        para honrar el slogan "cero ruido". Para debug se puede pasar
        `?include_inactive=true` (futuro — no expuesto en UI).

        Filtros adicionales:
          ?country=MX,CO     → ofertas de México o Colombia
          ?modality=remote   → solo remotas
          ?modality=remote,hybrid → remotas o híbridas

        Sin params → todas las activas, orden por recencia. Si un param
        viene con valor inválido, se ignora silenciosamente.
        """
        qs = JobOffer.objects.filter(is_active=True).order_by("-created_at")

        country_param = (self.request.query_params.get("country") or "").strip()
        if country_param:
            countries = [c.strip().upper() for c in country_param.split(",") if c.strip()]
            if countries:
                qs = qs.filter(country__in=countries)

        modality_param = (self.request.query_params.get("modality") or "").strip()
        if modality_param:
            modalities = [
                m.strip().lower()
                for m in modality_param.split(",")
                if m.strip().lower() in VALID_MODALITIES
            ]
            if modalities:
                qs = qs.filter(modality__in=modalities)

        return qs

    def _maybe_create_match_notification(self, user, offers):
        """Crea una notif `kind=match` si hay ≥1 oferta con match alto.

        Reglas:
          - Solo cuenta ofertas con `match_percentage >= _NOTIF_MATCH_THRESHOLD`.
          - `title` = "N nuevas ofertas calzan con tu perfil".
          - `body` = primeros 3 títulos truncados (anti-noisy).
          - `metadata` guarda la lista de offer ids — útil cuando un
            futuro click en la notif lleva al feed prefiltered.

        No-op silencioso si no hay match alto — no spamear al usuario con
        notifs vacías cada vez que da click a "Buscar ofertas".
        """
        high_match = [
            o for o in offers
            if getattr(o, "match_percentage", 0) >= _NOTIF_MATCH_THRESHOLD
        ]
        if not high_match:
            return

        # Tomamos los 3 títulos para el body. Truncados a 60 chars
        # cada uno para que el preview en el drawer no rompa el layout.
        sample_titles = [(o.title or "")[:60] for o in high_match[:3]]
        if len(high_match) > 3:
            body = f"{', '.join(sample_titles)} y {len(high_match) - 3} más — todas con +{_NOTIF_MATCH_THRESHOLD}% match."
        else:
            body = f"{', '.join(sample_titles)} — todas con +{_NOTIF_MATCH_THRESHOLD}% match."

        Notification.objects.create(
            user=user,
            kind="match",
            title=f"{len(high_match)} {'nueva oferta calza' if len(high_match) == 1 else 'nuevas ofertas calzan'} con tu perfil",
            body=body,
            metadata={"offer_ids": [o.id for o in high_match]},
        )

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

    @action(detail=False, methods=["get"], url_path="filter-options")
    def filter_options(self, request):
        """Devuelve los valores disponibles para los filtros del dashboard
        con conteo de ofertas — los dropdowns muestran "MX (45)" / "CO (20)".

        El frontend cachea esta respuesta — se llama 1 vez al cargar el
        dashboard. El refresh implícito ocurre cuando el user navega de
        vuelta (no precisa polling).

        Filtramos países 'XX' del response — los dejamos en DB para no
        perder datos pero no los exponemos como opción seleccionable
        (sería confuso ver "Sin país conocido (15)").
        """
        country_counts = (
            JobOffer.objects.exclude(country="XX")
            .values("country")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        modality_counts = (
            JobOffer.objects.values("modality")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        # Labels legibles para el dropdown
        modality_labels = dict(JobOffer.MODALITY_CHOICES)
        return Response(
            {
                "countries": [
                    {"value": row["country"], "count": row["count"]}
                    for row in country_counts
                ],
                "modalities": [
                    {
                        "value": row["modality"],
                        "label": modality_labels.get(row["modality"], row["modality"]),
                        "count": row["count"],
                    }
                    for row in modality_counts
                ],
            }
        )

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
        # Rate limit per-user via cache (fail-open si Redis down).
        if not _check_and_bump_scrape_rate(request.user.id):
            return Response(
                {
                    "error": (
                        "Demasiadas búsquedas en la última hora. "
                        "Esperá un rato e intentá de nuevo."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

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

            # Notif de match — solo si hay ofertas arriba del umbral.
            # Pongo el create al final del happy path para no romper el
            # scrape si la tabla Notification tiene un problema.
            self._maybe_create_match_notification(request.user, filtered_offers)

            serializer = self.get_serializer(filtered_offers, many=True)
            return Response(
                {"offers": serializer.data, "scrape_stats": scrape_stats},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Scraping failed: {e!s}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
