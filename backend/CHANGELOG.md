# Changelog - SkillBridge Backend

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [1.2.0] - 2025-12-07

### 🎉 Fase 3: Performance y NLP - COMPLETADA

#### ✅ Agregado

- **Integración de Celery y Redis**
  - Configurado Celery como task queue asíncrono
  - Redis configurado como broker y result backend
  - `core/celery.py`: Aplicación Celery con autodiscovery de tareas
  - Variables de entorno: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

- **Tareas Asíncronas**
  - `jobs/tasks.py`:
    - `scrape_job_offers()`: Scraping asíncrono de ofertas
    - `clean_old_offers()`: Limpieza automática de ofertas antiguas
  - `users/tasks.py`:
    - `analyze_cv_async()`: Análisis asíncrono de CVs con actualización automática de perfil

- **Procesamiento de Lenguaje Natural (NLP)**
  - Integrado spaCy 3.8.3 para análisis semántico
  - `users/services/nlp_service.py`: Servicio centralizado de NLP
    - `extract_entities()`: Extracción de entidades nombradas (personas, organizaciones, lugares)
    - `extract_skills_nlp()`: Identificación inteligente de skills técnicas
    - `calculate_text_similarity()`: Similaridad semántica entre textos
    - `extract_key_phrases()`: Extracción de frases clave
    - `generate_summary()`: Generación automática de resúmenes
  - `CVAnalyzerService` mejorado con NLP:
    - `enhance_with_nlp()`: Enriquecimiento de datos extraídos con análisis NLP
    - Skills adicionales detectadas automáticamente
    - Generación de summaries cuando no existen
    - Extracción de nombres usando entidades nombradas

- **Matching Semántico**
  - `JobMatchingService` con análisis semántico:
    - `_find_semantic_matches()`: Matching por similaridad semántica (threshold 0.8)
    - Parámetro `use_semantic` en `calculate_match_percentage()`
    - Detecta skills equivalentes aunque no coincidan textualmente

- **Sistema de Caché con Redis**
  - Configurado django-redis como backend de caché
  - `CACHES` con Redis en settings.py
  - Cache key prefix: 'skillbridge'
  - Timeout por defecto: 5 minutos
  - Sesiones almacenadas en Redis para mejor performance
  - Caché en `get_top_matched_jobs()` (10 minutos TTL)

#### 🔧 Mejorado

- **Performance**
  - Matching de jobs cacheado por usuario
  - Queries optimizados con `select_related('user')` en perfiles
  - Tareas pesadas (scraping, CV analysis) ejecutadas en background
  - Reducción de carga en servidor web

- **Inteligencia del Sistema**
  - Matching más preciso con análisis semántico
  - Detección automática de skills variantes (ej: "js" vs "javascript")
  - Extracción de información mejorada en CVs complejos
  - Generación automática de summaries profesionales

- **Escalabilidad**
  - Arquitectura preparada para múltiples workers Celery
  - Redis como punto único de caché distribuido
  - Tareas asíncronas no bloquean requests HTTP

#### 📦 Dependencias Agregadas

- celery==5.4.0
- redis==5.2.1
- django-redis==5.4.0
- spacy==3.8.3

## [1.1.0] - 2025-12-07

### 🎉 Fase 2: Arquitectura y Código Limpio - COMPLETADA

#### ✅ Agregado

- **Capa de Servicios**
  - `jobs/services/matching_service.py`: Lógica de matching entre jobs y perfiles
    - `JobMatchingService.calculate_match_percentage()`: Calcula porcentaje de coincidencia
    - `JobMatchingService.filter_jobs_by_skills()`: Filtra jobs por skills del usuario
    - `JobMatchingService.get_top_matched_jobs()`: Obtiene top N jobs mejor matched
  - `jobs/services/job_service.py`: Gestión de ofertas de trabajo
    - `JobService.get_all_jobs()`: Obtiene todas las ofertas
    - `JobService.get_job_by_id()`: Obtiene oferta por ID
    - `JobService.scrape_new_jobs()`: Ejecuta scraping de nuevas ofertas
    - `JobService.search_jobs()`: Busca ofertas por keyword
  - `users/services/profile_service.py`: Gestión de perfiles de usuario
    - `ProfileService.get_profile_by_user()`: Obtiene perfil por usuario
    - `ProfileService.create_profile()`: Crea nuevo perfil
    - `ProfileService.update_profile()`: Actualiza perfil existente
    - `ProfileService.profile_exists()`: Verifica existencia de perfil
  - `users/services/cv_analyzer_service.py`: Análisis de CVs
    - `CVAnalyzerService.analyze_cv()`: Analiza CV y extrae información
    - `CVAnalyzerService.validate_cv_file()`: Valida formato y tamaño de CV
    - `CVAnalyzerService.extract_skills_list()`: Extrae skills como lista

- **Refactorización a ViewSets**
  - `jobs/views.py`: Convertido a `JobOfferViewSet` con DRF ViewSets
    - Action `matched()`: Filtra jobs por matching con usuario
    - Action `scrape()`: Ejecuta scraping basado en perfil
    - Queries optimizados con `order_by('-created_at')`
  - `users/views.py`: Convertido a `UserProfileViewSet`
    - Action `check()`: Verifica completitud del perfil
    - Método `create()`: Maneja creación y actualización de perfiles
    - Queries optimizados con `select_related('user')`

- **URLs con Router**
  - `jobs/urls.py`: Implementado `DefaultRouter` para endpoints RESTful
    - `/api/jobs/jobs/` - Lista de ofertas
    - `/api/jobs/jobs/{id}/` - Detalle de oferta
    - `/api/jobs/jobs/matched/` - Ofertas matched
    - `/api/jobs/jobs/scrape/` - Scraping de ofertas
  - `users/urls.py`: Implementado `DefaultRouter`
    - `/api/users/profiles/` - CRUD de perfiles
    - `/api/users/profiles/check/` - Verificación de perfil

#### 🔧 Mejorado

- **Separación de Responsabilidades**
  - Lógica de negocio movida de vistas a servicios
  - Vistas ahora solo manejan requests/responses
  - Servicios encapsulan lógica reutilizable
  - Mejor testabilidad del código

- **Documentación de Código**
  - Docstrings completos en todos los servicios
  - Documentación de parámetros y retornos
  - Comentarios explicativos en lógica compleja

- **Logging**
  - Implementado logging en servicios críticos
  - Logs de info para operaciones exitosas
  - Logs de warning/error para problemas

## [1.0.0] - 2025-12-07

### 🎉 Fase 1: Fundamentos y Seguridad - COMPLETADA

#### ✅ Agregado

- **Variables de Entorno**
  - Implementado `python-decouple` para gestión de configuración
  - Creado archivo `.env.example` con todas las variables requeridas
  - Creado archivo `.env` para desarrollo local
  - Agregado `.gitignore` completo para proteger información sensible

- **Configuración Mejorada en settings.py**
  - `SECRET_KEY` ahora se carga desde variables de entorno
  - `DEBUG` configurable por entorno
  - `ALLOWED_HOSTS` configurable por entorno
  - Soporte para PostgreSQL con configuración condicional
  - CORS configurado apropiadamente con `CORS_ALLOWED_ORIGINS`
  - Configuración de JWT con timeouts personalizables
  - Paginación por defecto en DRF (20 items por página)

- **Documentación**
  - README.md completo con instrucciones de instalación
  - Guía de configuración de variables de entorno
  - Checklist de seguridad para producción
  - Documentación de endpoints principales
  - Estructura del proyecto documentada

#### 🔧 Corregido

- **Wildcard Imports Eliminados**
  - `users/views.py`: Imports explícitos de modelos y serializers
  - `users/serializers.py`: Imports explícitos
  - `users/urls.py`: Imports explícitos de vistas
  - `users/admin.py`: Imports explícitos
  - `jobs/views.py`: Imports explícitos
  - `jobs/urls.py`: Imports explícitos
  - `dashboard/views.py`: Imports explícitos
  - `dashboard/urls.py`: Imports explícitos

- **Errores y Typos Corregidos**
  - `jobs/views.py`: `JobsOfferViwe` → `JobsOfferView`
  - `jobs/urls.py`: Actualizada referencia a `JobsOfferView`
  - `dashboard/views.py`: `.daya` → `.data` en `dashboardUserData`
  - `users/views.py`: Corregida validación en `UserProfileCheckView` para usar campos correctos del modelo

- **Validaciones Mejoradas**
  - `UserProfileCheckView` ahora maneja correctamente `UserProfile.DoesNotExist`
  - Validación de perfil completo usando campos existentes del modelo

#### 🔒 Seguridad

- Eliminada exposición de `SECRET_KEY` en código
- Removido `CORS_ALLOW_ALL_ORIGIN = True` (inseguro)
- Implementado CORS apropiado con orígenes específicos
- `DEBUG` ahora es configurable y por defecto False
- Credenciales de base de datos movidas a variables de entorno

#### 📦 Dependencias

- Agregado `python-decouple==3.8` a requirements.txt

#### 📝 Cambios en Configuración

**settings.py:**
```python
# Antes
SECRET_KEY = 'django-insecure-...'
DEBUG = True
ALLOWED_HOSTS = []
CORS_ALLOW_ALL_ORIGIN = True

# Después
from decouple import config, Csv

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:4200', cast=Csv())
```

### 🔄 Archivos Modificados

1. `core/settings.py` - Refactorizado para usar variables de entorno
2. `users/views.py` - Eliminados wildcard imports, corregidas validaciones
3. `users/serializers.py` - Eliminados wildcard imports
4. `users/urls.py` - Eliminados wildcard imports
5. `users/admin.py` - Eliminados wildcard imports
6. `jobs/views.py` - Eliminados wildcard imports, corregido typo
7. `jobs/urls.py` - Eliminados wildcard imports, actualizada referencia
8. `dashboard/views.py` - Eliminados wildcard imports, corregido typo
9. `dashboard/urls.py` - Eliminados wildcard imports
10. `requirements.txt` - Agregado python-decouple

### 📄 Archivos Nuevos

1. `.env` - Variables de entorno para desarrollo
2. `.env.example` - Plantilla de variables de entorno
3. `.gitignore` - Configuración de archivos a ignorar
4. `README.md` - Documentación completa del proyecto
5. `CHANGELOG.md` - Este archivo
6. `ANALISIS_Y_REFACTORIZACION.md` - Plan completo de refactorización

### ✅ Tests

- ✅ `python manage.py check` - Sin errores
- ✅ Variables de entorno cargándose correctamente
- ✅ Servidor inicia sin errores
- ⚠️ Tests unitarios pendientes de implementación

### 📊 Métricas de Mejora

**Código:**
- Wildcard imports: 10 → 0 ✅
- Errores corregidos: 4 ✅
- Typos corregidos: 2 ✅

**Seguridad:**
- SECRET_KEY hardcodeada: ❌ → ✅
- DEBUG hardcodeado: ❌ → ✅
- CORS_ALLOW_ALL: ❌ → ✅
- Credenciales en código: ❌ → ✅

**Documentación:**
- README: No existía → Completo ✅
- Variables de entorno: No documentadas → Documentadas ✅
- .gitignore: No existía → Completo ✅

---

## [Próximas Versiones]

### [1.1.0] - Fase 2: Arquitectura (Planificado)

- [ ] Implementar capa de servicios
- [ ] Refactorizar a ViewSets
- [ ] Optimizar queries (select_related, prefetch_related)
- [ ] Mejorar serializers

### [1.2.0] - Fase 3: Performance (Planificado)

- [ ] Implementar Celery + Redis
- [ ] Agregar caché con Redis
- [ ] Mover scraping a tareas asíncronas
- [ ] Mejorar CV analyzer con NLP (spaCy)

### [1.3.0] - Fase 4: Testing (Planificado)

- [ ] Tests unitarios (>80% coverage)
- [ ] Tests de integración
- [ ] Documentación Swagger/OpenAPI
- [ ] CI/CD pipeline

---

## Formato

Este changelog sigue el formato de [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

### Tipos de Cambios

- **Agregado** para nuevas funcionalidades
- **Cambiado** para cambios en funcionalidad existente
- **Obsoleto** para funcionalidades que serán removidas
- **Removido** para funcionalidades removidas
- **Corregido** para corrección de bugs
- **Seguridad** para mejoras de seguridad
