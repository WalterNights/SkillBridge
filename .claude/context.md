# Project context

_Last updated: 2026-06-24 by Walter — roadmap principal entregado, abierto a próximas prioridades._

## Current focus

Cerramos un sprint largo entregando los 10 items del backlog + bugs y mejoras reportadas en vivo. El producto tiene tracking de postulaciones con estados, alertas por email, LinkedIn sign-in, generador de cartas de presentación con AI, cuantificador de logros del CV, auditor estructural del CV, filtros por país y modalidad en el dashboard, 6 scrapers en producción (Computrabajo, LinkedIn, Indeed, Magneto, Hireline, Trabajos Colombia, Trabajando.com), páginas legales reales y footer rediseñado. **Lo que sigue lo decide Walter** — el backlog original está agotado.

## State of the tree

- **Branch**: `main`
- **Last commit**: `9f0c3518` — feat(scrape): Trabajando.com (Chile + Colombia)
- **Uncommitted**: limpio
- **Open PRs**: N/A (workflow es commit directo a main, GitHub Actions despliega auto)
- **Tests**: backend 272/272 passing

## Recent work (sprint del 2026-06-23/24)

- **#1 Tracking de postulaciones con estados** (7 estados: pending, applied, in_review, interview, offer, rejected, withdrawn). Vista `/applications` con tabs + dropdown de cambio de estado + notas libres.
- **#2 Alertas por correo** — Celery beat task diaria 12:00 UTC, digest HTML con matches >85%, anti-dedup 20h. Toggle en `/settings`.
- **#3 LinkedIn sign-in** (OAuth 2.0 / OpenID Connect) — botón en login + register, `linkedin_user_id` para idempotencia, redirect via `/auth/linkedin/complete`.
- **#4 Cartas de presentación con Gemini** — modal en `/jobs/:id` y `/applications`, tono (formal/cercano/directo) + idioma (ES/EN), guardada por (user, offer), copiar/descargar.
- **#5a Hireline (MX + CO)** — sitemap + JSON-LD JobPosting.
- **#5d Trabajando.com (CL + CO)** — misma arquitectura.
- **#6 Cuantifica logros en /cv** — botón "✨ Cuantificar" por entry de experiencia, 3 variantes con números/métricas, optimistic update + PATCH.
- **#7 Auditor estructural del CV** — botón "🧠 Auditar con AI" en `/cv`, modal con score 0-100 + 6 categorías con severity + top 3 recomendaciones.
- **#8 Footer rediseñado** — nueva columna "Cuenta" (Login/Register/Contacto), legal links como tertiary en bottom row.
- **#9 trabajos.com Colombia** — scraper requests + BS4.
- **#10 Filtros dashboard por país + modalidad** — extractores heurísticos `extract_country` (ISO) + `extract_modality` (remote/hybrid/onsite/unknown), backfill en migración, panel de chips multi-select con conteos.
- **Páginas legales reales** (`/legal/{privacidad,terminos,cookies}`) — necesarias para registrar la app de LinkedIn Developers y porque los links del footer estaban con `href="#"`. Contenido adaptado a Ley 1581/2012 Colombia + GDPR.
- **Bug fix crítico**: loop infinito en el token refresh interceptor — cuando el refresh-token expiraba, cada 401 disparaba otro refresh que también daba 401. Skip de la lógica de refresh para URLs `/token/*` y `/register/*` y cuando no hay refresh-token guardado.
- **Bug fix**: "Ver más recursos" del widget Tip del día apuntaba a `href="#"` (caía en home) — ahora `routerLink="/recursos"`.
- **Feature extra**: reajustar zoom/encuadre de avatar y banner ya subidos sin re-subir el archivo (fetch del URL público → blob → reusa el cropper).
- **Diagnostic logging** en LinkedIn callback cuando llegan params inesperados (sirve para debug en prod sin pedir screenshots).

## Active decisions

- **AppShell wraps authenticated routes EXCEPTO `/profile` y `/cv`** — esos dos son standalone full-page editorial. `/me` sí va en shell.
- **`/profile` ≠ `/me`** — `/profile` es wizard onboarding one-shot; `/me` es edición continua.
- **Dark-only** — sin toggle de modo claro.
- **AdminGuard placeholder** rechaza todos — usa `user.rol` (ya existe), habilitar cuando se necesite.
- **Filtros dashboard**: country como ISO alpha-2 ('XX' para desconocido, excluido del dropdown). Modality como enum cerrado. Multi-select con OR intra-categoría, AND inter-categoría.
- **Scrapers JSON-LD-first**: cuando un portal tiene JSON-LD `JobPosting` server-rendered (Hireline, Trabajando.com), preferir parsearlo en vez de CSS selectors — más estable a redeploys del frontend del portal.
- **BNE México y BNE Chile deferidos** — ambos son SPAs gubernamentales sin API obvia, requieren Playwright + reverse engineering (~3-4h cada uno) y ROI dudoso (ofertas gov de baja calidad, poco actualizadas). Reabrir si los users explícitamente piden ofertas gov.
- **Co-Authored-By en commits**: NO incluir (preferencia del usuario).

## Next steps (sin orden, esperando prioridad de Walter)

- **Sumar más portales** si vienen pedidos: BNE MX/CL (deferred), OCC, Bumeran (scraper estaba implementado pero deshabilitado del registry), CompuTrabajo otros países.
- **Sentry o similar para monitoring** de errores en prod — hoy solo tenemos logs en gunicorn/celery.
- **Test E2E del flujo de login con LinkedIn** — el OAuth flow tiene 10 unit tests pero no hay smoke test que valide el flow end-to-end.
- **Limpieza técnica diferida**: tipado `any` en `MyProfileComponent.unwrapProfile` y `patchFormFromProfile`; borrar `ngx-image-cropper` del `package.json` (no se usa, el cropper actual es custom).
- **Backfill de `country` y `modality` en prod** — la migración 0007 corre auto en el deploy y trae el RunPython, así que ya está cubierto, pero verificar después del próximo deploy que los conteos del endpoint `/filter-options/` no sean todos `XX`/`unknown`.

## Open questions / blockers

- **Resize de fotos en backend** — la subida actual del cropper ya genera output controlado (1024px avatar / 1920px banner), pero no hay validación server-side. Walter subió fotos chicas, pero un user con PNG 4K (sin pasar por el cropper) podría comer storage.
- **Comments / feedback widget** — el muro del home logged-in usa data hardcoded (`STUB_COMMENTS`). Scope sin decidir (platform-wide vs per-job vs comunidad).

## Pointers

- [docs/clean_code.md](docs/clean_code.md) — reglas del proyecto (codebase usa ES, doc desactualizado en eso)
- [docs/seo-submission.md](docs/seo-submission.md) — guía paso-a-paso GSC + Bing Webmaster
- [backend/jobs/services/matching_service.py](backend/jobs/services/matching_service.py) — scoring título 60% + skills 40%
- [backend/jobs/adapters/scrapers/registry.py](backend/jobs/adapters/scrapers/registry.py) — single source of truth de scrapers activos
- [backend/jobs/utils/offer_attributes.py](backend/jobs/utils/offer_attributes.py) — extractores country + modality, único punto de modificación
- [backend/users/services/cv_auditor.py](backend/users/services/cv_auditor.py) y [achievement_quantifier.py](backend/users/services/achievement_quantifier.py) — features AI del CV
- [backend/applications/cover_letter_generator.py](backend/applications/cover_letter_generator.py) — generador de cartas
- [backend/users/oauth_linkedin.py](backend/users/oauth_linkedin.py) — flow OAuth con state CSRF en cache
- [deploy/README.md](deploy/README.md) — incluye sección sobre cómo subir nuevas variables del `.env` al VPS (scp + restart, no se inyectan en el deploy automático)
- [frontend/src/app/shared/portal.ts](frontend/src/app/shared/portal.ts) — mapeo URL → portal para avatares del feed
- [frontend/src/app/auth/token-interceptor.service.ts](frontend/src/app/auth/token-interceptor.service.ts) — interceptor JWT con fix anti-loop de refresh
