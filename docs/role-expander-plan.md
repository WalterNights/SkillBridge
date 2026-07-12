# Role Expander — Query expansion pre-scrape

**Estado:** propuesta validada, pendiente de implementación
**Última actualización:** 2026-07-08
**Autor original:** Walter + discusión con IA en sesión de trabajo

## Contexto y motivación

Hoy `PortalRouterService.suggest_portals(profile)` extrae **un único query**
del título profesional del usuario ([backend/jobs/services/portal_router.py:90](../backend/jobs/services/portal_router.py#L90))
usando `_extract_primary_role`. Ese query se envía **idéntico** a los 10-12
portales que scrapeamos por perfil.

**Consecuencia:** un user con título `"Full Stack Developer"` **solo** ve
ofertas cuyo título contiene `full`, `stack` o `developer`. NO ve:

- `"Backend Developer"` (aunque probablemente le calce)
- `"Frontend Developer"` (idem)
- `"Desarrollador Backend .NET"` (idem, especialmente si tiene .NET en skills)

Un user "Zootecnista" **solo** ve ofertas con `zootecnista` en el título,
NO `"Médico Veterinario"` o `"Ingeniero Agrónomo"` (mismo vertical agro,
mismo tipo de trabajo). Hoy Fabio ve estas ofertas al 45% en su feed solo
si **otro user** las scrapeó primero (piso vertical del matcher) — no
porque hicimos búsqueda directa para él.

### Malentendido común

El "boost same-vertical" y el "piso vertical (45%)" del matcher **NO son
query expansion**. Solo son mecanismos de rescate en el matcher post-scrape.
Query expansion es un problema distinto: qué le pedimos a Computrabajo /
LinkedIn en tiempo de scrape.

## Objetivo

Cuando un user dispara scrape, buscar **múltiples queries relacionados** en
cada portal en vez de uno. Deduplicación por URL canónica (ya existe —
`normalize_url` desde el commit 475ede66) se encarga del solapamiento.

## Diseño

### Módulo nuevo: `backend/jobs/services/role_expander.py`

Función pura, sin efectos secundarios:

```python
def expand_role_queries(
    title: str,
    category: str,
    skills: list[str],
) -> list[str]:
    """Devuelve la lista de queries a scrapear para el user.

    Siempre incluye el rol principal como primer elemento (respeta la
    prioridad del user). Cap a MAX_EXPANSIONS para no explotar el
    volumen de scraping. Dedup case-insensitive.
    """
```

**Fuentes de expansión, en orden de prioridad:**

1. **Rol principal normalizado** (siempre incluido).
   Extraído con el `_extract_primary_role` que ya usamos.

2. **Sinónimo bidireccional ES↔EN** (aprovecha `_TITLE_SYNONYMS` de
   `matching_service.py`):
   - "Full Stack Developer" → agregar "Desarrollador Full Stack"
   - "Zootecnista" → no aplica (no hay traducción común usada)
   Cubre portales bilingües (LinkedIn, WeWorkRemotely).

3. **Roles hermanos por dict curado** — mapeo explícito de "roles vecinos"
   agrupados por vertical (ver dict abajo).

4. **Stack-based (opcional, solo tech)** — si el user tiene skills tech
   relevantes, generar 1 query "Backend Developer <top-skill>" o similar.
   Solo aplica si el rol es genérico ("developer", "engineer") y hay una
   skill dominante en las primeras 3-5 declaradas.

### Dict curado (draft del mapeo)

```python
# Keys en lowercase + sin tildes para lookup normalizado.
# Values son tuples de queries adicionales (no incluyen la key).
_ROLE_EXPANSIONS: dict[str, tuple[str, ...]] = {
    # Tech - generalistas y frameworks comunes
    "full stack developer": (
        "desarrollador full stack",
        "backend developer",
        "frontend developer",
    ),
    "backend developer": (
        "desarrollador backend",
        "full stack developer",
    ),
    "frontend developer": (
        "desarrollador frontend",
        "full stack developer",
        "ui developer",
    ),
    "mobile developer": (
        "desarrollador mobile",
        "android developer",
        "ios developer",
        "react native developer",
    ),
    "data scientist": (
        "cientifico de datos",
        "data analyst",
        "ml engineer",
    ),
    "devops engineer": (
        "sre",
        "cloud engineer",
        "platform engineer",
    ),

    # Design
    "ui/ux designer": (
        "diseñador ui/ux",
        "product designer",
    ),
    "product designer": (
        "diseñador de producto",
        "ui/ux designer",
    ),

    # Agro (caso Fabio)
    "zootecnista": (
        "medico veterinario",
        "ingeniero agronomo",
        "avicultor",
    ),
    "medico veterinario": (
        "veterinario",
        "zootecnista",
    ),
    "ingeniero agronomo": (
        "agronomo",
        "zootecnista",
    ),

    # Marketing / ventas
    "community manager": (
        "social media manager",
        "marketing digital",
    ),
    "growth marketer": (
        "marketing digital",
        "performance marketing",
    ),

    # ... arrancar con ~15 keys, extender con feedback real
}
```

### Cap y configuración

```python
# En core/settings.py
ROLE_EXPANSION_ENABLED = True  # feature flag para rollback rápido
ROLE_EXPANSION_MAX_QUERIES = 4  # cap
```

**Trade-off del cap:**
- 3 queries → 3× volumen scrape → conservador
- 4 queries → 4× volumen → recomendado (balance)
- 5+ queries → riesgo de rate-limit en portales (LinkedIn especialmente)

### Integración en el flow existente

**Cambio 1** — `PortalRouterService.suggest_portals` devuelve **N × M**
planes (N queries × M portales) en vez de 1 × M:

```python
# Antes:
plans.append(PortalPlan(portal=portal_name, query=query, location=location))

# Después:
for expanded_query in expand_role_queries(profile.professional_title,
                                          category,
                                          _split_skills(profile.skills)):
    plans.append(PortalPlan(portal=portal_name,
                            query=expanded_query,
                            location=location))
```

**Cambio 2** — `_scrape_one_portal` no requiere cambios. Sigue procesando
un `PortalPlan` con un query. Solo hay más planes.

**Cambio 3** — dedup. Ya existe via `normalize_url` en
`JobService.save_new_offers`. Sin cambios necesarios.

## Ejemplos verificados

### Caso Walter (tech, fullstack)

**Input:**
- `title="FullStack Developer"`
- `category="tech"`
- `skills=["React.js", "Angular.js", "Node.js", "Python", "Django", ...]`

**Output esperado (cap 4):**
```
1. Full Stack Developer          # principal (extract_primary_role)
2. Desarrollador Full Stack      # sinónimo ES
3. Backend Developer             # hermano por dict
4. Frontend Developer            # hermano por dict
```

Con stack-based habilitado (opcional):
```
1. Full Stack Developer
2. Desarrollador Full Stack
3. Backend Developer Node        # stack: Node.js
4. Frontend Developer Angular    # stack: Angular
```

### Caso Fabio (agro, zootecnista)

**Input:**
- `title="Zootecnista"`
- `category="agro"`
- `skills=["ganado", "pasturas", "avicultura"]`

**Output esperado (cap 4):**
```
1. Zootecnista                   # principal
2. Medico Veterinario            # hermano por dict
3. Ingeniero Agronomo            # hermano por dict
4. Avicultor                     # hermano por dict
```

Fabio ahora tiene búsquedas ACTIVAS de "Médico Veterinario" en
Computrabajo/Magneto/etc, no solo espera que otro user las scrapeé.

## Trade-offs honestos

| Dimensión | Beneficio | Costo/Riesgo |
|---|---|---|
| Recall | ↑ 2-4× ofertas por scrape (empíricamente) | 3-4× más tiempo por scrape/user |
| Precisión | El matcher honesto (post rewrite) filtra bien | Ninguno — ofertas irrelevantes salen <40% y no aparecen |
| Costo scraping | — | Portales pueden rate-limitear (LinkedIn ya lo hace) |
| Mantenimiento | — | Dict a mantener con feedback de usuarios reales |
| Latencia scrape sync | — | ~30s → ~90-120s por scrape sync |

**Duración típica del scrape:**
- Actualmente: ~30s por user (comentario `daily_scrape_for_active_users`
  en `jobs/tasks.py:68`).
- Con expansion (cap 4): ~90-120s por user.
- Ventana nocturna del cron (04:00 UTC): 100 users × 120s = 200 min.
  Fuera de la ventana de una hora — necesita paralelización o
  ejecución en varias tandas.

## Fases de implementación

### Fase 1 — Módulo base (dedicated PR)

- [ ] `backend/jobs/services/role_expander.py` con `expand_role_queries()`
      + dict curado (~15 keys iniciales).
- [ ] Tests unitarios: casos tech, agro, design, marketing +
      edge cases (título vacío, sin match en dict, con y sin skills).
- [ ] Feature flag `ROLE_EXPANSION_ENABLED` en settings.

### Fase 2 — Integración en el router (dedicated PR)

- [ ] `PortalRouterService.suggest_portals` itera sobre queries expandidas.
- [ ] Test de integración: verificar que con Walter genera N × M planes.
- [ ] Test de anti-regresión: sin `ROLE_EXPANSION_ENABLED`, comportamiento
      idéntico al anterior.

### Fase 3 — Ajuste del cron (dedicated PR)

- [ ] `daily_scrape_for_active_users`: chequear que la ventana nocturna
      alcanza con el nuevo volumen. Si no, paralelizar con `chord` o
      dividir en tandas.
- [ ] Alertas: log del tiempo total del cron para detectar drift.

### Fase 4 — Feedback y ajuste del dict

- [ ] Después de 1-2 semanas de datos reales, revisar:
      - ¿Cuántas ofertas nuevas trajo el expansion vs el baseline?
      - ¿El match% de las ofertas nuevas es honesto (>= 40)?
      - ¿Portales rate-limitearon?
- [ ] Agregar/quitar keys del dict según feedback.

### Fase 5 — Opcional: stack-based expansion

Solo si Fase 1-4 muestran valor claro. Requiere lógica extra para mapear
skill → categoría de stack (ej. "React.js" → "React" → válido para
frontend/fullstack). Skips si aparece mucho ruido.

## Preguntas abiertas

1. **¿El expansion aplica solo al scrape "buscar más ofertas" del user,
   o también al cron diario?** — Sugerencia: ambos, pero el cron debe
   monitorearse por tiempo total.

2. **¿Guardamos qué query trajo cada oferta?** — Ayuda a debug pero
   agrega complejidad al modelo. Alternativa: log estructurado sin
   persistir en DB.

3. **¿El feature flag es global o per-user (feature flag admin
   controlable)?** — Global es más simple. Per-user permite A/B testing
   pero requiere infra.

## Referencias

- `backend/jobs/services/portal_router.py:65-118` — `suggest_portals`
  actual.
- `backend/jobs/services/matching_service.py:101-147` —
  `_extract_primary_role`.
- `backend/jobs/services/matching_service.py:152-178` — `_TITLE_SYNONYMS`
  que ya existe (solo se usa en matcher post-scrape hoy).
- `backend/users/services/profession_classifier.py:244-263` —
  `_PATTERNS` de categorías macro.
- `backend/jobs/adapters/scrapers/base.py:59` — firma
  `search(query: str, ...)` de los scrapers.
- Commit `475ede66` — dedupe por URL canónica que hace que el expansion
  no explote la DB con duplicados.
