"""Tests del módulo analytics — ingest, bot filter, agregaciones, admin gate."""

from datetime import timedelta

import pytest
from django.utils import timezone

from analytics.bots import is_bot
from analytics.models import AnalyticsEvent


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache():
    """El rate-limit del POST /track/ (120/min/ip) comparte el bucket
    entre tests. Reset antes/después para evitar cross-contamination."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


_REAL_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


# ──────────────────────────────────────────────────────────────────────
# Bot filter (puro)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestBotDetector:
    def test_real_chrome_is_not_bot(self):
        assert is_bot(_REAL_UA) is False

    def test_empty_ua_is_bot(self):
        """UA vacío es bot — un browser real siempre manda UA."""
        assert is_bot("") is True
        assert is_bot(None) is True

    def test_googlebot_is_bot(self):
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        assert is_bot(ua) is True

    def test_curl_is_bot(self):
        assert is_bot("curl/8.4.0") is True

    def test_ahrefsbot_is_bot(self):
        assert is_bot("Mozilla/5.0 (compatible; AhrefsBot/7.0)") is True

    def test_headless_chrome_is_bot(self):
        ua = "Mozilla/5.0 HeadlessChrome/120.0.0.0 Safari/537.36"
        assert is_bot(ua) is True


# ──────────────────────────────────────────────────────────────────────
# Track endpoint
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.django_db
class TestTrackEndpoint:
    URL = "/api/analytics/track/"

    def test_anon_pageview_is_recorded(self, api_client):
        response = api_client.post(
            self.URL,
            {"event_type": "pageview", "path": "/faq", "anon_id": "abc123de"},
            format="json",
            HTTP_USER_AGENT=_REAL_UA,
        )
        assert response.status_code == 204
        ev = AnalyticsEvent.objects.get()
        assert ev.event_type == "pageview"
        assert ev.path == "/faq"
        assert ev.anon_id == "abc123de"
        assert ev.user is None
        assert _REAL_UA[:50] in ev.user_agent  # se guarda truncado

    def test_logged_user_is_attached(self, api_client, user):
        api_client.force_authenticate(user=user)
        api_client.post(
            self.URL,
            {"event_type": "pageview", "path": "/dashboard", "anon_id": "anon-xyz1"},
            format="json",
            HTTP_USER_AGENT=_REAL_UA,
        )
        ev = AnalyticsEvent.objects.get()
        assert ev.user == user

    def test_bot_ua_is_dropped_silently(self, api_client):
        """Un bot recibe 204 (sin pista de que lo bloqueamos) pero la
        fila NO se crea."""
        response = api_client.post(
            self.URL,
            {"event_type": "pageview", "path": "/faq", "anon_id": "bot-1"},
            format="json",
            HTTP_USER_AGENT="Mozilla/5.0 (compatible; Googlebot/2.1)",
        )
        assert response.status_code == 204
        assert AnalyticsEvent.objects.count() == 0

    def test_missing_ua_is_treated_as_bot(self, api_client):
        response = api_client.post(
            self.URL,
            {"event_type": "pageview", "path": "/faq", "anon_id": "no-ua"},
            format="json",
        )
        assert response.status_code == 204
        assert AnalyticsEvent.objects.count() == 0

    def test_invalid_event_type_is_dropped_with_204(self, api_client):
        """No queremos que el frontend reintente con shape inválido —
        respondemos 204 incluso ante validation failure."""
        response = api_client.post(
            self.URL,
            {"event_type": "INVALID", "path": "/faq", "anon_id": "x" * 10},
            format="json",
            HTTP_USER_AGENT=_REAL_UA,
        )
        assert response.status_code == 204
        assert AnalyticsEvent.objects.count() == 0

    def test_path_is_normalized_with_leading_slash(self, api_client):
        api_client.post(
            self.URL,
            {"event_type": "pageview", "path": "faq", "anon_id": "ok-id-12"},
            format="json",
            HTTP_USER_AGENT=_REAL_UA,
        )
        assert AnalyticsEvent.objects.get().path == "/faq"

    def test_cta_event_with_label(self, api_client):
        api_client.post(
            self.URL,
            {
                "event_type": "cta_click",
                "path": "/",
                "label": "home_hero_register",
                "anon_id": "anon-cta",
            },
            format="json",
            HTTP_USER_AGENT=_REAL_UA,
        )
        ev = AnalyticsEvent.objects.get()
        assert ev.event_type == "cta_click"
        assert ev.label == "home_hero_register"


# ──────────────────────────────────────────────────────────────────────
# Summary endpoint
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.django_db
class TestSummaryEndpoint:
    URL = "/api/analytics/summary/"

    def test_requires_admin(self, authed_client):
        response = authed_client.get(self.URL)
        assert response.status_code == 403

    def test_anon_is_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_summary_aggregates_correctly(self, api_client, admin_user):
        # Setup: 3 visitors distintos, 5 pageviews, 2 CTA clicks, 1 outbound
        AnalyticsEvent.objects.create(
            event_type="pageview", path="/", anon_id="a1", user_agent=_REAL_UA
        )
        AnalyticsEvent.objects.create(
            event_type="pageview", path="/", anon_id="a2", user_agent=_REAL_UA
        )
        AnalyticsEvent.objects.create(
            event_type="pageview", path="/faq", anon_id="a1", user_agent=_REAL_UA
        )
        AnalyticsEvent.objects.create(
            event_type="pageview", path="/faq", anon_id="a2", user_agent=_REAL_UA
        )
        AnalyticsEvent.objects.create(
            event_type="pageview", path="/dashboard", anon_id="a3", user_agent=_REAL_UA
        )
        AnalyticsEvent.objects.create(
            event_type="cta_click",
            path="/",
            label="home_register",
            anon_id="a1",
            user_agent=_REAL_UA,
        )
        AnalyticsEvent.objects.create(
            event_type="cta_click",
            path="/",
            label="home_register",
            anon_id="a2",
            user_agent=_REAL_UA,
        )
        AnalyticsEvent.objects.create(
            event_type="outbound",
            path="/jobs/42",
            label="linkedin",
            anon_id="a3",
            user_agent=_REAL_UA,
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.get(self.URL)
        assert response.status_code == 200
        body = response.json()

        assert body["window_days"] == 30
        assert body["totals"]["pageviews"] == 5
        assert body["totals"]["unique_visitors"] == 3
        assert body["totals"]["cta_clicks"] == 2
        assert body["totals"]["outbound_clicks"] == 1
        # Top path es "/" y "/faq" empatados en 2; "/dashboard" en 1.
        top_paths = {row["path"]: row["count"] for row in body["top_paths"]}
        assert top_paths["/"] == 2
        assert top_paths["/faq"] == 2
        assert top_paths["/dashboard"] == 1
        # Top CTA
        assert body["top_ctas"][0]["label"] == "home_register"
        assert body["top_ctas"][0]["count"] == 2

    def test_events_outside_window_are_excluded(self, api_client, admin_user):
        old = AnalyticsEvent.objects.create(
            event_type="pageview", path="/old", anon_id="old", user_agent=_REAL_UA
        )
        AnalyticsEvent.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=100)
        )
        AnalyticsEvent.objects.create(
            event_type="pageview", path="/new", anon_id="new", user_agent=_REAL_UA
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(self.URL + "?days=30")
        body = response.json()
        paths = [row["path"] for row in body["top_paths"]]
        assert "/new" in paths
        assert "/old" not in paths

    def test_days_param_is_clamped(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        # 9999 → debería capear a 90
        response = api_client.get(self.URL + "?days=9999")
        assert response.status_code == 200
        assert response.json()["window_days"] == 90
        # 0 → debería min a 1
        response = api_client.get(self.URL + "?days=0")
        assert response.json()["window_days"] == 1

    def test_referrer_filters_localhost(self, api_client, admin_user):
        AnalyticsEvent.objects.create(
            event_type="pageview",
            path="/",
            anon_id="x",
            referrer="http://localhost:4200/blog",
            user_agent=_REAL_UA,
        )
        AnalyticsEvent.objects.create(
            event_type="pageview",
            path="/",
            anon_id="y",
            referrer="https://twitter.com/share/abc",
            user_agent=_REAL_UA,
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(self.URL)
        referrers = [row["referrer"] for row in response.json()["top_referrers"]]
        assert "https://twitter.com/share/abc" in referrers
        assert not any("localhost" in r for r in referrers)
