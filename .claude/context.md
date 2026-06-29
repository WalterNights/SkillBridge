# Project context

_Last updated: 2026-06-29 by Walter — sesión enfocada en separación de verticales + loosening del feed + setup de GitHub MCP._

## Current focus

Hacer el feed viable para CUALQUIER perfil profesional sin tunear caso por caso. El sistema ahora taggea cada `JobOffer` con una `category` macro (tech, agro, legal, health, trades, admin, etc.) y filtra el feed estricto por la categoría del user — un abogado nunca ve ofertas de diseño, un zootecnista solo ve ofertas agro/veterinarias. Cliente piloto de validación: **Fabio (cuenta `minos009`)**, zootecnista en Bogotá.

## State of the tree

- **Branch**: `main`
- **Last commit**: `7a0d42d5` — fix(feed): aflojar min_match a 0 para users con vertical claro
- **Uncommitted**: ninguno
- **Open PRs**: N/A (workflow es commit directo a main, GitHub Actions despliega auto)
- **Tests**: 676/676 passing
- **Último deploy GHA**: #128 `success` (commit 7a0d42d5, verificado en prod 2026-06-29)

## Recent work (sesiones 2026-06-27 / 28 / 29)

- **Separación de verticales** (commit 56cfccb1) — `JobOffer.category` (migración 0013), `JobService.save_new_offers` infiere category al guardar via `infer_profession_category(title + summary)`. Feed filtra `category=user_category`. Cliente Fabio pasó de "ver de todo" a ver solo agro.
- **Filtro estricto sin 'general' como comodín** (a9d3a27d) — eliminado el fallback que incluía `category='general'` para users con vertical. Reportado por el cliente: "NADA que no tenga que ver con la profesión del usuario".
- **Classifier robusto a plurales + pet care en agro** (15fadbb6) — helper `_word_with_plurals` agrega plurales españoles automáticamente al regex; categoría `agro` incluye veterinaria, zootecnia, pet care (peluquero canino, estilista canina, paseador de perros). Migración 0014 re-taggea TODAS las ofertas viejas con el classifier corregido.
- **Limpieza de city para URLs de portales** (87582122) — helper `clean_city_for_slug` trunca al primer sufijo administrativo ("Bogotá D.C." → "Bogotá"). Sin esto, Computrabajo devolvía página 200 OK con 0 ofertas porque el slug quedaba mal armado.
- **Loosening de min_match para vertical claro** (7a0d42d5, ESTA sesión) — para users con `user_category != 'general'`, el threshold default se afloja a 0 (el filtro por categoría ya garantiza relevancia, match% solo ordena). Verificado en prod con Fabio: default pasó de **2 → 10 ofertas**. Si user pide `?min_match=80` explícito, se respeta.
- **GitHub MCP global setup** (ESTA sesión) — binary `github-mcp-server v1.5.0` en `~/.claude/bin/`, wrapper `.cmd` lee `GITHUB_MCP` de `.env` del proyecto al lanzar, toolsets `default,actions`. PAT vive **solo** en `<project>/.env`, nunca en `.claude.json`. Permite consultar workflow runs / jobs / logs desde Claude sessions.
- **Rate limit del scrape 5→10→20/h** (946e05e9 + 1710a3f7) — escalable después de sacar Gemini del path crítico.
- **Gemini fuera del PortalRouter** (708484bd) — el `PortalRouterService` ahora usa `infer_profession_category` + `scraper.categories` determinístico, sin AI en el path crítico. Quita costo + dependencia externa.
- **Checkbox "Ver matches débiles" como modo DIAGNOSTICO** (63bac7e1 + eb8b1183) — gated por feature flag `show_low_match_filter`. Default 50%, checkbox extiende a 0-49% (diagnostic). Después del loosening de 7a0d42d5, en users con vertical el checkbox es semánticamente redundante (todas las same-vertical ya muestran en default) — el feature flag sigue siendo útil para users `general`.

## Active decisions

- **Vertical filter es la puerta principal de relevancia**, no el match%. Si el offer es de la categoría del user, debe verse — match% sirve para ordenar dentro. Esto cambia la semántica histórica donde min_match=50 era el filtro principal.
- **Gemini fuera del path crítico del scrape**. Router determinístico via classifier + scraper categories. Razón: costo + dependency externa + observabilidad.
- **PAT del GitHub MCP en `.env` del proyecto, nunca en `.claude.json`**. Un wrapper `.cmd` los junta al lanzar. Rotación: editar `.env` y reload de VSCode.
- **Co-Authored-By en commits**: NO incluir.
- **CV en formato Oficio** (215.9×355.6mm = US Legal) — estándar LATAM.
- **AppShell wraps authenticated routes EXCEPTO `/profile`** — wizard standalone. `/cv` está dentro del shell.
- **Dark-only** — sin toggle modo claro.
- **Scrapers JSON-LD-first** cuando el portal sirve `JobPosting` server-rendered.
- **BNE México y Chile deferidos** — SPAs gov sin API, ROI dudoso.

## Open questions / blockers

- **Falso positivo del classifier** — "Tecnico auxiliar de cocina" tageado como `agro` en producción (aparece en el feed de Fabio). Probable: alguna keyword del summary matcheando una palabra agro. Pending: inspeccionar la oferta puntual + ajustar el regex de agro para no matchear esos casos.
- **Scrapers con bajo recall** — Magneto/Indeed/Trabajos_co/WebSearch volviendo 0 en últimos runs. Sospechas: Playwright issues o ban por IP. LinkedIn recall ~11 vs ~36 manual (personalización por IP del guest API).
- **Trabajando sitemap-based desperdicia cuota** — el sitemap recorre todas las ofertas; para users de vertical específico hace mucho parseo inútil.
- **Verificar disponibilidad de ofertas en portal origen** (backlog viejo, no resuelto) — caso reportado: ofertas con 85% match cuyas URLs devuelven "oferta no disponible". Implementar probe asíncrono que marque `is_active=False` cuando 404.

## Backlog UI/UX (no resuelto desde 2026-06-24)

1. **Bug visual /settings dropdown idioma** — `<select>` native con fondo claro y options casi invisibles. Fix de contraste o reemplazar por custom dropdown.
2. **Badge "1" quemado en /applications tab "Todas"** — estilo del badge no respeta los otros tabs. Quick fix de CSS.
3. **Paginación CV perfectible** — entries más grandes que una hoja Oficio no se splittean, orphaned h2 al final de página.

## Next steps

1. Investigar el falso positivo "Tecnico auxiliar de cocina" → agro (classifier fix puntual).
2. Diagnosticar por qué Magneto/Indeed/Trabajos_co/WebSearch vuelven 0 — empezar por logs del último scrape para ver si es timeout, ban o cambio de HTML.
3. Subir el probe de disponibilidad de ofertas (backlog viejo) — patron de LinkedIn closed probe en `web_search.py` es buen punto de partida.

## Pointers

- [backend/jobs/views.py](backend/jobs/views.py) — `JobOfferViewSet.get_queryset` (filtro estricto) + `list` (loosening same-vertical)
- [backend/jobs/services/job_service.py](backend/jobs/services/job_service.py) — `save_new_offers` calcula category al guardar
- [backend/jobs/services/matching_service.py](backend/jobs/services/matching_service.py) — scoring título 60% + skills 40%, `_extract_primary_role`
- [backend/jobs/adapters/scrapers/base.py](backend/jobs/adapters/scrapers/base.py) — `clean_city_for_slug` + `extract_age_days` + `JobScraper.categories`
- [backend/jobs/adapters/scrapers/registry.py](backend/jobs/adapters/scrapers/registry.py) — single source of truth de scrapers
- [backend/jobs/services/portal_router.py](backend/jobs/services/portal_router.py) — router determinístico (sin Gemini en critical path)
- [backend/jobs/migrations/0013_joboffer_category.py](backend/jobs/migrations/0013_joboffer_category.py) — agrega `category` + backfill
- [backend/jobs/migrations/0014_retag_categories_after_plurals_fix.py](backend/jobs/migrations/0014_retag_categories_after_plurals_fix.py) — re-taggea todas las ofertas con classifier corregido
- [backend/users/services/profession_classifier.py](backend/users/services/profession_classifier.py) — `_word_with_plurals`, categorías macro (tech, design, marketing, agro, health, legal, admin, trades, etc.)
- [backend/jobs/tests/test_jobs_api.py](backend/jobs/tests/test_jobs_api.py) — tests del feed incluyen separación de verticales + loosening
- [docs/clean_code.md](docs/clean_code.md) — reglas del proyecto
- [deploy/README.md](deploy/README.md) — incluye sección de cómo subir `.env` al VPS
- `~/.claude/bin/github-mcp-wrapper.cmd` — wrapper que lee `GITHUB_MCP` de `.env` para el MCP de GitHub
- `~/.claude/projects/d--WalterNights-software-projects-SkillBridge/memory/reference_skiltak_ci.md` — pattern de uso del GitHub MCP (paginar runs, traer logs)
