from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from applications.models import JobApplication
from applications.serializers import JobApplicationSerializer


class JobApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet del modelo JobApplication, scoped a request.user.

    Endpoints:
      - GET    /api/applications/                → lista del user
      - POST   /api/applications/                → crear (status=pending)
      - DELETE /api/applications/{id}/           → undo (si dijo "no")
      - POST   /api/applications/{id}/confirm/   → status=applied
      - GET    /api/applications/applied-ids/    → set de offer_ids para
                                                    el badge "Aplicado"
                                                    en el feed

    SEGURIDAD: get_queryset filtra por user → un user no puede leer ni
    mutar applications de otro (404 antes que 403, sin leak).
    """

    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # lista chica (~10s-100s) — front filtra/scrollea

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user).select_related(
            "offer"
        )

    def create(self, request, *args, **kwargs):
        """Crear es idempotente: si ya existe para (user, offer), devuelve
        la existente sin tocar nada. Cubre el caso "user clickea Apply
        dos veces antes de confirmar"."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = serializer.validated_data["offer"]
        instance, created = JobApplication.objects.get_or_create(
            user=request.user,
            offer=offer,
            defaults={"status": "pending"},
        )
        out = JobApplicationSerializer(instance).data
        return Response(
            out, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """User confirma "Sí, aplicé" → status=applied + applied_at=now."""
        application = self.get_object()
        application.status = "applied"
        application.applied_at = timezone.now()
        application.save(update_fields=["status", "applied_at"])
        return Response(JobApplicationSerializer(application).data)

    @action(detail=False, methods=["get"], url_path="applied-ids")
    def applied_ids(self, request):
        """Devuelve el set de offer_ids con status=applied para el user
        actual — usado por el feed para mostrar el badge "Aplicado" en
        las cards sin hidratar el JobApplication completo.

        Retorna {"applied_offer_ids": [1, 5, 12]} para que el frontend
        haga un Set() en O(1).
        """
        ids = JobApplication.objects.filter(
            user=request.user, status="applied"
        ).values_list("offer_id", flat=True)
        return Response({"applied_offer_ids": list(ids)})
