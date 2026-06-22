# Project context

_Last updated: 2026-06-22 by Walter — cerramos sesión post-redesign + SEO, próximo paso es atacar el feature backlog._

## Current focus

Acabamos de cerrar la fase de redesign del frontend (auth, dashboard, /me, /cv, settings, job-detail) y dejamos production-ready desde SEO. El próximo bloque es el feature backlog: notificaciones reales (backend Notification model + drawer cableado), resize de fotos en backend, cron diario de scrape, email digest, y la sección de comentarios.

## State of the tree

- **Branch**: `main`
- **Last commit**: `3cca0680` — feat(seo): meta tags, robots, sitemap + brand icon polish
- **Uncommitted**: `docs/seo-submission.md` (untracked, recién creado, listo para sumar al próximo commit cuando empieces tareas operativas)
- **Open PRs**: N/A (workflow es commit directo a main)

## Recent work (últimas sesiones)

- **Redesign frontend completo (Aurora design language)**: AppShell wireado como parent de rutas autenticadas, landing nuevo, auth screens (login/register), /me LinkedIn-style con cropper de avatar + banner, /cv ATS, /settings, job detail, dashboard feed.
- **Custom photo cropper** (sin librería externa) en `shared/photo-cropper/` — ngx-image-cropper instalada pero no usada (invierte el UX pattern); puede sacarse en un cleanup.
- **Backend matching combinado** título 60% + skills 40%, con fallback título-solo cap a 70% cuando el job no enumera stack. Threshold 25%.
- **WebSearchJobsScraper** (DDG HTML) reemplaza a Google que bloquea no-JS. Tag `portal="websearch"` para stats. Probe activo para descartar LinkedIn jobs cerrados.
- **Profile persistence fix**: `ProfileService.create_profile/update_profile` solo persistía 3 de 15 campos (mapeaba a columnas inexistentes). View ahora delega en `UserProfileSerializer` con `partial=True`. Login completeness gate usa `all([first_name, last_name, city, phone, professional_title])` en vez de `number_id is not None`.
- **SEO**: meta tags + Open Graph + Twitter Card + JSON-LD en `index.html`, `robots.txt` y `sitemap.xml` en `public/`.

## Active decisions

- **AppShell wraps authenticated routes EXCEPTO `/profile` y `/cv`** — esos dos son standalone full-page editorial (no shell, no sidebar). `/me` sí va en shell.
- **`/profile` ≠ `/me`** — `/profile` es wizard onboarding one-shot post-registro; `/me` es la pantalla de edición continua. `/profile` redirige a `/me` si el perfil ya está completo.
- **Dark-only** — eliminamos el toggle de modo claro en `/settings`. Toda la app vive en el canvas oscuro.
- **Comentarios en frontend stub**: muro de feedback positivo en landing logged-in usa data hardcoded. Backend `Feedback` model pending (scope a definir: platform-wide vs per-job vs comunidad).
- **`backdrop-blur` evitado en parents de elementos `position: fixed`** — crea containing block que rompe drawers/modals. Topbar del shell y navbar del landing usan `bg-canvas` sólido, no `bg-canvas/80 backdrop-blur-xl`.
- **AdminGuard placeholder** rechazando todos — necesita backend role flag antes de habilitar `/admin/users` y `/admin/stats`.

## Next steps (en orden de prioridad sugerido)

1. **Notifications backend**: modelo `Notification{user, type, title, body, link, is_read, is_saved, created_at}` + endpoint `/api/notifications/` (list, mark-read, save). Cablear al `UserNavComponent` drawer reemplazando `STUB_NOTIFICATIONS`.
2. **Photo + banner resize en backend**: integrar Pillow para downscale al subir (avatar max 512×512, banner max 1280×320). Hoy se guarda raw — la foto que subió Walter pesaba 410×506, pero un usuario con un PNG 4K se va a comer storage.
3. **Cron diario de scrape**: Celery beat que recorre profiles completos, ejecuta `scrape_all_portals_with_stats`, crea notifications cuando hay matches nuevos. Celery+Redis ya están en `requirements.txt`.
4. **Email digest**: template HTML del resumen diario. Decisión pendiente del provider (ver Open questions).
5. **Comments backend**: definir scope primero (A/B/C en propuesta), después modelo + endpoints + reemplazar el stub en `home.component.ts`.
6. **Cleanup técnico**: tipado `any` en `MyProfileComponent.unwrapProfile` y `patchFormFromProfile` (definir `UserProfileDto` compartido), borrar `ngx-image-cropper` de `package.json` (no se usa).

## Open questions / blockers

- **Email provider** para notificaciones: SendGrid (caro pero confiable) / Mailgun / SMTP propio en VPS Hostinger / Postmark. Requiere decisión antes de empezar #4.
- **Scope de comentarios**: platform-wide feedback (A) vs per-job (B) vs comunidad/foro (C). Por copy actual ("Lo que dice nuestra comunidad") parece A, confirmar con Walter.
- **Backend role flag** para AdminGuard: agregar `is_admin` boolean al User model (o usar el `rol` existente, que ya tiene values `user`/`admin`).

## Pointers

- [docs/clean_code.md](docs/clean_code.md) — reglas del proyecto (no `any`, comentarios en EN — pero codebase usa ES por convención del equipo; el doc está desactualizado)
- [docs/seo-submission.md](docs/seo-submission.md) — guía paso-a-paso GSC + Bing Webmaster post-deploy
- [backend/jobs/services/matching_service.py](backend/jobs/services/matching_service.py) — scoring combinado title+skills
- [backend/jobs/adapters/scrapers/web_search.py](backend/jobs/adapters/scrapers/web_search.py) — DDG meta-scraper + LinkedIn closed probe
- [backend/users/views.py](backend/users/views.py) — `UserProfileViewSet.create` delega en serializer con partial=True; `CustomTokenObtainPairSerializer` define el gate de profile-complete
- [frontend/src/app/shell/app-shell.component.ts](frontend/src/app/shell/app-shell.component.ts) — sidebar colapsable + topbar
- [frontend/src/app/shared/user-nav/user-nav.component.ts](frontend/src/app/shared/user-nav/user-nav.component.ts) — bell + dropdown + notifications drawer (stub)
- [frontend/src/app/shared/photo-cropper/photo-cropper-dialog.component.ts](frontend/src/app/shared/photo-cropper/photo-cropper-dialog.component.ts) — cropper custom HTML/canvas
- [frontend/src/app/account/my-profile/my-profile.component.ts](frontend/src/app/account/my-profile/my-profile.component.ts) — /me LinkedIn-style
- [deploy/nginx/skiltak.com.conf](deploy/nginx/skiltak.com.conf) — config production (dominio confirmado: `skiltak.com` + `www.skiltak.com`, API en `api.skiltak.com`)
