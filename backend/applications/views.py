from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from applications.cover_letter_generator import (
    CoverLetterGenerationError,
    generate_cover_letter,
)
from applications.models import CoverLetter, JobApplication
from applications.serializers import CoverLetterSerializer, JobApplicationSerializer
from jobs.models import JobOffer


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


def _profile_dict_for_prompt(user) -> dict:
    """Compone el dict que consume `generate_cover_letter`.

    El perfil puede no existir todavía (user OAuth recién creado sin
    completar el wizard) — devolvemos defaults vacíos y dejamos que el
    prompt los maneje. El generator usa fallbacks tipo "profesional" /
    "varios años" para no producir prosa rota.
    """
    profile = getattr(user, "profile", None)
    if profile is None:
        return {
            "full_name": (user.first_name + " " + user.last_name).strip() or user.username,
            "professional_title": "",
            "years_experience": "",
            "city": "",
            "skills": "",
            "summary": "",
        }
    return {
        "full_name": f"{profile.first_name} {profile.last_name}".strip() or user.username,
        "professional_title": profile.professional_title or "",
        # No tenemos años_experience como campo — dejamos vacío y el prompt
        # se las arregla con "varios años" como fallback.
        "years_experience": "",
        "city": profile.city or "",
        "skills": profile.skills or "",
        "summary": profile.summary or "",
    }


@method_decorator(
    ratelimit(key="user", rate="10/h", method="POST", block=True),
    name="create",
)
class CoverLetterViewSet(viewsets.ModelViewSet):
    """ViewSet de cartas de presentación, scoped a request.user.

    Endpoints:
      - GET    /api/cover-letters/                      → lista del user
      - GET    /api/cover-letters/?job_offer_id=N       → la del oferta N (o 404)
      - POST   /api/cover-letters/                      → genera + guarda
        body: {job_offer_id, tone, language}
        Si ya existe para (user, offer) → la sobreescribe (regenerar).
      - PATCH  /api/cover-letters/{id}/                 → editar content
      - DELETE /api/cover-letters/{id}/                 → borrar

    Rate-limit: 10 generaciones POST por hora — Gemini cuesta tokens.
    PATCH/GET/DELETE no rate-limitados.

    SEGURIDAD: get_queryset filtra por user.
    """

    serializer_class = CoverLetterSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = CoverLetter.objects.filter(user=self.request.user).select_related("offer")
        # ?job_offer_id=X — para que el frontend chequee "¿ya hay carta
        # para esta oferta?" antes de mostrar el botón "Generar" vs "Ver".
        offer_id = self.request.query_params.get("job_offer_id")
        if offer_id:
            qs = qs.filter(offer_id=offer_id)
        return qs

    def create(self, request, *args, **kwargs):
        """Genera (o regenera) la carta para una oferta.

        Si ya existía para (user, offer), sobreescribe content/tone/language
        y resetea user_edited=False — el user pidió una versión nueva,
        sus ediciones previas se pierden.
        """
        offer_id = request.data.get("job_offer_id")
        tone = (request.data.get("tone") or "cercano").strip()
        language = (request.data.get("language") or "es").strip()

        if not offer_id:
            raise ValidationError({"job_offer_id": "Requerido."})
        if tone not in dict(CoverLetter.TONE_CHOICES):
            raise ValidationError({"tone": f"Tono inválido. Usá: {', '.join(dict(CoverLetter.TONE_CHOICES).keys())}"})
        if language not in dict(CoverLetter.LANGUAGE_CHOICES):
            raise ValidationError({"language": "Idioma inválido. Usá 'es' o 'en'."})

        try:
            offer = JobOffer.objects.get(pk=offer_id)
        except JobOffer.DoesNotExist:
            raise NotFound("La oferta no existe o fue eliminada.")

        try:
            content = generate_cover_letter(
                user_profile=_profile_dict_for_prompt(request.user),
                offer_title=offer.title,
                offer_company=offer.company,
                offer_description=offer.summary,
                tone=tone,
                language=language,
            )
        except CoverLetterGenerationError as exc:
            return Response(
                {"error": "generation_failed", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        letter, created = CoverLetter.objects.update_or_create(
            user=request.user,
            offer=offer,
            defaults={
                "content": content,
                "tone": tone,
                "language": language,
                "user_edited": False,
                "offer_title_snapshot": offer.title,
                "offer_company_snapshot": offer.company or "",
                "offer_url_snapshot": offer.url or "",
            },
        )
        out = CoverLetterSerializer(letter).data
        return Response(
            out,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        """PATCH — solo content es editable. Marca user_edited=True para
        que el frontend avise al regenerar."""
        instance = self.get_object()
        new_content = request.data.get("content")
        if new_content is None:
            raise ValidationError({"content": "Requerido."})
        instance.content = str(new_content).strip()
        instance.user_edited = True
        instance.save(update_fields=["content", "user_edited", "updated_at"])
        return Response(CoverLetterSerializer(instance).data)
