"""Tests del WebSearchJobsScraper (backend: DuckDuckGo HTML).

Cubre las partes que más se rompen en producción:
- Construcción del query (operadores `site:`)
- Detección de rate-limit
- Parsing del SERP con whitelist por dominio
- Descarte de ads (URLs `/y.js?ad_domain=...`)
- Unwrap de URLs envueltas en `/l/?uddg=...`
- Heurísticas de empresa/ubicación

NO le pega a DDG real — el SERP es fixture estática inline.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from jobs.adapters.scrapers.base import ScraperError
from jobs.adapters.scrapers.web_search import (
    WebSearchJobsScraper,
    _JOB_SITES_AGRO,
    _JOB_SITES_CREATIVE,
    _JOB_SITES_GENERAL,
    _is_individual_offer_url,
)


def _fake_response(text: str = "", status_code: int = 200):
    """Mock liviano que sólo expone los campos que el scraper toca."""

    class _R:
        def __init__(self):
            self.text = text
            self.status_code = status_code
            self.content = text.encode("utf-8")

    return _R()


@pytest.fixture
def _no_linkedin_probe():
    """Patch del probe activo de LinkedIn — los tests de search() que
    procesan URLs de LinkedIn lo usan para evitar I/O real."""
    with patch(
        "jobs.adapters.scrapers.web_search.WebSearchJobsScraper._is_linkedin_offer_closed",
        return_value=False,
    ):
        yield


# Fixture imita el layout real de DDG HTML: cada `.result` tiene
# `a.result__a` con título y href, y `.result__snippet` con descripción.
# Incluye un ad y un resultado fuera de scope para validar el filtrado.
_SERP_HTML = """
<html><body>
  <div class="result results_links">
    <h2 class="result__title">
      <a class="result__a" href="https://duckduckgo.com/y.js?ad_domain=udemy.com&ad_provider=bingv7aa">
        Curso Full Stack Developer en Udemy
      </a>
    </h2>
    <a class="result__snippet">Aprende programación.</a>
  </div>
  <div class="result results_links">
    <h2 class="result__title">
      <a class="result__a" href="https://www.linkedin.com/jobs/view/123456">
        Senior Full Stack Developer at Acme Corp
      </a>
    </h2>
    <a class="result__snippet">
      Acme Corp · Bogotá, Colombia · Hace 2 días.
      Buscamos un developer con experiencia en React, Node.js y PostgreSQL.
    </a>
  </div>
  <div class="result results_links">
    <h2 class="result__title">
      <a class="result__a" href="https://www.elempleo.com/co/ofertas-trabajo/desarrollador-bogota/12345678">
        Desarrollador Backend
      </a>
    </h2>
    <a class="result__snippet">TechSolutions · Medellín · Hace 1 día. Python, Django, AWS.</a>
  </div>
  <div class="result results_links">
    <h2 class="result__title">
      <a class="result__a" href="https://random-unrelated-blog.com/article/jobs-2024">
        10 mejores ofertas de empleo
      </a>
    </h2>
    <a class="result__snippet">Blog post irrelevante.</a>
  </div>
  <div class="result results_links">
    <h2 class="result__title">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fco.linkedin.com%2Fjobs%2Fview%2F999">
        Junior Full Stack Developer
      </a>
    </h2>
    <a class="result__snippet">Startup Inc · Remoto · Hace 3 días.</a>
  </div>
</body></html>
"""


@pytest.mark.unit
class TestBuildQuery:
    def test_includes_query_and_location_in_quotes(self):
        q = WebSearchJobsScraper._build_query(
            "Full Stack Developer", "Medellín", sites=_JOB_SITES_GENERAL
        )
        assert '"Full Stack Developer"' in q
        assert '"Medellín"' in q

    def test_includes_at_least_one_site_operator(self):
        q = WebSearchJobsScraper._build_query(
            "Backend", "Bogotá", sites=_JOB_SITES_GENERAL
        )
        assert "site:linkedin.com/jobs" in q
        assert "site:elempleo.com" in q

    def test_empty_location_is_ok(self):
        q = WebSearchJobsScraper._build_query(
            "Backend Developer", "", sites=_JOB_SITES_GENERAL
        )
        assert '""' not in q
        assert '"Backend Developer"' in q

    def test_creative_sites_query_only_includes_creative_portals(self):
        """Pasada `creative` debe usar exclusivamente los portales de
        diseño/freelance — sin LinkedIn/Elempleo ahogándolos en la SERP."""
        q = WebSearchJobsScraper._build_query(
            "diseñador UX", "Bogotá", sites=_JOB_SITES_CREATIVE
        )
        assert "site:domestika.org" in q
        assert "site:behance.net" in q
        assert "site:workana.com" in q
        assert "site:dribbble.com" in q
        assert "site:freelancer.com" in q
        # Garantía clave: NO se mezclan los generales en esta pasada.
        assert "site:linkedin.com" not in q
        assert "site:elempleo.com" not in q

    def test_agro_sites_query_only_includes_agro_portals(self):
        """Pasada `agro` debe usar exclusivamente portales del sector
        — sin que LinkedIn/Elempleo dominen la SERP. Caso del cliente
        zootecnista que reportó 0 ofertas (2026-06-27)."""
        q = WebSearchJobsScraper._build_query(
            "zootecnista", "Bogotá", sites=_JOB_SITES_AGRO
        )
        assert "site:agrojobs.com" in q
        assert "site:agcareers.com" in q
        # Garantía: NO mezclar con generales/creativos en esta pasada.
        assert "site:linkedin.com" not in q
        assert "site:domestika.org" not in q

    def test_exclude_linkedin_filters_only_from_general(self):
        """`exclude_linkedin=True` en la pasada general debe sacar LinkedIn
        y agregar el `-site:linkedin.com` negativo."""
        q = WebSearchJobsScraper._build_query(
            "Backend", "Bogotá", sites=_JOB_SITES_GENERAL, exclude_linkedin=True
        )
        assert "site:linkedin.com/jobs" not in q
        assert "-site:linkedin.com" in q
        # Los otros generales siguen.
        assert "site:elempleo.com" in q


@pytest.mark.unit
class TestRateLimitDetection:
    def test_unusual_traffic_marker_detected(self):
        assert WebSearchJobsScraper._is_rate_limited(
            "<html>Our systems have detected unusual traffic...</html>"
        )

    def test_normal_serp_is_not_rate_limited(self):
        assert not WebSearchJobsScraper._is_rate_limited(_SERP_HTML)


@pytest.mark.unit
class TestUnwrapUrl:
    def test_direct_https_url_is_returned_unchanged(self):
        assert (
            WebSearchJobsScraper._unwrap_url("https://linkedin.com/jobs/view/1")
            == "https://linkedin.com/jobs/view/1"
        )

    def test_scheme_relative_url_gets_https_prefix(self):
        assert (
            WebSearchJobsScraper._unwrap_url("//elempleo.com/oferta/123")
            == "https://elempleo.com/oferta/123"
        )

    def test_ddg_redirect_unwraps_to_uddg_target(self):
        result = WebSearchJobsScraper._unwrap_url(
            "//duckduckgo.com/l/?uddg=https%3A%2F%2Flinkedin.com%2Fjobs%2F1"
        )
        assert result == "https://linkedin.com/jobs/1"

    def test_ad_redirect_is_dropped(self):
        assert (
            WebSearchJobsScraper._unwrap_url(
                "https://duckduckgo.com/y.js?ad_domain=udemy.com"
            )
            == ""
        )

    def test_empty_href_returns_empty(self):
        assert WebSearchJobsScraper._unwrap_url("") == ""


@pytest.mark.unit
@pytest.mark.usefixtures("_no_linkedin_probe")
class TestSearch:
    def test_empty_query_raises(self):
        with pytest.raises(ScraperError, match="query es obligatorio"):
            WebSearchJobsScraper().search("", "Bogotá")

    def test_returns_only_whitelisted_domains(self):
        """El blog random + el ad de Udemy deben descartarse."""
        scraper = WebSearchJobsScraper()
        with patch("requests.post", return_value=_fake_response(_SERP_HTML)):
            offers = scraper.search("Developer", "Bogotá")

        urls = [o.url for o in offers]
        assert "https://www.linkedin.com/jobs/view/123456" in urls
        assert "https://www.elempleo.com/co/ofertas-trabajo/desarrollador-bogota/12345678" in urls
        # El blog NO debe estar
        assert all("random-unrelated-blog" not in u for u in urls)
        # El ad NO debe estar
        assert all("y.js" not in u for u in urls)

    def test_unwraps_ddg_redirect_urls(self):
        """Los `/l/?uddg=...` deben quedar con la URL real, no la wrapper."""
        scraper = WebSearchJobsScraper()
        with patch("requests.post", return_value=_fake_response(_SERP_HTML)):
            offers = scraper.search("Developer", "Bogotá")

        urls = [o.url for o in offers]
        assert "https://co.linkedin.com/jobs/view/999" in urls
        assert all("duckduckgo.com/l/" not in u for u in urls)

    def test_tags_all_offers_as_websearch_portal(self):
        scraper = WebSearchJobsScraper()
        with patch("requests.post", return_value=_fake_response(_SERP_HTML)):
            offers = scraper.search("Developer", "Bogotá")
        assert offers
        assert all(o.portal == "websearch" for o in offers)

    def test_infers_company_from_snippet(self):
        scraper = WebSearchJobsScraper()
        with patch("requests.post", return_value=_fake_response(_SERP_HTML)):
            offers = scraper.search("Developer", "Bogotá")

        linkedin_offer = next(o for o in offers if "linkedin.com/jobs/view/123456" in o.url)
        assert linkedin_offer.company == "Acme Corp"

    def test_extracts_keywords_from_snippet(self):
        scraper = WebSearchJobsScraper()
        with patch("requests.post", return_value=_fake_response(_SERP_HTML)):
            offers = scraper.search("Developer", "Bogotá")

        linkedin_offer = next(o for o in offers if "linkedin.com/jobs/view/123456" in o.url)
        assert any(
            kw in linkedin_offer.keywords for kw in ("react", "node", "postgresql")
        )

    def test_rate_limit_response_returns_empty(self):
        scraper = WebSearchJobsScraper()
        captcha = "<html>Our systems detected unusual traffic</html>"
        with patch("requests.post", return_value=_fake_response(captcha)):
            offers = scraper.search("Developer", "Bogotá")
        assert offers == []

    def test_http_error_returns_empty(self):
        scraper = WebSearchJobsScraper()
        with patch("requests.post", return_value=_fake_response("", status_code=429)):
            offers = scraper.search("Developer", "Bogotá")
        assert offers == []

    def test_network_failure_returns_empty(self):
        scraper = WebSearchJobsScraper()
        with patch(
            "requests.post",
            side_effect=requests.RequestException("connection reset"),
        ):
            offers = scraper.search("Developer", "Bogotá")
        assert offers == []


@pytest.mark.unit
class TestInferCompany:
    def test_first_chunk_before_separator_is_company(self):
        assert (
            WebSearchJobsScraper._infer_company(
                "Acme Corp · Bogotá · Hace 2 días", "Fallback"
            )
            == "Acme Corp"
        )

    def test_date_at_start_falls_back(self):
        assert (
            WebSearchJobsScraper._infer_company(
                "Hace 5 días · Empresa · ...", "Fallback"
            )
            == "Fallback"
        )

    def test_empty_snippet_uses_fallback(self):
        assert WebSearchJobsScraper._infer_company("", "LinkedIn") == "LinkedIn"


@pytest.mark.unit
class TestClosedSnippetFilter:
    """Pre-filter zero-cost: descartar ofertas con marker explícito de
    cerrado en el título o snippet del SERP."""

    def test_detects_es_marker_in_snippet(self):
        assert WebSearchJobsScraper._is_closed_by_snippet(
            "Full Stack Developer", "Ya no se aceptan solicitudes para esta vacante."
        )

    def test_detects_en_marker_in_snippet(self):
        assert WebSearchJobsScraper._is_closed_by_snippet(
            "Backend Engineer", "No longer accepting applications."
        )

    def test_detects_marker_in_title(self):
        assert WebSearchJobsScraper._is_closed_by_snippet(
            "Vacante cerrada — Software Architect", ""
        )

    def test_open_offer_passes(self):
        assert not WebSearchJobsScraper._is_closed_by_snippet(
            "Senior Full Stack Developer at Acme",
            "Acme Corp · Bogotá · Hace 2 días",
        )

    def test_closed_offer_is_dropped_in_search_flow(self):
        """E2E: una oferta de DDG con marker de cerrado en su snippet
        no debe llegar al output del scraper."""
        html = """
        <html><body>
          <div class="result">
            <h2><a class="result__a" href="https://www.linkedin.com/jobs/view/dead">
              Dead Job
            </a></h2>
            <a class="result__snippet">Ya no se aceptan solicitudes.</a>
          </div>
          <div class="result">
            <h2><a class="result__a" href="https://www.elempleo.com/co/ofertas-trabajo/alive/87654321">
              Alive Job
            </a></h2>
            <a class="result__snippet">Acme · Bogotá · Empleo activo.</a>
          </div>
        </body></html>
        """
        scraper = WebSearchJobsScraper()
        # _filter_closed_linkedin no debe hacer requests reales acá.
        with (
            patch("requests.post", return_value=_fake_response(html)),
            patch.object(scraper, "_is_linkedin_offer_closed", return_value=False),
        ):
            offers = scraper.search("Developer", "Bogotá")

        urls = [o.url for o in offers]
        assert "https://www.elempleo.com/co/ofertas-trabajo/alive/87654321" in urls
        assert all("/dead" not in u for u in urls)


@pytest.mark.unit
class TestLinkedInActiveProbe:
    """Probe activo: GET a LinkedIn URLs y descartar las que sirven el
    banner de cerrado. Crítico: ante errores de red, mantener la oferta."""

    def test_detects_closed_marker_in_linkedin_body(self):
        body = "<html>...No longer accepting applications...</html>"
        with patch("requests.get", return_value=_fake_response(body)):
            assert (
                WebSearchJobsScraper._is_linkedin_offer_closed(
                    "https://www.linkedin.com/jobs/view/123"
                )
                is True
            )

    def test_open_offer_returns_false(self):
        body = "<html>Apply now! Active job.</html>"
        with patch("requests.get", return_value=_fake_response(body)):
            assert (
                WebSearchJobsScraper._is_linkedin_offer_closed(
                    "https://www.linkedin.com/jobs/view/123"
                )
                is False
            )

    def test_network_error_returns_false(self):
        """Ante red caída, mantenemos la oferta (no penalizar por error)."""
        with patch(
            "requests.get",
            side_effect=requests.RequestException("connection reset"),
        ):
            assert (
                WebSearchJobsScraper._is_linkedin_offer_closed(
                    "https://www.linkedin.com/jobs/view/123"
                )
                is False
            )

    def test_http_4xx_returns_false(self):
        with patch("requests.get", return_value=_fake_response("", status_code=429)):
            assert (
                WebSearchJobsScraper._is_linkedin_offer_closed(
                    "https://www.linkedin.com/jobs/view/123"
                )
                is False
            )

    def test_filter_only_touches_linkedin_urls(self):
        """Las URLs que NO son de LinkedIn pasan intactas sin probe."""
        scraper = WebSearchJobsScraper()
        from jobs.adapters.scrapers.base import JobOfferData

        offers = [
            JobOfferData(
                title="x",
                company="x",
                location="x",
                summary="x",
                keywords="",
                url="https://www.elempleo.com/oferta/1",
                portal="websearch",
            ),
            JobOfferData(
                title="x",
                company="x",
                location="x",
                summary="x",
                keywords="",
                url="https://www.bumeran.com.co/empleo/2",
                portal="websearch",
            ),
        ]
        # Si tocara LinkedIn, esta llamada haría I/O — patch defensivo
        with patch.object(
            scraper, "_is_linkedin_offer_closed", side_effect=AssertionError("no debe llamarse")
        ):
            result = scraper._filter_closed_linkedin(offers)
        assert len(result) == 2

    def test_filter_drops_only_closed_linkedin_offers(self):
        scraper = WebSearchJobsScraper()
        from jobs.adapters.scrapers.base import JobOfferData

        offers = [
            JobOfferData(
                title="alive",
                company="x",
                location="x",
                summary="x",
                keywords="",
                url="https://www.linkedin.com/jobs/view/alive",
                portal="websearch",
            ),
            JobOfferData(
                title="dead",
                company="x",
                location="x",
                summary="x",
                keywords="",
                url="https://www.linkedin.com/jobs/view/dead",
                portal="websearch",
            ),
        ]
        # Devuelve True solo para la dead
        def fake_probe(url):
            return "dead" in url

        with patch.object(scraper, "_is_linkedin_offer_closed", side_effect=fake_probe):
            result = scraper._filter_closed_linkedin(offers)
        urls = [o.url for o in result]
        assert "https://www.linkedin.com/jobs/view/alive" in urls
        assert all("/dead" not in u for u in urls)


@pytest.mark.unit
class TestInferLocation:
    def test_skips_company_takes_second_chunk(self):
        result = WebSearchJobsScraper._infer_location(
            "Acme · Bogotá, Colombia · Hace 2 días"
        )
        assert result == "Bogotá, Colombia"

    def test_skips_date_chunks(self):
        assert WebSearchJobsScraper._infer_location("Empresa · Hace 3 días") == ""

    def test_empty_snippet_returns_empty(self):
        assert WebSearchJobsScraper._infer_location("") == ""


@pytest.mark.unit
class TestIsIndividualOfferUrl:
    """El filtro que descarta listings (search pages) de los SERPs.

    Bug histórico: ofertas que en realidad son páginas de resultados
    se guardaban como JobOffer y el user clickeaba y caía a una lista.
    Caso reportado: elempleo URLs como /co/ofertas-empleo/<ciudad>/...
    sin ID al final eran listings, no ofertas.
    """

    # LinkedIn
    def test_linkedin_view_is_individual(self):
        assert _is_individual_offer_url("https://www.linkedin.com/jobs/view/12345")

    def test_linkedin_search_is_listing(self):
        assert not _is_individual_offer_url(
            "https://www.linkedin.com/jobs/search?keywords=python"
        )

    # Computrabajo
    def test_computrabajo_oferta_is_individual(self):
        assert _is_individual_offer_url(
            "https://co.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-developer-abc123"
        )

    def test_computrabajo_search_is_listing(self):
        assert not _is_individual_offer_url(
            "https://co.computrabajo.com/ofertas-de-trabajo/?q=python"
        )

    # Indeed
    def test_indeed_viewjob_is_individual(self):
        assert _is_individual_offer_url("https://co.indeed.com/viewjob?jk=abc123")

    def test_indeed_search_is_listing(self):
        assert not _is_individual_offer_url("https://co.indeed.com/jobs?q=python")

    # Elempleo — el caso que motivó el filtro nuevo.
    def test_elempleo_old_format_is_individual(self):
        """URL viejo formato singular 'ofertas-trabajo'."""
        assert _is_individual_offer_url(
            "https://www.elempleo.com/co/ofertas-trabajo/desarrollador-fullstack/12345678"
        )

    def test_elempleo_new_format_with_id_is_individual(self):
        """URL nuevo formato — termina con ID numérico largo."""
        assert _is_individual_offer_url(
            "https://www.elempleo.com/co/ofertas-empleo/medellin/trabajo-fullstack-developer-162646464613"
        )

    def test_elempleo_search_with_category_is_listing(self):
        """Sufijo -area-X = listing por categoría, no oferta individual."""
        assert not _is_individual_offer_url(
            "https://www.elempleo.com/co/ofertas-empleo/medellin/trabajo-fullstack-developer-area-sistemas-tecnologia"
        )

    def test_elempleo_paginated_search_is_listing(self):
        """Sufijo /N = paginación, no oferta individual."""
        assert not _is_individual_offer_url(
            "https://www.elempleo.com/co/ofertas-empleo/medellin/trabajo-fullstack-developer/3"
        )

    def test_elempleo_root_search_is_listing(self):
        assert not _is_individual_offer_url(
            "https://www.elempleo.com/co/ofertas-empleo/medellin/trabajo-fullstack-developer"
        )

    def test_elempleo_short_id_is_listing(self):
        """IDs cortos (<8 dígitos) no son confiables como individuales —
        podrían ser sufijos numéricos de slug. Conservamos margen."""
        assert not _is_individual_offer_url(
            "https://www.elempleo.com/co/ofertas-empleo/medellin/trabajo-fullstack-1234"
        )

    # Resto (bumeran, magneto, getonbrd) — fallback laxo
    def test_unknown_portal_passes_through(self):
        """Para portales sin patrón auditado aceptamos cualquier URL
        del dominio (mejor falso positivo que perder ofertas reales)."""
        assert _is_individual_offer_url("https://www.bumeran.com.co/cualquier-path")
        assert _is_individual_offer_url("https://www.magneto365.com/empleos/foo")

    # Portales creativos (Tier 1.5) — Domestika, Behance, Workana, Dribbble.
    def test_domestika_detail_is_individual(self):
        assert _is_individual_offer_url(
            "https://www.domestika.org/es/jobs/12345-motion-designer"
        )

    def test_domestika_root_listing_is_not_individual(self):
        assert not _is_individual_offer_url("https://www.domestika.org/es/jobs")

    def test_behance_detail_is_individual(self):
        assert _is_individual_offer_url(
            "https://www.behance.net/joblist/12345/Senior-Designer"
        )

    def test_behance_root_listing_is_not_individual(self):
        assert not _is_individual_offer_url("https://www.behance.net/joblist")

    def test_workana_detail_is_individual(self):
        """Workana usa singular `/job/` para detail y plural `/jobs` para listing."""
        assert _is_individual_offer_url(
            "https://www.workana.com/job/diseno-de-logo-empresa-12345"
        )

    def test_workana_listing_is_not_individual(self):
        assert not _is_individual_offer_url("https://www.workana.com/jobs?category=design")

    def test_dribbble_detail_is_individual(self):
        assert _is_individual_offer_url(
            "https://dribbble.com/jobs/123456-senior-product-designer"
        )

    def test_dribbble_root_listing_is_not_individual(self):
        assert not _is_individual_offer_url("https://dribbble.com/jobs")

    def test_freelancer_project_is_individual(self):
        """Freelancer usa /projects/<slug>/ para detail page."""
        assert _is_individual_offer_url(
            "https://www.freelancer.com/projects/graphic-design/logo-design-12345"
        )

    def test_freelancer_jobs_root_is_not_individual(self):
        """`/jobs` es el listing de Freelancer, no una oferta puntual."""
        assert not _is_individual_offer_url(
            "https://www.freelancer.com/jobs/graphic-design/"
        )
