# Project context

_Last updated: 2026-06-24 by Walter — segunda sesión del día, foco en mejoras del CV y editor._

## Current focus

Después de cerrar el roadmap original, esta sesión se dedicó a pulir el flow del CV: extractor mejorado, "Mejorar con AI", auditor, formato Oficio con paginación, toolbar de formato Markdown-light, render de bullets/bold en /cv. También hubo trabajo en sidebar (categorías, Recursos+Blog para auth) y un bug crítico de loop en el token-refresh interceptor. **El feature de paginación del CV quedó funcionalmente OK pero perfeccionable** (ver Open questions).

## State of the tree

- **Branch**: `main`
- **Last commit**: `ab6b2563` — feat(cv): formato Oficio + paginación visual cuando supera 1 hoja
- **Uncommitted**: 5 archivos modificados (snap algorithm rewrite + markdown line breaks + bold cross-line fix) — listos para commit al cierre de sesión
- **Open PRs**: N/A (workflow es commit directo a main, GitHub Actions despliega auto)
- **Tests**: backend 272/272 passing

## Recent work (sesión 2026-06-24)

- **Extractor de CV mejorado** — el prompt de Gemini ahora preserva todos los bullets de experiencia (antes los comprimía a 2 oraciones), captura `languages` (array {language, level}) + `soft_skills` (texto comma-sep). UserProfile gana campos `soft_skills` y `languages` (migración 0010). Render en /cv tiene secciones nuevas.
- **"Mejorar mi CV con AI"** — endpoint `POST /api/users/cv/improve/` que devuelve propuesta (no persiste). Modal con before/after de summary, skills y sample de experiencia. Defensivo: si Gemini cambia el count de experiences o se inventa empresas/fechas, descartamos esas mejoras y caemos al original (no perdemos roles).
- **Auditor del CV** (entregado sesión anterior pero usado y validado acá) — botón "🧠 Auditar con AI" en /cv, modal con score 0-100 + 6 categorías + top 3 recomendaciones + botón "Aplicar mejoras con AI" que abre el improver.
- **Toolbar de formato sticky** en /me edit mode — Negrita, Cursiva, Lista, Numerada, Limpiar. `position: fixed` a la izquierda del form (sin robar ancho). En mobile cae como franja sticky-top. Solo visible en edit mode.
- **RichTextComponent** (shared) — parser Markdown-light propio (sin librerías). Soporta `**bold**`, `*italic*`, listas con `- /• /*`, listas numeradas, párrafos por línea + spacer entre bloques (blank line del input). Pre-procesa bold multi-línea para tolerar selecciones que cruzan newlines.
- **Formato Oficio (215.9×355.6mm)** en /cv — antes era A4. PDF export actualizado a `'legal'` en jsPDF.
- **Paginación visual del CV** — separadores "Página N" entre hojas Oficio. **Algoritmo actual**: snappea solo `.cv-entry` (no `.cv-section` enteras), inyecta `margin-top` para empujar entries que cruzan el boundary al inicio de la próxima hoja. Markers derivados de las posiciones reales de los snaps (no de fórmula teórica). Cache de altura natural para evitar loop en `ngAfterViewChecked`.
- **Sidebar reorganizado** — "Inicio" → "Ofertas", secciones "Trabajo" (Ofertas/Postulaciones/CV) y "Aprender" (Recursos/Blog). Recursos y Blog accesibles auth y unauth (componentes detectan `insideShell` via AuthService.isAuthenticated y skip PublicNav/PublicFooter cuando están en shell).
- **Routing con `canMatch`** — nuevo `authMatchGuard` para que `/recursos` y `/blog` se renderean dentro del shell cuando hay auth y caigan al fallback público cuando no.
- **Filtros dashboard "Cargar más"** — antes el feed mostraba solo 20 (DRF default) y daba sensación de que se reemplazaban tras cada scrape. Ahora `JobService.getJobs(filters, page)` devuelve envelope completo + frontend acumula páginas con botón "Cargar más ofertas (N restantes)".
- **Bug fix crítico — token refresh loop** — el interceptor capturaba 401 de `/token/refresh/` y disparaba otro refresh → loop infinito que martillaba el backend. Skip de refresh para URLs `/token/*` y `/register/*` y cuando no hay refresh_token guardado.
- **Bug fix — GEMINI_API_KEY no declarada** — 500 en /cv/audit/. Los nuevos services accedían via `settings.GEMINI_API_KEY` que nunca se declaró en core/settings.py (los modules viejos leían `config()` directo). Declaradas las dos vars con defaults seguros.
- **Bug fix — "Ver más recursos" en Tip widget** — apuntaba a `href="#"` → ahora `routerLink="/recursos"`. Después se quitó el link por redundante (Recursos ya está en el sidebar como item de primer nivel).
- **Categorías en sidebar** — secciones "Trabajo" + "Aprender" en vez de un solo "Menú".
- **Editor de imágenes ya subidas** — botón "Reajustar" en banner y avatar de /me. Fetch del URL público → blob → File → reusa el cropper existente.
- **Textareas resize:vertical only** — override en styles.scss para que summary/experience/education solo se redimensionen vertical, no horizontal (rompía el grid del form).

## Active decisions

- **AppShell wraps authenticated routes EXCEPTO `/profile`** — wizard de onboarding standalone full-page. `/cv` ahora SÍ está dentro del shell (cambio reciente — antes era standalone).
- **`/profile` ≠ `/me`** — wizard una vez vs edición continua. `/profile` redirige a `/me` si el perfil ya está completo.
- **Dark-only** — sin toggle de modo claro.
- **Filtros dashboard**: country ISO alpha-2 ('XX' = desconocido, excluido del dropdown). Modality enum cerrado. Multi-select OR intra-categoría, AND inter-categoría.
- **Scrapers JSON-LD-first**: si un portal tiene `JobPosting` server-rendered (Hireline, Trabajando.com), usar sitemap + JSON-LD en vez de CSS selectors.
- **BNE México y BNE Chile deferidos** — SPAs gov sin API, requieren Playwright. ROI dudoso.
- **Co-Authored-By en commits**: NO incluir.
- **CV en formato Oficio** (215.9×355.6mm = US Legal) — estándar para LATAM. PDF export con `'legal'`.
- **Paginación del CV via snap a `.cv-entry`** — NO snappear `.cv-section` (demasiado grandes, dejarían páginas casi vacías). Markers derivados de snaps reales, no de fórmula teórica.
- **Markdown light en CV/profile**: sintaxis propia (`**bold**`, `- bullet`, `1. numbered`, `*italic*`). RichTextComponent renderea con Angular templates sin `[innerHTML]` (sin riesgo de XSS). No usamos `marked` + DOMPurify para mantener cero deps.
- **Toolbar de formato wrappea por línea** cuando la selección abarca múltiples líneas. Sin esto, un solo `**...**` cruzando newlines no es detectado por el parser line-by-line.
- **Routing con `canMatch`** para rutas con fallback público (`/recursos`, `/blog`). El shell route las cubre cuando hay auth; cuando no, caen al fallback público que renderea con PublicNav.

## Open questions / blockers

- **Paginación del CV — perfectible**:
  - Si un solo `.cv-entry` es más alto que una hoja Oficio (raro pero posible con un rol con 20 bullets), se desborda sin snap. Falta una pasada que split entries demasiado grandes.
  - Orphaned section headers — el h2 "Experiencia profesional" puede quedar al final de una hoja con su primera entry en la siguiente. Para fixearlo bien habría que tratar (h2 + primer entry) como unidad indivisible.
  - El marker visual es de 14mm y se centra en el gap; con gaps muy chicos puede solaparse con contenido. Acotado a `Math.max(0, gapMid - 27)`.
- **Render Markdown en CV — limitado**:
  - No soporta links, headings inline, código, tablas, imágenes. Suficiente para CV ATS, no para blog/docs.
  - `**bold**` cross-line ya se pre-procesa, pero italic cross-line no (raro que aparezca, baja prioridad).
- **Resize de fotos en backend** — el cropper ya genera output controlado (1024px avatar / 1920px banner). Falta validación server-side para users que carguen un PNG 4K sin pasar por el cropper.
- **Comments / feedback widget** — el muro del home logged-in usa `STUB_COMMENTS` hardcoded. Scope sin decidir.

## Next steps (sin orden, esperando prioridad de Walter)

- **Mejorar paginación CV**: split de entries demasiado grandes, manejo de orphaned headers.
- **Más portales**: BNE MX/CL (deferred), OCC, Bumeran, CompuTrabajo otros países.
- **Sentry o similar** para monitoring en prod — solo tenemos logs en gunicorn/celery.
- **Test E2E del flow LinkedIn OAuth** — hay 10 unit tests pero no smoke end-to-end.
- **Limpieza técnica**: tipado `any` en `MyProfileComponent.unwrapProfile`, borrar `ngx-image-cropper` del package.json (no se usa).
- **Backfill prod de `country` + `modality`**: la migración 0007 corre auto en deploy y trae RunPython. Verificar después del próximo deploy que los conteos del endpoint `/filter-options/` no sean todos `XX`/`unknown`.

## Pointers

- [docs/clean_code.md](docs/clean_code.md) — reglas del proyecto
- [docs/seo-submission.md](docs/seo-submission.md) — GSC + Bing Webmaster
- [backend/jobs/services/matching_service.py](backend/jobs/services/matching_service.py) — scoring título 60% + skills 40%
- [backend/jobs/adapters/scrapers/registry.py](backend/jobs/adapters/scrapers/registry.py) — single source of truth de scrapers
- [backend/jobs/utils/offer_attributes.py](backend/jobs/utils/offer_attributes.py) — extractores country + modality
- [backend/users/services/cv_auditor.py](backend/users/services/cv_auditor.py) — auditor del CV
- [backend/users/services/cv_improver.py](backend/users/services/cv_improver.py) — improver del CV (defensivo: preserva counts originales)
- [backend/users/services/achievement_quantifier.py](backend/users/services/achievement_quantifier.py) — cuantificador per-bullet
- [backend/users/adapters/gemini_analyzer.py](backend/users/adapters/gemini_analyzer.py) — extractor de CV (prompt mejorado para preservar bullets + languages + soft_skills)
- [backend/applications/cover_letter_generator.py](backend/applications/cover_letter_generator.py)
- [backend/users/oauth_linkedin.py](backend/users/oauth_linkedin.py)
- [deploy/README.md](deploy/README.md) — incluye sección de cómo subir `.env` al VPS
- [frontend/src/app/shared/rich-text/rich-text.component.ts](frontend/src/app/shared/rich-text/rich-text.component.ts) — parser Markdown-light propio
- [frontend/src/app/shared/text-format-toolbar/text-format-toolbar.component.ts](frontend/src/app/shared/text-format-toolbar/text-format-toolbar.component.ts) — toolbar sticky en /me edit
- [frontend/src/app/auth/auth-match.guard.ts](frontend/src/app/auth/auth-match.guard.ts) — canMatch guard para rutas con fallback público
- [frontend/src/app/ats-cv/ats-cv.component.ts](frontend/src/app/ats-cv/ats-cv.component.ts) — viewer del CV con snap-pagination
- [frontend/src/app/shared/portal.ts](frontend/src/app/shared/portal.ts) — mapeo URL → portal para avatares
- [frontend/src/app/auth/token-interceptor.service.ts](frontend/src/app/auth/token-interceptor.service.ts) — interceptor JWT con fix anti-loop
