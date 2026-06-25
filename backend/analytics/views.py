"""Views de analytics.

Endpoints:
  POST /api/analytics/track/     → ingest público (rate-limited)
  GET  /api/analytics/summary/   → agregaciones (admin)

El track es fire-and-forget desde el frontend: si falla, no rompe el
flow del user — devolvemos 204 incluso ante validation soft (campos
truncados).
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.bots import is_bot
from analytics.models import AnalyticsEvent
from analytics.serializers import TrackEventSerializer


@method_decorator(
    # 120/min por IP: deja margen para SPAs que disparan varios pageviews
    # rápidos (lazy routes), pero detiene scripts maliciosos.
    ratelimit(key="ip", rate="120/m", method="POST", block=True),
    name="post",
)
class TrackView(APIView):
    """POST /api/analytics/track/

    Body: { event_type, path, label?, anon_id, referrer? }

    Filtramos bots por user-agent — no ensucian las métricas. Igual
    devolvemos 204 (no informar al bot que lo detectamos).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TrackEventSerializer(data=request.data)
        if not serializer.is_valid():
            # Devolvemos 204 igual — no queremos que el frontend reintente
            # con un evento inválido. Logueamos para debug si hace falta.
            return Response(status=status.HTTP_204_NO_CONTENT)

        ua = request.META.get("HTTP_USER_AGENT", "")[:200]
        if is_bot(ua):
            return Response(status=status.HTTP_204_NO_CONTENT)

        data = serializer.validated_data
        AnalyticsEvent.objects.create(
            event_type=data["event_type"],
            path=data["path"],
            label=data.get("label", ""),
            anon_id=data["anon_id"],
            user=request.user if request.user.is_authenticated else None,
            referrer=data.get("referrer", ""),
            user_agent=ua,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class SummaryView(APIView):
    """GET /api/analytics/summary/

    Query params:
      - days (default 30, max 90): ventana temporal de las métricas.

    Devuelve:
      - totals { pageviews, unique_visitors, cta_clicks, outbound_clicks,
                 authed_pageviews, anon_pageviews }
      - pageviews_by_day [{ date, count }]   # serie temporal del bucket
      - top_paths [{ path, count }]          # top 10
      - top_ctas  [{ label, count }]         # top 10
      - top_referrers [{ referrer, count }]  # top 10, excluye internos/blank
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError):
            days = 30
        days = max(1, min(days, 90))

        since = timezone.now() - timedelta(days=days)
        qs = AnalyticsEvent.objects.filter(created_at__gte=since)

        pageviews_qs = qs.filter(event_type=AnalyticsEvent.EVENT_PAGEVIEW)
        ctas_qs = qs.filter(event_type=AnalyticsEvent.EVENT_CTA)
        outbound_qs = qs.filter(event_type=AnalyticsEvent.EVENT_OUTBOUND)

        # Unique visitors = anon_ids distintos en el rango. No diferencia
        # auth vs anon — un user logueado mantiene su anon_id.
        unique_visitors = qs.values("anon_id").distinct().count()

        authed_pageviews = pageviews_qs.filter(user__isnull=False).count()
        anon_pageviews = pageviews_qs.filter(user__isnull=True).count()

        per_day = (
            pageviews_qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        pageviews_by_day = [
            {"date": row["day"].isoformat(), "count": row["count"]} for row in per_day
        ]

        top_paths = list(
            pageviews_qs.values("path")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        top_ctas = list(
            ctas_qs.exclude(label="")
            .values("label")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        # Referrers: ignoramos blanks y self-referrers (filtramos
        # localhost/127.0.0.1 para no contaminar con dev).
        top_referrers = list(
            qs.exclude(referrer="")
            .exclude(referrer__startswith="http://localhost")
            .exclude(referrer__startswith="http://127.0.0.1")
            .values("referrer")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        return Response(
            {
                "window_days": days,
                "totals": {
                    "pageviews": pageviews_qs.count(),
                    "unique_visitors": unique_visitors,
                    "cta_clicks": ctas_qs.count(),
                    "outbound_clicks": outbound_qs.count(),
                    "authed_pageviews": authed_pageviews,
                    "anon_pageviews": anon_pageviews,
                },
                "pageviews_by_day": pageviews_by_day,
                "top_paths": top_paths,
                "top_ctas": top_ctas,
                "top_referrers": top_referrers,
            },
            status=status.HTTP_200_OK,
        )
