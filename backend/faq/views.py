"""Views del FAQ.

Endpoints:
  - Public:
      GET  /api/faq/                  → lista de FAQs publicadas
      GET  /api/faq/categories/       → lista de categorías activas
      POST /api/faq/{id}/view/        → incrementa view_count (analytics)
  - Auth required:
      POST /api/faq/ask/              → user pregunta, AI auto-responde,
                                         queda en cola de moderación
  - Admin only (IsAdminUser):
      GET    /api/faq/admin/          → todas las preguntas (?status=)
      PATCH  /api/faq/admin/{id}/     → editar/publicar/rechazar
      GET    /api/faq/admin/stats/    → métricas para el dashboard
"""

from __future__ import annotations

import logging

from django.db.models import Count, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from faq.models import FaqCategory, FaqQuestion
from faq.serializers import (
    FaqAdminSerializer,
    FaqCategorySerializer,
    FaqPublicSerializer,
    FaqSubmitSerializer,
)
from faq.services.faq_responder import FaqResponderError, generate_answer

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# PUBLIC
# ──────────────────────────────────────────────────────────────────────


class FaqPublicListView(ListAPIView):
    """GET /api/faq/ — todas las FAQs publicadas, ordenadas por
    categoría y display_order. Visible para visitantes anónimos."""

    permission_classes = [AllowAny]
    serializer_class = FaqPublicSerializer
    pagination_class = None  # FAQ es chica; cargar todo de una.

    def get_queryset(self):
        qs = (
            FaqQuestion.objects.filter(status=FaqQuestion.STATUS_PUBLISHED)
            .select_related("category")
            .order_by("category__display_order", "display_order", "id")
        )
        cat_slug = self.request.query_params.get("category")
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)
        return qs


class FaqCategoryListView(ListAPIView):
    """GET /api/faq/categories/ — categorías activas, para construir
    el árbol de navegación en el front."""

    permission_classes = [AllowAny]
    serializer_class = FaqCategorySerializer
    pagination_class = None
    queryset = FaqCategory.objects.filter(is_active=True).order_by(
        "display_order", "name"
    )


class FaqViewCountView(APIView):
    """POST /api/faq/{id}/view/ — incrementa el contador atómicamente.

    Lo llama el frontend cuando el user EXPANDE una pregunta (no por
    cargar la lista). Sin auth — un visitante anónimo cuenta igual.
    Sin rate limit — el cost-per-call es 1 UPDATE, no vale la pena.
    """

    permission_classes = [AllowAny]

    def post(self, request, pk: int):
        # F() expression para evitar race condition con incrementos
        # concurrentes. Solo afecta filas publicadas.
        updated = FaqQuestion.objects.filter(
            pk=pk, status=FaqQuestion.STATUS_PUBLISHED
        ).update(view_count=F("view_count") + 1)
        if not updated:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────────────────────────────
# USER ASK (auth)
# ──────────────────────────────────────────────────────────────────────


@method_decorator(
    # 5 preguntas por hora por user — protege contra spam y limita el
    # costo de Gemini si un user se entusiasma.
    ratelimit(key="user", rate="5/h", method="POST", block=True),
    name="post",
)
class FaqAskView(APIView):
    """POST /api/faq/ask/ — el usuario manda una pregunta, le devolvemos
    la respuesta AI inmediatamente, y queda en cola admin.

    Flow:
      1. Validar payload (10-300 chars).
      2. Llamar a Gemini → ai_draft.
      3. Crear FaqQuestion(status=pending, source=user, answer=ai_draft,
         ai_draft=ai_draft, submitted_by=request.user).
      4. Devolver {id, question, ai_answer} al frontend para mostrar
         toast/inline.

    Si Gemini falla (502/timeout), creamos la entry SIN ai_draft y
    devolvemos un mensaje genérico — la pregunta no se pierde, solo
    no tiene auto-respuesta.

    Response 200: { id, question, ai_answer, has_ai_answer }
    Response 400: validation error
    Response 429: rate limit (5/h)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FaqSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data["question"]

        ai_answer = ""
        ai_failed = False
        try:
            ai_answer = generate_answer(question)
        except FaqResponderError as exc:
            logger.info("FAQ AI auto-answer failed: %s", exc)
            ai_failed = True

        faq = FaqQuestion.objects.create(
            question=question,
            answer=ai_answer,  # admin lo puede editar antes de publicar
            ai_draft=ai_answer,
            source=FaqQuestion.SOURCE_USER,
            status=FaqQuestion.STATUS_PENDING,
            submitted_by=request.user,
        )

        return Response(
            {
                "id": faq.id,
                "question": faq.question,
                "ai_answer": ai_answer,
                "has_ai_answer": not ai_failed,
                "detail": (
                    "Tu pregunta llegó. Un admin la revisará antes de publicarla."
                    if not ai_failed
                    else (
                        "Tu pregunta llegó. No pudimos generar una respuesta "
                        "automática esta vez; un admin la responderá pronto."
                    )
                ),
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────
# ADMIN
# ──────────────────────────────────────────────────────────────────────


class FaqAdminListView(ListCreateAPIView):
    """GET /api/faq/admin/   — lista paginada para la cola de moderación.
    POST /api/faq/admin/     — el admin crea una FAQ curada manualmente.

    GET filtros:
      - ?status=pending|published|rejected|all (default: pending)
      - ?source=user|seed

    POST shape esperado:
      { question, answer, category_id?, status? }

    Reglas del POST (forzadas por perform_create, no por el cliente):
      - `source` se setea a `seed` siempre — esta vía es para curaduría
        del admin, no para preguntas de usuarios.
      - `submitted_by` queda en NULL (no es una pregunta enviada por user).
      - `status` default = `published` para que aparezca de una en /faq.
      - Si `status` = `published`, registramos al admin como moderador
        + timestamp (audit trail).
    """

    permission_classes = [IsAdminUser]
    serializer_class = FaqAdminSerializer

    def get_queryset(self):
        qs = FaqQuestion.objects.select_related(
            "category", "submitted_by", "moderated_by"
        ).order_by("-created_at")
        status_filter = self.request.query_params.get("status", "pending")
        if status_filter != "all":
            qs = qs.filter(status=status_filter)
        source = self.request.query_params.get("source")
        if source:
            qs = qs.filter(source=source)
        return qs

    def perform_create(self, serializer):
        # `source` y `submitted_by` están en `read_only_fields` del
        # serializer (defensa contra mass-assignment), así que el cliente
        # no los puede setear — los forzamos acá.
        requested_status = self.request.data.get("status") or FaqQuestion.STATUS_PUBLISHED
        moderation = {}
        if requested_status == FaqQuestion.STATUS_PUBLISHED:
            moderation = {
                "moderated_by": self.request.user,
                "moderated_at": timezone.now(),
            }
        serializer.save(
            source=FaqQuestion.SOURCE_SEED,
            submitted_by=None,
            status=requested_status,
            ai_draft="",  # nunca hay draft AI en curaduría manual
            **moderation,
        )


class FaqAdminDetailView(APIView):
    """PATCH /api/faq/admin/{id}/ — edita una FAQ (publicar/rechazar/
    cambiar categoría/editar respuesta).

    Cuando el `status` cambia, registra moderated_by + moderated_at
    para auditoría. Si el admin rechaza, puede mandar `moderation_note`
    explicando por qué (ofensivo, irrelevante, duplicado, etc.).
    """

    permission_classes = [IsAdminUser]

    def get(self, request, pk: int):
        faq = get_object_or_404(FaqQuestion, pk=pk)
        return Response(FaqAdminSerializer(faq).data)

    def patch(self, request, pk: int):
        faq = get_object_or_404(FaqQuestion, pk=pk)
        serializer = FaqAdminSerializer(faq, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        status_changed = (
            "status" in request.data and request.data["status"] != faq.status
        )
        instance = serializer.save()

        if status_changed:
            instance.moderated_by = request.user
            instance.moderated_at = timezone.now()
            instance.save(update_fields=["moderated_by", "moderated_at"])

        return Response(FaqAdminSerializer(instance).data)

    def delete(self, request, pk: int):
        """DELETE = hard-delete. Úsese solo para spam evidente / pruebas.
        Para "rechazo con tracking", usar PATCH status=rejected."""
        faq = get_object_or_404(FaqQuestion, pk=pk)
        faq.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FaqAdminStatsView(APIView):
    """GET /api/faq/admin/stats/ — métricas para el panel admin.

    Devuelve:
      - total preguntas (por status)
      - total ratio de aprobación (publicadas / no-pendientes)
      - top categorías con más preguntas
      - últimas 5 preguntas user (para overview rápido)
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        by_status = list(
            FaqQuestion.objects.values("status").annotate(count=Count("id"))
        )
        totals = {row["status"]: row["count"] for row in by_status}
        total = sum(totals.values())
        published = totals.get(FaqQuestion.STATUS_PUBLISHED, 0)
        rejected = totals.get(FaqQuestion.STATUS_REJECTED, 0)
        pending = totals.get(FaqQuestion.STATUS_PENDING, 0)
        decided = published + rejected
        approval_rate_pct = (published / decided * 100) if decided > 0 else 0.0

        by_category = list(
            FaqQuestion.objects.filter(category__isnull=False)
            .values("category__name", "category__slug")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        by_source = list(
            FaqQuestion.objects.values("source").annotate(count=Count("id"))
        )

        recent_user_questions = list(
            FaqQuestion.objects.filter(source=FaqQuestion.SOURCE_USER)
            .order_by("-created_at")
            .values("id", "question", "status", "created_at")[:5]
        )

        return Response(
            {
                "totals": {
                    "all": total,
                    "pending": pending,
                    "published": published,
                    "rejected": rejected,
                },
                "approval_rate_pct": round(approval_rate_pct, 1),
                "by_category": by_category,
                "by_source": by_source,
                "recent_user_questions": recent_user_questions,
            },
            status=status.HTTP_200_OK,
        )
