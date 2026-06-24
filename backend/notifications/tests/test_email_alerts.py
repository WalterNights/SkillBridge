"""Tests de la tarea send_daily_match_alerts.

Mockean el SMTP via Django mail.outbox (locmem backend, default en tests)
para verificar que se enviaron los emails sin pegarle a un servidor real.
"""

from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from jobs.models import JobOffer
from notifications.tasks import send_daily_match_alerts
from users.models import UserProfile


@pytest.fixture
def profile_with_skills(user):
    """Perfil completo con skills tech — matcheará una oferta tech."""
    return UserProfile.objects.create(
        user=user,
        first_name="Alice",
        last_name="Doe",
        phone="+5491112345678",
        city="Buenos Aires",
        professional_title="Backend Developer",
        skills="python, django, postgresql, docker, aws",
        experience="5 años de backend.",
    )


@pytest.fixture
def matching_offer():
    """Oferta que va a tener match >85% con profile_with_skills."""
    return JobOffer.objects.create(
        title="Backend Developer Python",
        company="Acme Tech",
        location="Buenos Aires, Argentina",
        summary="Buscamos Backend Developer con experiencia en Python, Django, PostgreSQL, Docker y AWS.",
        keywords="python, django, postgresql, docker, aws",
        url="https://x.com/offer/1",
        portal="other",
    )


@pytest.fixture
def non_matching_offer():
    """Oferta sin match — skills completamente diferentes."""
    return JobOffer.objects.create(
        title="Diseñador UX Senior",
        company="Design Co",
        location="México DF",
        summary="UX designer con Figma, Sketch, Adobe XD.",
        keywords="figma, sketch, adobe xd",
        url="https://x.com/offer/2",
        portal="other",
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestSendDailyMatchAlerts:
    def test_sends_email_for_high_match(self, profile_with_skills, matching_offer):
        mail.outbox.clear()
        metrics = send_daily_match_alerts()
        assert metrics["users_processed"] == 1
        assert metrics["emails_sent"] == 1
        assert metrics["errors"] == 0
        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == [profile_with_skills.user.email]
        assert matching_offer.title in sent.body  # plain text body
        # HTML alternative también presente
        assert any(
            "text/html" in alt[1] for alt in sent.alternatives
        )

    def test_skips_user_with_alerts_disabled(self, profile_with_skills, matching_offer):
        profile_with_skills.email_alerts_enabled = False
        profile_with_skills.save()
        mail.outbox.clear()
        metrics = send_daily_match_alerts()
        assert metrics["users_processed"] == 0  # ni siquiera se itera
        assert metrics["emails_sent"] == 0
        assert len(mail.outbox) == 0

    def test_no_email_when_no_matches(
        self, profile_with_skills, non_matching_offer
    ):
        # Solo hay una oferta de diseño — el perfil tech no matchea
        mail.outbox.clear()
        metrics = send_daily_match_alerts()
        assert metrics["users_processed"] == 1
        assert metrics["emails_sent"] == 0
        assert len(mail.outbox) == 0

    def test_skips_recent_send(self, profile_with_skills, matching_offer):
        # Simulamos que el último envío fue hace 5 horas
        profile_with_skills.last_alert_sent_at = timezone.now() - timedelta(hours=5)
        profile_with_skills.save()
        mail.outbox.clear()
        metrics = send_daily_match_alerts()
        assert metrics["users_processed"] == 1
        assert metrics["skipped_recent"] == 1
        assert metrics["emails_sent"] == 0

    def test_resends_after_dedup_window(
        self, profile_with_skills, matching_offer
    ):
        # Si el último envío fue hace 25h (>20h cutoff), sí enviamos
        profile_with_skills.last_alert_sent_at = timezone.now() - timedelta(hours=25)
        profile_with_skills.save()
        mail.outbox.clear()
        metrics = send_daily_match_alerts()
        assert metrics["emails_sent"] == 1

    def test_updates_last_alert_sent_at_after_send(
        self, profile_with_skills, matching_offer
    ):
        assert profile_with_skills.last_alert_sent_at is None
        mail.outbox.clear()
        send_daily_match_alerts()
        profile_with_skills.refresh_from_db()
        assert profile_with_skills.last_alert_sent_at is not None

    def test_skips_old_offers(self, profile_with_skills):
        # Oferta de hace 48h — fuera de la ventana de 24h
        old = JobOffer.objects.create(
            title="Backend Python Senior",
            company="Old Co",
            location="BA",
            summary="Python Django Docker",
            keywords="python, django, docker",
            url="https://x.com/old",
            portal="other",
        )
        old.created_at = timezone.now() - timedelta(hours=48)
        old.save()

        mail.outbox.clear()
        metrics = send_daily_match_alerts()
        assert metrics["emails_sent"] == 0

    def test_ignores_incomplete_profiles(
        self, django_user_model, matching_offer
    ):
        bob = django_user_model.objects.create_user(
            username="bob", email="bob@example.com", password="bobpass123"
        )
        # Profile sin professional_title — incompleto
        UserProfile.objects.create(
            user=bob,
            first_name="Bob",
            last_name="X",
            phone="+11",
            city="",  # sin city tampoco
            professional_title="",
            skills="python, django",
            experience="",
        )
        mail.outbox.clear()
        metrics = send_daily_match_alerts()
        assert metrics["users_processed"] == 0  # bob no califica
