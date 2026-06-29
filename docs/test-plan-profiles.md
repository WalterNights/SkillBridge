# Test Plan — Cobertura de Profesiones

Validación end-to-end de la plataforma SkilTak con perfiles representativos
de cada categoría profesional macro que soporta el clasificador. Objetivo:
verificar que un usuario de cualquier vertical encuentra ofertas relevantes
y NO ve ruido cross-vertical (promesa "cero ruido").

## Setup

| Componente | URL local | Datos |
|---|---|---|
| Backend (Django + DRF) | http://localhost:8000 | SQLite con dump de prod (586 ofertas reales) |
| Frontend (Angular) | http://localhost:4200 | apuntando a localhost:8000 |
| Chrome MCP | controlado por agente | navega + screenshot |

### Distribución de ofertas en la DB local

| Categoría | Cantidad |
|---|---:|
| general | 303 |
| tech | 114 |
| sales | 58 |
| design | 50 |
| trades | 16 |
| agro | 10 |
| admin | 9 |
| operations | 8 |
| hr | 6 |
| health | 5 |
| education | 3 |
| marketing | 3 |
| finance | 1 |
| **legal** | **0** ← gap del catálogo prod |

Implicación: perfiles `legal` no van a ver ofertas relevantes en este snapshot.
Es un gap del catálogo real, no del código. Sirve para validar el caso de
"feed vacío + mensaje correcto al usuario".

## Metodología por perfil

Para cada perfil de la tabla:

1. **Registro** vía `/auth/register` con email único `test+<slug>@skiltak.local`.
2. **Completar onboarding wizard** (`/profile`) con título profesional + ciudad
   + skills + experiencia mínima.
3. **Navegar al dashboard** y observar:
   - Cantidad de ofertas mostradas en default (sin checkbox de débiles)
   - Distribución de match% (cuántas al 90%, 70-90%, 50-70%, etc.)
   - **Categoría única**: que TODAS las ofertas listadas pertenezcan al
     mismo vertical del usuario (no cross-vertical leak)
   - Falsos positivos potenciales (ofertas que no deberían estar)
4. **Screenshot** del feed por perfil.
5. **Anotar resultado** en la tabla de resultados al final del archivo.

## Perfiles de test

**Ya validados en prod previamente** (excluidos de este round):
- **tech** — perfil de Walter (developer)
- **design** — Jorge (UI/UX Designer multi-rol)
- **agro** — Fabio / minos009 (Zootecnista — Peluquero canino)

Este test plan cubre los **9 verticales restantes**: marketing, sales, finance,
hr, operations, health, legal, admin, trades.

> Convención de email: `test+<slug>@skiltak.local`
> Convención de password: `TestPass2026!` (compartida — local only)

| # | Slug | Título profesional | Categoría esperada | Skills | Notas |
|---|---|---|---|---|---|
| 1 | marketing | Community Manager Senior | marketing | seo, content marketing, instagram, ads | Solo 3 ofertas en DB |
| 2 | sales | Asesor Comercial B2B | sales | crm, hubspot, salesforce, negociación | Vertical con buen volumen (58) |
| 3 | finance | Contadora Pública con Especialización Tributaria | finance | siigo, sap, normatividad fiscal, niif | Solo 1 oferta — caso "casi vacío" |
| 4 | hr | Reclutadora Tech / Talent Acquisition | hr | linkedin recruiter, sourcing, ats, entrevistas | 6 ofertas |
| 5 | operations | Jefe de Producción Industrial | operations | lean, six sigma, scm, sap | 8 ofertas |
| 6 | health-pediatra | Médico Pediatra | health | pediatría, vacunación, urgencias pediátricas | 5 ofertas |
| 7 | health-enfermera | Enfermera Profesional | health | uci, urgencias, primeros auxilios | Subset health |
| 8 | legal | Abogada Penalista | legal | derecho penal, litigio, audiencias | **0 ofertas en DB** — feed vacío esperado |
| 9 | admin | Asistente Administrativa | admin | excel, contabilidad básica, archivística | 9 ofertas |
| 10 | trades | Plomero con experiencia | trades | gasodomésticos, instalaciones hidráulicas, mantenimiento | 16 ofertas |

## Criterios de aceptación

Por cada perfil, el feed debe cumplir:

| Criterio | Bueno | Aceptable | Falla |
|---|---|---|---|
| **Match% del top** | ≥ 70% | 50-69% | < 50% |
| **Cross-vertical leak** | 0 ofertas de otra categoría | 0 (siempre debe ser 0) | ≥1 oferta off-topic |
| **Distribución** | ≥3 ofertas a 90%, resto same-vertical | 1-2 ofertas a 90%, resto same-vertical | sin 90% |
| **Tiempo de carga** | < 1.5s | 1.5-3s | > 3s |
| **Empty state** (si feed vacío) | mensaje claro + CTA | mensaje genérico | error o blank |

## Resultados (a llenar durante ejecución)

| # | Slug | Categoría inferida | Total ofertas | Top match% | Distribución | Falsos positivos | Notas |
|---|---|---|---:|---:|---|---|---|
| 1 | marketing | marketing ✓ | 3/3 | 50% | 3×50% | 0 | Floor del boost dispara correcto, sin overlap directo título |
| 2 | sales | sales ✓ | 61 (paginado 20/61) | 90% | 4×90% + 4×70% + 16×50-69% | 0 | "Asesor Comercial B2B" matchea exacto en title de 4 ofertas |
| 3 | finance | finance ✓ | 1/1 | 50% | 1×50% (Auditor Interno) | 0 | Edge case "casi vacío" — la única oferta finance del DB aparece correctamente |
| 4 | hr | hr ✓ pero con FP | 7 | 50% | 7×50% | **5 (71%)** | 🔴 Bug: "Hrs"/"HRS" (abreviatura de horas) matchea como plural de "hr" → retail/operario tageadas como HR. Fix: excluir plural en palabras ≤2 chars |
| 5 | operations | operations ✓ | 12 | 67% | 1×67% + 11×50% | 0 | "Jefe de producción" matchea parcialmente título user. Resto al floor 50% |
| 6 | health-pediatra | health ✓ | 8 | 50% | 8×50% | 0 | No hay ofertas de pediatra en DB pero el filter agrupa salud humana correctamente (vets→agro NO aparecen aquí) |
| 7 | health-enfermera | health ✓ | 58 (paginado) | 90% | 1×90% + resto 50% | 0 | Top: "Enfermera profesional / Bogotá". Race condition UI: dashboard mostró 0/0 inicial, refresh OK |
| 8 | legal | legal ✓ | 0 | N/A | empty | 0 | Edge case "vacío" — UI muestra "Aún no encontramos ofertas para tu perfil" + CTA. Sin leak |
| 9 | admin | admin ✓ | 14 | 50% | 14×50% (floor) | 0 | Asistentes/recepcionistas/secretarias/administradores — todas legítimas |
| 10 | trades | trades ✓ | 60 (paginado 20/60) | 70% | 4×70% + 16×50% | 0 | Mecánico, servicios generales, soldador — todos oficios concretos legítimos |

## UI/UX backlog (descubierto durante test plan)

- **Registro vertical alignment**: la columna izquierda del wizard de tipo
  cuenta (`/auth/register`) arranca mucho más abajo que la del login
  (`/auth/login`). El heading "¿Qué tipo de cuenta querés crear?" debería
  alinearse a la misma altura que "Bienvenido de vuelta" del login para
  consistencia visual.
- **Dashboard race condition**: tras submitear el wizard de perfil, el
  dashboard muestra "Mostrando 0 de 0" hasta refresh manual (~1-2s). El
  feed se popula después de la persistencia del JWT. Investigar si el
  auth interceptor está usando token stale, o si falta un await en el
  redirect post-save.

## Cleanup

Los datos de test viven solo en la DB local (`database/db.sqlite3`).
Para reset completo:
- `rm database/db.sqlite3 && python manage.py migrate && python manage.py loaddata database/offers_dump.json`

No hay nada que limpiar en prod — todo el plan corre offline.
