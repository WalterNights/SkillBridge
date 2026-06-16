# Reporte de auditoría — SkilTak

> Auditoría profunda del código (backend + frontend) ejecutada en sesión de 2026-06-16. Reporte previo al refactor de la **Tarea 1 del [ROADMAP](ROADMAP.md)**. Este documento es **solo lectura** — los cambios se aplicarán en commits separados bajo el plan de migración del final.

## TL;DR

**🚨 4 bugs activos en producción** que hay que arreglar antes de cualquier refactor:

1. [backend/users/services/cv_analyzer_service.py:199](../backend/users/services/cv_analyzer_service.py#L199) — `NameError` en runtime: llama a `extract_skills()` que no está importada. La función `extract_skills_list` está además **definida dos veces** (L161 y L188), la segunda sobreescribe la primera.
2. [backend/users/utils/cv_keywords_loader.py:9-10](../backend/users/utils/cv_keywords_loader.py) — Typos que rompen el import: `encoding="uft-8"` y `line.stripe()`. Cualquier `import` revienta. Es **código muerto** que nunca se ejecutó (el sistema arranca solo porque nadie lo importa).
3. [backend/core/urls.py:12](../backend/core/urls.py#L12) — `name='tokee_refresh'` (typo) — los `reverse()` de tests/código que apunten a `token_refresh` van a fallar.
4. [backend/core/settings.py — INSTALLED_APPS](../backend/core/settings.py) — La app `dashboard` **no está registrada** pero tiene rutas activas (`/api/dashboard/`). Funciona por accidente (Django resuelve URLs por path); rompe migraciones, signals y management commands.

**🔓 Posible filtración de datos** en [backend/dashboard/views.py — dashboardUserList](../backend/dashboard/views.py) — devuelve **todos los perfiles sin paginación** y sin verificar permisos finos. Si está expuesto al frontend, es un leak de PII.

**📊 0% de cobertura de tests** — `tests.py` vacíos en todas las apps. Cualquier refactor sin red de seguridad es alto riesgo.

---

## Backend — Hallazgos por severidad

### 🔴 Críticos

| # | Archivo | Problema |
|---|---|---|
| 1 | `users/services/cv_analyzer_service.py` | `NameError` activo + función duplicada (L161 vs L188) |
| 2 | `users/utils/cv_keywords_loader.py` | Typos `uft-8` + `stripe()` lo dejan no-importable; código muerto |
| 3 | `users/utils/cv_analyzer.py` + `users/services/cv_analyzer_service.py` | **Triple duplicación** con `gemini_cv_service.py` (3 caminos para analizar un CV); bug `country=phone_code` (L43) |
| 4 | `jobs/keywords.py` + `users/utils/cv_keywords.py` + `cv_keywords_loader.py` + set inline en `nlp_service.py:89` | **4 fuentes de verdad** de skills, inconsistentes (`react.js` vs `react`); matching producirá falsos negativos garantizados |
| 5 | `jobs/utils/scraper.py` | God function: HTTP + parsing + ORM + escribe `output.html` en disco; `requests.get` sin `timeout`; `run_scraper_and_store_results` rota (falta arg `location`) |
| 6 | `core/urls.py:12` | Typo `tokee_refresh` (debe ser `token_refresh`) |
| 7 | `core/settings.py` INSTALLED_APPS | `dashboard` ausente pero tiene rutas |
| 8 | `dashboard/views.py` | Lista todos los perfiles sin paginación; potencial leak |

### 🟡 Importantes

| # | Archivo | Problema |
|---|---|---|
| 9 | `users/services/gemini_cv_service.py` | Acople directo al SDK de Gemini, sin interfaz `LLMProvider`; modelo `'gemini-2.5-flash'` (que **no existe** — la versión válida es `gemini-2.0-flash-exp` o `gemini-1.5-flash`); prompt de 60 líneas hardcoded en el código; parseo frágil `split('```json')[1]` |
| 10 | `users/services/nlp_service.py` | Carga `en_core_web_sm` (inglés) para CVs en español — el matching semántico (`doc.similarity` L136) sin vectores reales devuelve valores casi aleatorios → el `threshold=0.8` de matching nunca se cumple |
| 11 | `users/services/nlp_service.py:29` | `subprocess.run(["python", "-m", "spacy", "download", ...])` en runtime de request — descarga modelo desde código de servidor (inaceptable en producción) |
| 12 | `jobs/services/matching_service.py` | Matching exacto sin normalización (`"React.js"` ≠ `"react"`); cache key (L185) no se invalida cuando el usuario actualiza el CV (queda obsoleto 10 min); magic numbers `50`, `0.8`, `30`, `600` sin nombre ni config |
| 13 | `users/services/profile_service.py:75` | Lista hardcoded de campos del perfil → si agregás un campo en el modelo, **no se guarda** (silenciosamente pierde datos extraídos por Gemini) |

### 🟢 Menores

| # | Archivo | Problema |
|---|---|---|
| 14 | `jobs/services/job_service.py` | Wrappers triviales sobre ORM (anémico) — `JobOfferQuerySet` sería más idiomático |
| 15 | `users/utils/cv_analyzer.py:46-62` | `extract_full_name` con cascada de `if len(name_part)` — heurística frágil |
| 16 | 8 `print()` en `scraper.py` y `celery.py:24` | Logging informal en producción |
| 17 | `users/views.py — AnalyzerResumeView` | View de ~60 líneas (debería delegar a servicio) |

### App `resumes/`
Solo contiene `CV_FullStack_Walter_H_2025_V6_ESP.pdf`. **No es una app Django** — borrar el directorio y mover el PDF a `media/` o `docs/` según corresponda.

---

## Frontend — Hallazgos por severidad

### 🔴 Críticos

| # | Archivo | Problema |
|---|---|---|
| 18 | 8 componentes (`results`, `dashboard`, `job-detail`, `ats-cv`, `auth/profile`, `manual-profile`, `header-dashboard`, `sidebar`) | Inyectan `HttpClient` directamente — saltean capa de servicios |
| 19 | Todo el frontend | **0 uso de `takeUntilDestroyed()`** + 17 `.subscribe()` manuales + 0 uso de `async` pipe → leaks de memoria garantizados en SPA |
| 20 | `home.html` (504 líneas), `manual-profile.html` (436), `profile.html` (408), `register.html` (337) | Templates gigantes con Tailwind crudo repetido. La librería `shared/atoms` + `molecules` + `organisms` **existe y casi nadie la usa** |
| 21 | `shared/profile-builder/profile-builder.component.ts` | Es `@Injectable({providedIn:'root'})` pero está nombrado y ubicado como Component (288 líneas haciendo HTTP) — servicio mal etiquetado |
| 22 | Botones de icono SVG sin `aria-label` (`home`, `dashboard`, `results`) | Accesibilidad |

### 🟡 Importantes

| # | Archivo | Problema |
|---|---|---|
| 23 | 12 archivos | 25 ocurrencias de `: any` — modelos (`JobOffer`, `User`, `Profile`) existen pero no se usan consistentemente |
| 24 | `auth/auth.module.ts` + `auth-routing.module.ts` | NgModule residuales con `declarations: []` vacío — migración a standalone incompleta |
| 25 | `results.component.ts:153-159` | `alert()` nativo para errores (`ToastService` ya existe en `services/`) |
| 26 | 19 `console.log` / `console.error` | Quedaron en producción |
| 27 | Rutas `/results`, `/ats-cv`, `/dashboard` | Sin auth guard (existe `AutoGuard` aplicado solo a `/profile`) |

### 🟢 Menores

| # | Archivo | Problema |
|---|---|---|
| 28 | `auth/auto.guard.ts:11` | Clase implementando `CanActivate` — Angular 19 prefiere functional guards |
| 29 | Estado | Sin lib de state mgmt (OK por ahora — ver propuesta abajo). 3 `BehaviorSubject` ad-hoc + 1 signal aislado |

---

## Decisiones de duplicación

| Mantener | Borrar | Razón |
|---|---|---|
| `gemini_cv_service.py` (con refactor a `CVAnalyzer` interface) | `users/utils/cv_analyzer.py` (379 líneas regex) | Regex legacy, anchors hardcoded en español, duplica funcional con Gemini |
| `gemini_cv_service.py` | `users/services/cv_analyzer_service.py` (208 líneas con bugs) | Wrapper con `NameError` activo y mapping `country=phone_code` |
| `gemini_cv_service.py` | `users/utils/cv_keywords_loader.py` | Código muerto con typos no-importables |
| `nlp_service.extract_entities` + `calculate_text_similarity` (migrar a `es_core_news_md`) | `nlp_service.extract_skills_nlp` + `generate_summary` | El primero duplica Gemini; el segundo es "truncado disfrazado de resumen" |
| `backend/common/skills_taxonomy.py` (nuevo) | `jobs/keywords.py` + `users/utils/cv_keywords.py` + set inline en `nlp_service.py` | Una única fuente de verdad para skills + aliases |

**Reducción estimada**: ~900 líneas de Python eliminadas, 4 fuentes de skills consolidadas en 1.

---

## Top 5 refactors prioritarios

Ordenado por **riesgo de no hacerlo** (no por dificultad):

### 1. 🚨 Fixes inmediatos de bugs (1-2 horas, alta urgencia)
- Eliminar `cv_keywords_loader.py` (código muerto roto)
- Eliminar la segunda definición de `extract_skills_list` en `cv_analyzer_service.py` o desactivar el archivo (depende de quién lo llama)
- Fixear typo `tokee_refresh → token_refresh` en `core/urls.py:12`
- Agregar `'dashboard'` a `INSTALLED_APPS` en `settings.py`
- Agregar paginación + permisos finos a `dashboardUserList`
- Cambiar modelo Gemini hardcoded de `gemini-2.5-flash` (inexistente) a `gemini-2.0-flash-exp` y mover a `settings.py` como `GEMINI_MODEL`

### 2. Unificar taxonomía de skills (2-3 horas)
Crear `backend/common/skills_taxonomy.py` con `SKILLS`, `ALIASES`, `CATEGORIES`. Borrar las otras 3 fuentes. **Sin esto, `matching_service.calculate_match_percentage` produce % falsos y `scraper.extract_keywords` reporta skills distintas a las que el CV detecta.** Es la raíz del producto roto.

### 3. Consolidar análisis de CV detrás de interfaz `CVAnalyzer` (medio día)
Implementar el patrón descrito en [ROADMAP §2.a](ROADMAP.md):
```
CVAnalyzer (ABC)
├── GeminiCVAnalyzer    (provider IA, default)
└── LocalNLPAnalyzer    (fallback regex+nlp, para tests y degradación)
```
Borrar `cv_analyzer.py` + `cv_analyzer_service.py` + partes muertas de `nlp_service.py`.

### 4. Refactor scraper a Strategy pattern (medio día)
Implementar `BaseScraper` + `ComputrabajoScraper`. Sacar persistencia del scraper a `JobService.bulk_upsert(offers)`. Eliminar `output.html` writes y `print`. Setear `timeout=30` en `requests.get`. Esto desbloquea la [Tarea 2.b del ROADMAP](ROADMAP.md) (multi-portal).

### 5. Frontend — extraer HTTP a servicios + `takeUntilDestroyed` (1 día)
Crear `UserService`, `DashboardService`, `JobDetailService` (o expandir `JobService`). Migrar los 8 componentes con `HttpClient` directo. Agregar `takeUntilDestroyed(this.destroyRef)` a los 17 `.subscribe()` o pasar a `async` pipe. Reemplazar `alert()` por `ToastService`.

---

## Tests de regresión — antes de refactorizar

**Sin tests, cualquier refactor es ciego.** Prioridades mínimas antes de tocar código existente:

```python
# backend/jobs/tests/test_matching.py
# - calculate_match_percentage devuelve % esperado con skills exactas
# - el cache se invalida cuando cambian las skills del perfil

# backend/users/tests/test_cv_analysis.py
# - subir un CV de muestra (PDF + DOCX) y verificar campos extraídos
# - mockear Gemini con un response_schema canónico

# backend/jobs/tests/test_scraper.py
# - mockear HTML de Computrabajo (fixtures en jobs/tests/fixtures/)
# - parser devuelve estructura esperada
```

**No** se requiere cobertura alta — solo los **happy paths críticos** del producto: subida de CV → análisis → matching → resultados.

---

## Arquitectura propuesta — confirmada

Confirmamos lo del [ROADMAP §1](ROADMAP.md) tras la auditoría:

```
backend/
├── common/                      [NUEVO]
│   ├── skills_taxonomy.py       — fuente única de skills + aliases
│   ├── exceptions.py            — ScraperError, AIProviderError, etc.
│   └── logging.py               — config de logging estructurado
│
├── users/
│   ├── adapters/                [NUEVO]
│   │   ├── cv_analyzer_base.py  — interfaz CVAnalyzer
│   │   ├── gemini_analyzer.py   — GeminiCVAnalyzer
│   │   └── local_analyzer.py    — LocalNLPAnalyzer (fallback)
│   ├── services/                — casos de uso (profile_service, cv_analysis_service)
│   ├── views.py                 — thin, delega a servicios
│   └── models.py
│
├── jobs/
│   ├── adapters/                [NUEVO]
│   │   ├── scrapers/
│   │   │   ├── base.py          — JobScraper interface
│   │   │   ├── computrabajo.py
│   │   │   └── factory.py       — ScraperRegistry
│   ├── services/                — job_service, matching_service
│   ├── views.py
│   └── models.py
│
└── core/                        — settings, urls, celery, wsgi
```

**Frontend**: mantener estructura actual pero **consumir realmente** la atomic library de `shared/`. Convertir los 3 `BehaviorSubject` a `signal()` + `computed()`. Usar `resource()` (Angular 19) para reemplazar los HTTP gets manuales — esto elimina los 17 `.subscribe()` y los `isLoading`/`error` locales de un golpe.

**No** adoptamos NgRx — overhead innecesario para el estado actual (auth, sidebar, toasts).

---

## Plan de migración incremental — 6 commits

> **Sin big bang. Cada commit es deployable y reversible.**

### Commit 1: Fixes de bugs activos (sin tocar arquitectura)
- Borrar `users/utils/cv_keywords_loader.py`
- Fix `tokee_refresh` → `token_refresh`
- Add `dashboard` a `INSTALLED_APPS`
- Paginación + IsAuthenticated en `dashboardUserList`
- Update `GEMINI_MODEL` a `gemini-2.0-flash-exp` via env var
- Remover segunda definición de `extract_skills_list`
- Borrar `resumes/` como app Django (mover PDF a `docs/`)

**Riesgo**: bajo. **Tests requeridos**: smoke (curl a endpoints).

### Commit 2: Tests de regresión
- Pytest + `pytest-django` + fixtures básicas
- Tests críticos: análisis CV (mockeando Gemini), matching, scraper parser
- CI: agregar `pytest` al workflow de GitHub Actions

**Riesgo**: bajo. Solo agrega, no cambia.

### Commit 3: Taxonomía única de skills
- Crear `backend/common/skills_taxonomy.py`
- Migrar `matching_service` para usar `ALIASES`
- Borrar `cv_keywords.py`, set inline de `nlp_service`, consolidar con `jobs/keywords.py`

**Riesgo**: medio. Mitigación: tests del commit 2.

### Commit 4: Refactor CV analyzer a Adapter pattern
- Crear `users/adapters/cv_analyzer_base.py` + `gemini_analyzer.py`
- Mover lógica de `gemini_cv_service.py`
- Borrar `cv_analyzer.py` + `cv_analyzer_service.py`
- `users/services/cv_analysis_service.py` orquesta (no contiene SDK calls)

**Riesgo**: medio-alto. Mitigación: tests del commit 2 + feature flag para rollback (`USE_NEW_ANALYZER=true`).

### Commit 5: Refactor scraper a Strategy pattern
- `jobs/adapters/scrapers/base.py` + `computrabajo.py`
- `ScraperRegistry` con factory
- `JobService.bulk_upsert(offers)` separado
- Sin `output.html`, sin `print`, con timeout

**Riesgo**: medio. Mitigación: tests de parser con HTML fixtures.

### Commit 6: Frontend — HTTP a servicios + RxJS cleanup
- Crear servicios faltantes (`UserService`, `DashboardService`)
- Migrar componentes a usarlos
- `takeUntilDestroyed(this.destroyRef)` en todos los `.subscribe()`
- Reemplazar `alert()` por `ToastService`
- Renombrar `profile-builder.component.ts` → `profile-builder.service.ts`

**Riesgo**: medio. Mitigación: probar cada componente manualmente en `localhost:4200`.

### (Después, no en Tarea 1)
- Tarea 2.b: agregar InfoJobs/Magneto/Indeed scrapers (commits separados)
- Tarea 2.a: mejorar análisis con `response_schema` de Gemini
- Tarea 3: rediseño Stitch + atomic library consumption

---

## Anexo — Hallazgos no clasificados que vale la pena tener presente

- [backend/users/serializers.py — UserProfileSerializer](../backend/users/serializers.py) duplica lógica de `phone_code/phone_number` entre `create` y `update` — refactor menor pendiente.
- [backend/users/views.py — AnalyzerResumeView](../backend/users/views.py) tiene ~60 líneas con lógica de archivo en el view (debería estar en servicio).
- [backend/jobs/views.py — JobOfferViewSet.matched](../backend/jobs/views.py) crea el `matched_skills`/`missing_skills`/`match_percentage` dinámicamente en serializer — atributos no documentados.
- [backend/jobs/serializers.py — JobOfferSerializer](../backend/jobs/serializers.py) lee atributos dinámicos que no existen en el modelo → falla si los llaman en otros contextos.
- `core/celery.py:24` — `print()` en `debug_task` (cambiar a logger).
- Frontend `app.routes.ts:5-16` — lazy loading ✅ bien hecho.
- Frontend solo tiene **1 `<img>` con alt** en toda la app — confirma que el UI es muy texto-pesado (Stitch va a cambiar esto).

---

**Próximo paso**: tu confirmación del plan de migración. Si está OK, arrancamos por el **Commit 1** (fixes de bugs activos) que es bajo riesgo y arregla cosas rotas hoy.
