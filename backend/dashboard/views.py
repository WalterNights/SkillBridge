from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.models import JobApplication
from jobs.models import IgnoredOffer, JobOffer
from users.models import UserProfile
from users.serializers import UserProfileSerializer

User = get_user_model()


class dashboardUserList(ListAPIView):
    """Listado paginado de perfiles para el panel admin.

    SEGURIDAD: `IsAdminUser` (Django `is_staff=True`) — antes era
    `IsAuthenticated` y cualquier user con sesión podía listar TODOS
    los perfiles. PII leak. Ahora solo admins ven la lista.
    """

    permission_classes = [IsAdminUser]
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.select_related("user").order_by("-id")


class dashboardUserData(APIView):
    """Devuelve el perfil del request.user — usado por flows
    autenticados normales (no requiere admin)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class dashboardStats(APIView):
    """Métricas de plataforma para el dashboard admin.

    Todo en queries agregadas — nada de N+1 ni materializar querysets.
    Las métricas se calculan en el momento; sin cache. Si el volumen de
    datos crece (decenas de miles de ofertas) considerar mover a una
    materialized view o cron que escriba un snapshot diario.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        # Usuarios
        total_users = User.objects.count()
        total_profiles = UserProfile.objects.count()
        # Perfil "completo" = mismo criterio que el JWT login response.
        complete_profiles = UserProfile.objects.exclude(
            first_name=""
        ).exclude(
            last_name=""
        ).exclude(
            city=""
        ).exclude(
            phone=""
        ).exclude(
            professional_title=""
        ).count()

        # Ofertas
        total_offers = JobOffer.objects.count()
        active_offers = JobOffer.objects.filter(is_active=True).count()
        inactive_offers = total_offers - active_offers
        offers_by_portal = list(
            JobOffer.objects.filter(is_active=True)
            .values("portal")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        offers_by_country = list(
            JobOffer.objects.filter(is_active=True)
            .exclude(country="XX")
            .values("country")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Postulaciones
        total_applications = JobApplication.objects.count()
        applications_by_status = list(
            JobApplication.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        # Tasa de éxito real: applications con outcome positivo
        # (offer recibida) sobre el total de applications confirmadas
        # (cualquier status que no sea pending).
        non_pending = JobApplication.objects.exclude(status="pending").count()
        with_offer = JobApplication.objects.filter(status="offer").count()
        success_rate_pct = (with_offer / non_pending * 100) if non_pending > 0 else 0.0

        # Ignoradas — métrica de cuánto ruido tenemos.
        total_ignored = IgnoredOffer.objects.count()

        return Response(
            {
                "users": {
                    "total": total_users,
                    "with_profile": total_profiles,
                    "complete_profile": complete_profiles,
                },
                "offers": {
                    "total": total_offers,
                    "active": active_offers,
                    "inactive": inactive_offers,
                    "by_portal": offers_by_portal,
                    "by_country": offers_by_country,
                },
                "applications": {
                    "total": total_applications,
                    "by_status": applications_by_status,
                    "success_rate_pct": round(success_rate_pct, 1),
                },
                "ignored": {
                    "total": total_ignored,
                },
            },
            status=status.HTTP_200_OK,
        )
