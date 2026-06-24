from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from applications.models import JobApplication
from applications.serializers import JobApplicationSerializer


# Set de status válidos para validar transiciones — congelamos en módulo
# para evitar recalcularlo en cada request al endpoint update-status.
_VALID_STATUSES = {choice for choice, _ in JobApplication.STATUS_CHOICES}


class JobApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet del modelo JobApplication, scoped a request.user.

    Endpoints:
      - GET    /api/applications/                       → lista del user
      - GET    /api/applications/?active=true           → solo no cerradas
      - POST   /api/applications/                       → crear (status=pending)
      - DELETE /api/applications/{id}/                  → undo (si dijo "no")
      - PATCH  /api/applications/{id}/                  → editar notes
      - POST   /api/applications/{id}/confirm/          → status=applied
      - POST   /api/applications/{id}/update-status/    → mover entre estados
      - GET    /api/applications/applied-ids/           → set de offer_ids
                                                          para el badge en el feed
      - GET    /api/applications/status-options/        → lista de status válidos
                                                          (label + value) para
                                                          el dropdown del front

    SEGURIDAD: get_queryset filtra por user → un user no puede leer ni
    mutar applications de otro (404 antes que 403, sin leak).
    """

    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # lista chica (~10s-100s) — front filtra/scrollea

    def get_queryset(self):
        qs = JobApplication.objects.filter(user=self.request.user).select_related("offer")
        # ?active=true filtra a estados "vivos" (no cerrados). El frontend
        # lo usa para la tab "Activas" del view de Mis postulaciones.
        if self.request.query_params.get("active") == "true":
            qs = qs.filter(status__in=JobApplication.ACTIVE_STATUSES)
        # ?status=X filtra por un estado puntual — útil para la tab por
        # estado (interview, offer, etc).
        single_status = self.request.query_params.get("status")
        if single_status and single_status in _VALID_STATUSES:
            qs = qs.filter(status=single_status)
        return qs

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
        application.status_changed_at = timezone.now()
        application.save(update_fields=["status", "applied_at", "status_changed_at"])
        return Response(JobApplicationSerializer(application).data)

    @action(detail=True, methods=["post"], url_path="update-status")
    def update_status(self, request, pk=None):
        """Mover la postulación entre estados.

        Body: {"status": "interview"} (o cualquier valor de STATUS_CHOICES).

        No enforcemos transiciones válidas — los procesos de HR son
        caóticos en la realidad. Cualquier estado-destino es legal.

        Side effects:
          - status_changed_at = now (siempre, sirve para sorting).
          - Si pasa de pending/cualquiera a applied y no había applied_at,
            lo seteamos. Si ya tenía applied_at, no lo pisamos.
        """
        application = self.get_object()
        new_status = (request.data.get("status") or "").strip()
        if new_status not in _VALID_STATUSES:
            raise ValidationError(
                {"status": f"'{new_status}' no es un estado válido."}
            )
        application.status = new_status
        application.status_changed_at = timezone.now()
        fields_to_update = ["status", "status_changed_at"]
        if new_status == "applied" and application.applied_at is None:
            application.applied_at = timezone.now()
            fields_to_update.append("applied_at")
        application.save(update_fields=fields_to_update)
        return Response(JobApplicationSerializer(application).data)

    @action(detail=False, methods=["get"], url_path="status-options")
    def status_options(self, request):
        """Devuelve los estados disponibles con label legible.

        Frontend usa esto para poblar el dropdown del cambio de status
        sin hardcodear los choices del modelo — si agregamos un estado
        nuevo en el backend, el frontend lo recoge automáticamente.
        """
        return Response(
            {
                "options": [
                    {"value": value, "label": label}
                    for value, label in JobApplication.STATUS_CHOICES
                ],
                "active_statuses": sorted(JobApplication.ACTIVE_STATUSES),
            }
        )

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
