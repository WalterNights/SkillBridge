"""Eventos de analytics — minimalista por diseño.

Filosofía:
  - Sin cookies. El frontend genera un `anon_id` (UUID) que vive en
    localStorage. Si el user lo borra, contamos al mismo browser como
    "nuevo visitante". Aceptable a esta escala.
  - Sin IP. Privacidad y simplicidad — el bot filter es por user-agent.
  - Una sola tabla. Cada fila = un evento. Aggregations corren on-demand
    al pedir el summary; cuando el volumen crezca (>1M filas) movemos a
    rollups diarios.

Tipos de evento soportados:
  - `pageview`  : SPA route change
  - `cta_click` : botón / link relevante (con label descriptivo)
  - `outbound`  : link a sitio externo (postular, GitHub, etc.)
"""

from django.conf import settings
from django.db import models


class AnalyticsEvent(models.Model):
    EVENT_PAGEVIEW = "pageview"
    EVENT_CTA = "cta_click"
    EVENT_OUTBOUND = "outbound"
    EVENT_CHOICES = [
        (EVENT_PAGEVIEW, "Pageview"),
        (EVENT_CTA, "CTA click"),
        (EVENT_OUTBOUND, "Outbound click"),
    ]

    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES, db_index=True)
    # `path` siempre normalizado a la ruta del frontend (`/faq`, `/dashboard`,
    # etc.), SIN el host. Trimmed a 200 para acotar el storage.
    path = models.CharField(max_length=200, db_index=True)
    # Label libre — para `cta_click` describe el CTA ("home_register",
    # "faq_ask_open"), para `outbound` puede ser el destino ("linkedin",
    # "elempleo"). Vacío en pageviews.
    label = models.CharField(max_length=80, blank=True, db_index=True)

    # Anon ID generado en el front (UUIDv4). Sirve para contar visitors
    # únicos sin tocar cookies/IP. No es PII; rota si el user limpia
    # storage.
    anon_id = models.CharField(max_length=64, db_index=True)
    # User logueado al momento del evento — útil para distinguir tráfico
    # autenticado vs anónimo. NULL si era anónimo.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_events",
    )

    # Truncado a 200 — algunos referrers (Twitter share, Discord) son largos.
    referrer = models.CharField(max_length=200, blank=True)
    # User-agent sin hashear (200 chars). Sirve para device class y bot
    # filter retroactivo si llega bot que el filter inicial no capturó.
    user_agent = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Agregaciones diarias por tipo (cards de "pageviews últimos 30 días").
            models.Index(fields=["event_type", "created_at"]),
            # Top paths del summary.
            models.Index(fields=["path", "created_at"]),
            # Cálculo de unique visitors (DISTINCT anon_id por rango temporal).
            models.Index(fields=["anon_id", "created_at"]),
        ]

    def __str__(self) -> str:
        suffix = f" [{self.label}]" if self.label else ""
        return f"{self.event_type} {self.path}{suffix} @ {self.created_at:%Y-%m-%d %H:%M}"
