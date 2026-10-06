"""Tests de las preferencias persistentes del feed.

Cubre:
- Orden: "al final" gana sobre "primero"; el orden previo se respeta
  dentro de cada grupo; sin preferencias no cambia nada.
- Endpoint GET/PUT /api/jobs/jobs/preferences/: validación y persistencia.
- El feed aplica las preferencias guardadas sin esconder ofertas.
"""

import pytest

from jobs.models import JobOffer
from jobs.services.feed_preferences import apply_feed_preferences

PREFS_URL = "/api/jobs/jobs/preferences/"


def _offer(title: str, country: str = "CO", modality: str = "onsite") -> JobOffer:
    return JobOffer.objects.create(
        title=title,
        company="Acme",
        location="",
        summary="Backend Python Django",
        keywords="python, django",
        url=f"https://example.com/{title}",
        country=country,
        modality=modality,
        category="tech",
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestApplyFeedPreferences:
    def test_no_preferences_keeps_order(self):
        offers = [_offer("a", "ES"), _offer("b", "CO")]
        assert apply_feed_preferences(offers, {}) == offers

    def test_demoted_country_goes_last_and_preferred_first(self):
        es = _offer("es", "ES", "remote")
        onsite = _offer("onsite", "CO", "onsite")
        remote = _offer("remote", "CO", "remote")
        mx = _offer("mx", "MX", "onsite")
        prefs = {
            "modalities_first": ["remote"],
            "countries_first": ["MX"],
            "countries_last": ["ES"],
        }

        result = apply_feed_preferences([es, onsite, remote, mx], prefs)

        # remote y MX primero (en su orden original), después el resto, ES al
        # final aunque sea remota: "al final" gana.
        assert result == [remote, mx, onsite, es]

    def test_tolerates_corrupt_saved_data(self):
        offers = [_offer("a")]
        assert apply_feed_preferences(offers, {"countries_last": "ES"}) == offers


@pytest.mark.integration
@pytest.mark.django_db
class TestPreferencesEndpoint:
    def test_get_defaults_to_empty(self, authed_client, user_profile):
        body = authed_client.get(PREFS_URL).json()
        assert body == {"modalities_first": [], "countries_first": [], "countries_last": []}

    def test_put_normalizes_and_persists(self, authed_client, user_profile):
        r = authed_client.put(
            PREFS_URL,
            {"modalities_first": ["remote", "remote"], "countries_last": ["es"]},
            format="json",
        )
        assert r.status_code == 200
        user_profile.refresh_from_db()
        assert user_profile.feed_preferences == {
            "modalities_first": ["remote"],
            "countries_first": [],
            "countries_last": ["ES"],
        }

    @pytest.mark.parametrize(
        "payload",
        [
            {"modalities_first": ["unknown"]},
            {"countries_first": ["COL"]},
            {"countries_first": ["CO"], "countries_last": ["co"]},
        ],
    )
    def test_put_rejects_invalid(self, authed_client, user_profile, payload):
        assert authed_client.put(PREFS_URL, payload, format="json").status_code == 400

    def test_put_without_profile_is_rejected(self, authed_client):
        assert authed_client.put(PREFS_URL, {}, format="json").status_code == 400

    def test_requires_auth(self, api_client):
        assert api_client.get(PREFS_URL).status_code == 401


@pytest.mark.integration
@pytest.mark.django_db
def test_feed_applies_saved_preferences(authed_client, user_profile):
    es = _offer("spain", "ES")
    co = _offer("colombia", "CO")
    user_profile.feed_preferences = {"countries_last": ["ES"]}
    user_profile.save(update_fields=["feed_preferences"])

    body = authed_client.get("/api/jobs/jobs/?min_match=0").json()
    results = body["results"] if isinstance(body, dict) else body
    ids = [o["id"] for o in results]

    assert ids.index(co.id) < ids.index(es.id)
    assert es.id in ids  # relegada, no escondida
