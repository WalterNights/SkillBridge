from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import get_object_or_404
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


class UserRoleUpdateView(APIView):
    """PATCH /api/dashboard/users/{id}/role/ — promueve o degrada un user.

    Body: {"is_staff": bool, "is_superuser": bool} — ambos opcionales,
    se aplican solo los que vengan en el payload.

    Reglas de seguridad:
      - Solo IsAdminUser puede llamar al endpoint.
      - No puedes degradarte a ti mismo (anti-lockout: si el único
        admin se sacó is_staff por error, nadie puede recuperarlo
        sin SSH al VPS).
      - Solo un superuser puede tocar `is_superuser` (el escalado
        a super requiere ya ser super).
      - 404 si el target user no existe.
    """

    permission_classes = [IsAdminUser]

    def patch(self, request, user_id: int):
        target = get_object_or_404(User, pk=user_id)

        # Anti-self-lockout: el admin no puede sacarse sus propios
        # privilegios. Hay que pedirle a OTRO admin.
        is_self = request.user.id == target.id
        wants_demote_self = is_self and (
            request.data.get("is_staff") is False
            or request.data.get("is_superuser") is False
        )
        if wants_demote_self:
            return Response(
                {
                    "error": "self_demote_forbidden",
                    "detail": (
                        "No puedes degradarte a ti mismo. Pídele a otro admin "
                        "que lo haga."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Solo superusers pueden tocar is_superuser ajeno (defensa
        # contra escalado: un staff común no debería poder hacer
        # super a otro user, ni quitarle super a un super existente).
        if "is_superuser" in request.data and not request.user.is_superuser:
            return Response(
                {
                    "error": "superuser_required",
                    "detail": "Solo un super-admin puede modificar el flag de superuser.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        updates: dict[str, bool] = {}
        if "is_staff" in request.data:
            updates["is_staff"] = bool(request.data["is_staff"])
        if "is_superuser" in request.data:
            updates["is_superuser"] = bool(request.data["is_superuser"])
        if not updates:
            return Response(
                {
                    "error": "no_fields",
                    "detail": "Envía al menos is_staff o is_superuser en el body.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        for field, value in updates.items():
            setattr(target, field, value)
        target.save(update_fields=list(updates.keys()))

        return Response(
            {
                "id": target.id,
                "username": target.username,
                "email": target.email,
                "is_staff": target.is_staff,
                "is_superuser": target.is_superuser,
            }
        )


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
