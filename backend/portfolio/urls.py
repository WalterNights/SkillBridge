"""URLconf de la app portfolio.

Todos los endpoints cuelgan de `/api/portfolio/` (montado en core/urls.py).
"""

from django.urls import path

from portfolio.views import (
    PortfolioAdminView,
    PortfolioGithubContributionsView,
    PortfolioImageDeleteView,
    PortfolioImageListCreateView,
    PortfolioPublicView,
)

urlpatterns = [
    path("<slug:slug>/", PortfolioPublicView.as_view(), name="portfolio-public"),
    path("<slug:slug>/admin/", PortfolioAdminView.as_view(), name="portfolio-admin"),
    path(
        "<slug:slug>/images/",
        PortfolioImageListCreateView.as_view(),
        name="portfolio-images",
    ),
    path(
        "<slug:slug>/images/<int:pk>/",
        PortfolioImageDeleteView.as_view(),
        name="portfolio-image-detail",
    ),
    path(
        "<slug:slug>/github-contributions/",
        PortfolioGithubContributionsView.as_view(),
        name="portfolio-github-contributions",
    ),
]
