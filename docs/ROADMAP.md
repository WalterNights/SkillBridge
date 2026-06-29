# Roadmap — Próxima sesión

Plan de trabajo para mejorar SkilTak después del despliegue inicial. Tres frentes en paralelo: **arquitectura del código**, **funcionalidades de IA y scraping**, y **rediseño del frontend con Stitch**.

---

## 1. Auditoría de código + Arquitectura

> Objetivo: limpiar deuda técnica, aplicar SOLID, eliminar acoplamiento y duplicación, dejar el código preparado para crecer (más scrapers, más proveedores de IA, más funcionalidades).

### Estado actual observado

**Backend**
- Apps Django: `users`, `jobs`, `dashboard`, `resumes` (esta última solo tiene un PDF, parece sobrar como app).
- Ya hay separación `services/` (lógica de negocio) y `utils/` (helpers), lo cual es **buena base**.
- Posibles olores detectados en el pre-scan:
  - Duplicación entre [backend/users/services/cv_analyzer_service.py](../backend/users/services/cv_analyzer_service.py) y [backend/users/utils/cv_analyzer.py](../backend/users/utils/cv_analyzer.py).
  - [backend/jobs/utils/scraper.py](../backend/jobs/utils/scraper.py) es monolítico (121 líneas) y solo soporta Computrabajo → no es extensible.
  - [backend/users/services/gemini_cv_service.py](../backend/users/services/gemini_cv_service.py) (281 líneas) probablemente acopla la lógica al proveedor concreto (Gemini), sin interfaz.
  - `tests.py` existe en cada app pero no fue inspeccionado — probablemente vacíos.

**Frontend**
- Angular 19 standalone components + Tailwind 4 → stack moderno.
- A revisar: tamaño de componentes, lógica HTTP en componentes (debería estar en servicios), uso de `RxJS` sin `takeUntilDestroyed`, accesibilidad, manejo de estados de carga/error.

### Arquitectura propuesta a evaluar

**Backend — variante ligera de Clean Architecture / Ports & Adapters**

Capas:
```
views.py / serializers.py         ← capa HTTP (Django REST)
        │
services/                          ← casos de uso (lógica de negocio)
        │
domain/  (nuevo, opcional)         ← entidades puras, sin Django
        │
adapters/ (nuevo)                  ← clientes externos: scrapers, IA, email
        │
models.py                          ← persistencia (Django ORM)
```

**Patrones específicos a aplicar**:

| Patrón | Dónde | Por qué |
|---|---|---|
| **Strategy** | Scrapers de portales | Una interfaz `JobScraper` + `ComputrabajoScraper`, `InfojobsScraper`, `LinkedInScraper`. Cambiar portal = cambiar implementación. |
| **Factory** | Selección del scraper | `ScraperFactory.get_for(portal)` evita ifs anidados. |
| **Adapter** | Proveedores de IA | `AIProvider` abstracto + `GeminiAdapter`, `OpenAIAdapter`, `ClaudeAdapter`. Permite swap sin tocar la lógica. |
| **Repository** | Acceso a datos | `JobRepository`, `UserRepository` aíslan Django ORM del resto, facilitan tests con mocks. |
| **DTO** (Pydantic) | Boundaries | Serializers de DRF para HTTP, Pydantic para data entre capas. Ya está `pydantic` en deps. |
| **Command/Query separation** | Services | `CreateProfileCommand` vs `GetMatchingJobsQuery`. Hace explícito qué muta vs qué lee. |

**Checklist de buenas prácticas a aplicar mientras refactorizamos**:
- [ ] Single Responsibility: ningún archivo > 300 líneas, ninguna función > 50 líneas.
- [ ] Open/Closed: agregar un nuevo portal de scraping NO debería tocar código existente.
- [ ] Liskov: las implementaciones de `JobScraper` deben respetar el contrato (no lanzar excepciones inesperadas).
- [ ] Interface Segregation: si una clase implementa una interfaz pero solo usa 2/8 métodos, partir la interfaz.
- [ ] Dependency Inversion: services deben depender de **interfaces** (`AIProvider`), no de implementaciones (`GeminiClient`).
- [ ] **DRY**: detectar duplicación con [code-quality](../README.md) skill.
- [ ] **No sobrecarga**: funciones con > 4 parámetros → pasar un dataclass.
- [ ] **Naming**: nombres expresivos. `process_data()` ❌ vs `enrich_profile_with_skills()` ✓.
- [ ] **Errores tipados**: jerarquía de excepciones propia (`ScraperError`, `AIProviderError`) en lugar de `Exception` genéricas.
- [ ] **Logging estructurado**: agregar `structlog` o usar `logging` con contexto (user_id, job_id).
- [ ] **Tests**: cobertura mínima de servicios. Pytest + fixtures para Django.

### Entregables de esta tarea

1. Reporte de auditoría (severidad por archivo, refactor prioritarios).
2. Propuesta concreta de estructura de carpetas final.
3. Plan de migración incremental (no big bang).
4. Tests de regresión antes de tocar nada crítico.

---

## 2. Mejoras funcionales

### 2.a Análisis de perfil con IA — **Seguimos con Gemini, pero mejorado**

> Objetivo: que el análisis del CV/perfil sea más completo, confiable y útil para el matching. **Decisión**: mantener Gemini (free tier alcanza, Claude requiere pago). Aplicamos las mismas mejoras arquitectónicas y aprovechamos features de Gemini que probablemente no están usadas hoy.

**Mejoras que Gemini ya soporta y probablemente no usamos**:
- **`response_schema`** (JSON schema con Pydantic) → elimina el parseo frágil del texto devuelto. Gemini garantiza que la salida cumple el schema.
- **Multimodal nativo** → mandar el PDF directo como `Part.from_data(mime_type="application/pdf", data=pdf_bytes)`. Gemini 2.0 Flash y 1.5 Pro leen PDFs con layout/tablas/imágenes. Elimina dependencia de PyMuPDF/pdfplumber para extraer texto antes.
- **Context caching** (`cachedContents`) → si el system prompt + taxonomía de skills es estable (>32K tokens en 1.5 Pro), cachear baja drásticamente costo y latencia.
- **Function calling** → para análisis paso a paso (ej. "primero extraé skills, después matcheá con taxonomía").

**Refactor del servicio** ([backend/users/services/gemini_cv_service.py](../backend/users/services/gemini_cv_service.py)):

Aunque por ahora hay solo un proveedor, **vale la pena introducir la abstracción** ya: facilita tests con mocks, deja la puerta abierta a swap futuro (Claude/OpenAI) sin reescribir el dominio, y separa preocupaciones (lógica de análisis vs. cliente IA).

```python
# backend/users/services/cv_analyzer.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
import google.generativeai as genai

class CVAnalysisResult(BaseModel):
    nombre: str
    email: str | None
    experiencia: list[dict]
    skills_tecnicos: list[str]
    skills_blandos: list[str]
    educacion: list[dict]
    aniosExperiencia: int

class CVAnalyzer(ABC):
    @abstractmethod
    def analyze(self, cv_bytes: bytes, mime_type: str = "application/pdf") -> CVAnalysisResult: ...

class GeminiCVAnalyzer(CVAnalyzer):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model,
            system_instruction=SYSTEM_PROMPT_ANALISIS_CV,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": CVAnalysisResult,
            },
        )

    def analyze(self, cv_bytes, mime_type="application/pdf"):
        response = self.model.generate_content([
            {"mime_type": mime_type, "data": cv_bytes},
            "Analizá este CV y devolvé el JSON estructurado.",
        ])
        return CVAnalysisResult.model_validate_json(response.text)

# Fallback local sin red (para tests + degradación)
class LocalNLPAnalyzer(CVAnalyzer):
    """Usa nlp_service.py + cv_keywords. No requiere API."""
    def analyze(self, cv_bytes, mime_type="application/pdf"): ...

# Composición con fallback
class CVAnalyzerWithFallback(CVAnalyzer):
    def __init__(self, primary: CVAnalyzer, fallback: CVAnalyzer): ...
    def analyze(self, cv_bytes, mime_type="application/pdf"):
        try: return self.primary.analyze(cv_bytes, mime_type)
        except Exception: return self.fallback.analyze(cv_bytes, mime_type)
```

**A decidir en la próxima sesión**:
- ¿Qué modelo de Gemini? `gemini-2.0-flash-exp` (rápido, free tier generoso) vs `gemini-1.5-pro` (más preciso, también free tier).
- ¿Cache por hash del CV (en Redis o DB)? Si el usuario sube el mismo PDF 2 veces no llamamos a la API.
- ¿Wrapping con retry exponencial para errores transitorios (429, 503)?
- ¿Validación cruzada con `nlp_service.py` después de Gemini? (verificar que los skills devueltos existen en la taxonomía conocida).
- ¿Embeddings para matching CV ↔ oferta? Gemini tiene `text-embedding-004` gratis. Alternativa: `sentence-transformers` local (sin red).

**Cuándo evaluar migrar a Claude más adelante**:
- Si Gemini empieza a fallar / rate-limitear con uso real
- Si necesitamos features que Gemini no tiene tan bien (ej. seguimiento estricto de instrucciones complejas)
- Si el negocio puede absorber USD ~5-20/mes de costo cuando crezca
- La abstracción `CVAnalyzer` deja el swap como cambio de 1 archivo: agregar `ClaudeCVAnalyzer(CVAnalyzer)` y cambiar la inyección de dependencia.

**Patrón sugerido**:

```python
# Interface abstracta — services depende de esto, no de Gemini directamente
class CVAnalyzer(ABC):
    @abstractmethod
    def analyze(self, cv_bytes: bytes) -> CVAnalysisResult: ...

# Implementaciones intercambiables
class GeminiCVAnalyzer(CVAnalyzer): ...
class LocalNLPAnalyzer(CVAnalyzer): ...  # fallback sin red, basado en spaCy

# Composición con fallback
class CVAnalyzerWithFallback(CVAnalyzer):
    def __init__(self, primary: CVAnalyzer, fallback: CVAnalyzer): ...
    def analyze(self, cv_bytes):
        try: return self.primary.analyze(cv_bytes)
        except AIProviderError: return self.fallback.analyze(cv_bytes)
```

### 2.b Multi-portal scraping

> Objetivo: pasar de **1 portal (Computrabajo)** a **5+ portales** (Computrabajo, InfoJobs, Magneto, Indeed, LinkedIn, Bumeran, Glassdoor) sin que el código se vuelva inmantenible.

**Patrón obligatorio**: Strategy + Factory (descrito arriba).

```python
# backend/jobs/adapters/scrapers/__init__.py
class JobScraper(ABC):
    portal_name: str
    @abstractmethod
    def search(self, query: SearchQuery) -> list[JobOffer]: ...

# Una clase por portal
class ComputrabajoScraper(JobScraper): ...
class InfojobsScraper(JobScraper): ...
class IndeedScraper(JobScraper): ...
class LinkedInScraper(JobScraper): ...  # ¡ojo!, ver nota legal abajo

# Factory que devuelve el scraper apropiado
class ScraperRegistry:
    def get_all(self) -> list[JobScraper]: ...
    def get_by_name(self, name: str) -> JobScraper: ...
```

**A decidir**:
- **Async vs sync**: scrapear 5 portales en paralelo con `asyncio` + `httpx` puede reducir latencia de 25s a 5s. Pero Celery + asyncio juntos son delicados. Alternativa: lanzar 1 task de Celery por portal y agregar resultados.
- **Rate limiting**: cada portal tiene sus límites. Implementar backoff exponencial + cache.
- **Anti-bot**: LinkedIn e Indeed tienen detección agresiva. Considerar:
  - APIs oficiales donde existan (Indeed Publisher, LinkedIn Jobs API — requieren cuenta).
  - Servicios de proxy/scraping (ScraperAPI, Bright Data) — pago.
  - Headless browser (Playwright) con stealth — más pesado pero efectivo.
- **Normalización**: cada portal devuelve estructuras distintas. Un `JobOffer` canónico común (Pydantic model) + un `mapper` por portal.
- **Deduplicación**: la misma oferta puede aparecer en 3 portales. Hash por (titulo + empresa + ubicación) o embeddings.

**⚠️ Nota legal/ética**:
- **Computrabajo, InfoJobs, Magneto, Bumeran**: scraping suele ser tolerado para uso personal limitado.
- **LinkedIn**: TOS prohíbe scraping. Hay riesgo legal (caso hiQ Labs vs LinkedIn). Mejor usar su [Jobs API oficial](https://learn.microsoft.com/en-us/linkedin/talent/job-postings) si es viable.
- **Indeed**: tiene API de publisher.
- Documentar en una constante por scraper qué portales son seguros y cuáles requieren autorización.

### Entregables de esta tarea

1. Estructura `backend/jobs/adapters/scrapers/` con interfaz + al menos 3 implementaciones.
2. Sistema de tasks Celery paralelas para scrapear N portales.
3. Modelo canónico `JobOffer` + deduplicación.
4. Mejora del análisis de CV con `response_schema` de Gemini + fallback local.
5. Tests unitarios de cada scraper con respuestas mockeadas (HTML fixtures).

---

## 3. Rediseño del frontend con Stitch

> Objetivo: un diseño que comunique "vas a conseguir el trabajo que buscás" en los primeros 3 segundos. Visual, emocional, moderno.

**El MCP de Stitch ya está configurado** ([.claude/settings.local.json](../.claude/settings.local.json)) — al iniciar la próxima sesión tendré los tools `mcp__stitch__*` disponibles.

### Pantallas a generar/rediseñar (prioridad)

1. **Landing** (`/`) — hero impactante. Hoy probablemente es genérico.
   - Hero con video/animación sutil de personas trabajando + headline emocional.
   - Sección de social proof (logos, testimonios, métricas: "X CVs analizados", "Y matches exitosos").
   - CTA principal: "Sube tu CV y encuentra tu próximo empleo" — un solo botón gigante.
   - Microcopy enfocado en aspiraciones, no en features.
2. **Onboarding / Subida de CV** (`/profile-builder`) — primer wow moment.
   - Drag & drop con preview en vivo del PDF.
   - Loader con frases tipo "Detectando tus skills...", "Buscando empresas que te necesitan..." (genera dopamina vs spinner clásico).
3. **Dashboard** (`/dashboard`) — el feed de oportunidades.
   - Cards de ofertas con score de matching visual (radial progress, no número).
   - Filtros por portal de origen, salario, modalidad, ubicación.
   - Diferenciar visualmente "match alto" vs "explorar".
4. **Detalle de oferta** (`/job-detail/:id`) — comparación CV ↔ oferta.
   - Skills que tenés vs skills que pide → highlights verde/amarillo/rojo.
   - "Por qué este match" generado por IA.
5. **Resultados / Match list** (`/results`)
6. **ATS CV Optimizer** (`/ats-cv`) — diferencial fuerte. Vale UI específica.

### Estilo a pedirle a Stitch

- Paleta moderna: pongamos como base oscura + un acento vibrante (azul eléctrico o magenta).
- Tipografía: Inter o similar para UI, una display tipográfica audaz para titulares.
- Glassmorphism + soft shadows + bordes redondeados generosos (`rounded-2xl`).
- Microinteracciones (hover scale, fade-in al scrollear, skeleton loaders animados).
- Iconografía consistente: ya está `lucide-angular` en deps → usarlo en todo.
- **Mobile-first** real: muchos buscadores de empleo usan mobile.

### Flujo con Stitch

1. En la próxima sesión, prompt al MCP de Stitch: `"Diseñá una landing page para SkilTak: plataforma con IA que matchea CVs con ofertas laborales. Estilo moderno, dark mode, glassmorphism, paleta azul-magenta. Mobile-first."`
2. Stitch devuelve HTML+Tailwind.
3. Lo porto a Angular standalone components.
4. Iteración: refinar prompts hasta tener todas las pantallas.
5. Cuando estén las pantallas core, refactor del CSS para reutilizar (design tokens en `tailwind.config.js`).

### Entregables de esta tarea

1. 5-6 pantallas generadas con Stitch + portadas a Angular.
2. `tailwind.config.js` con design tokens (colores, espaciados, fuentes).
3. Librería de componentes reutilizables: `<job-card>`, `<skill-badge>`, `<match-score>`, `<empty-state>`.
4. Animaciones con Angular Animations o GSAP.

---

## Orden sugerido

```
Día 1 — Tarea 1 (auditoría):
  1. Code review profundo (skill /code-quality + /security-review)
  2. Reporte de hallazgos + plan de refactor priorizado
  3. Acordar arquitectura final con vos

Día 2 — Tarea 2.b (scrapers):
  1. Crear interfaz JobScraper + Factory
  2. Refactorizar Computrabajo a la nueva interfaz
  3. Implementar 2 portales nuevos (InfoJobs + Indeed)
  4. Tasks Celery paralelas + deduplicación

Día 3 — Tarea 2.a (IA):
  1. Refactor de gemini_cv_service con interface CVAnalyzer
  2. response_schema de Gemini + cache por hash
  3. Fallback local con nlp_service

Día 4 — Tarea 3 (Stitch + frontend):
  1. Generar las 6 pantallas con Stitch
  2. Portar a Angular standalone
  3. Componentes reutilizables + design tokens

Día 5 — Pulido:
  1. Tests faltantes
  2. Lighthouse audit (performance, accesibilidad)
  3. Deploy con todo lo nuevo
```

## Pendientes que arrastramos del deploy

- [ ] **Rotar credenciales expuestas**: PAT GitHub, Gemini API, Gmail app password, Stitch key.
- [ ] Después de rotar, actualizar `.env.prod` + `scp` al VPS + `systemctl restart skiltak-gunicorn skiltak-celery`.
- [ ] Actualizar acciones de GitHub Actions cuando salgan versiones con Node 24 (warning actual no bloquea).

## Para arrancar la próxima sesión

Decime simplemente: **"Arrancá con la Tarea 1: auditoría de código"** y largo con `/code-quality` sobre el backend + revisión manual de los archivos críticos.
