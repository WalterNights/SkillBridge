# 📊 Análisis Detallado y Plan de Refactorización - SkillBridge Backend

**Fecha:** 7 de Diciembre, 2025  
**Versión Actual:** Django 5.2.3 + DRF 3.16.0  
**Analista:** GitHub Copilot

---

## 📑 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Análisis de la Arquitectura Actual](#análisis-de-la-arquitectura-actual)
3. [Problemas Identificados](#problemas-identificados)
4. [Plan de Refactorización](#plan-de-refactorización)
5. [Mejoras Tecnológicas Propuestas](#mejoras-tecnológicas-propuestas)
6. [Roadmap de Implementación](#roadmap-de-implementación)

---

## 🎯 Resumen Ejecutivo

### Estado Actual
SkillBridge es una plataforma de matching de ofertas laborales que analiza CVs y conecta usuarios con oportunidades de empleo. El backend está construido con Django y Django REST Framework.

### Hallazgos Principales
- ✅ **Fortalezas:** Arquitectura modular básica, uso de JWT para autenticación, funcionalidad de scraping implementada
- ⚠️ **Problemas Críticos:** Falta de validación robusta, código duplicado, imports con wildcard, SQLite en producción
- 🔄 **Oportunidades:** Implementar caché, mejorar arquitectura, agregar testing, optimizar queries

### Prioridades
1. **CRÍTICO:** Seguridad y configuración
2. **ALTO:** Arquitectura y código limpio
3. **MEDIO:** Performance y optimización
4. **BAJO:** Testing y documentación

---

## 🏗️ Análisis de la Arquitectura Actual

### Estructura de Aplicaciones

```
backend/
├── core/           # Configuración principal
├── users/          # Gestión de usuarios y perfiles
├── jobs/           # Ofertas de trabajo y scraping
├── dashboard/      # Dashboard administrativo
└── resumes/        # (Vacío - posible app no utilizada)
```

### Tecnologías Utilizadas

| Categoría | Tecnología | Versión | Estado |
|-----------|-----------|---------|--------|
| Framework | Django | 5.2.3 | ✅ Actualizado |
| API | Django REST Framework | 3.16.0 | ✅ Actualizado |
| Auth | SimpleJWT | 5.5.0 | ✅ Actualizado |
| Base de Datos | SQLite | N/A | ⚠️ No recomendado para producción |
| Scraping | BeautifulSoup | 4.13.4 | ✅ Actualizado |
| PDF Processing | pdfplumber, PyMuPDF | Múltiples | ⚠️ Redundante |
| Word Processing | python-docx | 1.2.0 | ✅ OK |

---

## 🔍 Problemas Identificados

### 🔴 CRÍTICOS (Prioridad Alta)

#### 1. Seguridad y Configuración

**Problema:** `settings.py` expone credenciales y configuración insegura
```python
# ❌ PROBLEMA
SECRET_KEY = 'django-insecure-^%jjoou+0w6#s!j4_cut=w7)0g0e_as8@)x^ug_=3&7#1n_met'
DEBUG = True
ALLOWED_HOSTS = []
CORS_ALLOW_ALL_ORIGIN = True  # Muy inseguro
```

**Impacto:** Alta vulnerabilidad de seguridad, posible exposición de datos

**Solución:**
- Usar variables de entorno con `python-decouple` o `django-environ`
- Separar configuraciones por ambiente (dev, staging, prod)
- Implementar CORS apropiado
- Configurar `ALLOWED_HOSTS` correctamente

---

#### 2. Imports con Wildcard

**Problema:** Imports `from .models import *` en múltiples archivos
```python
# ❌ PROBLEMA en users/views.py, jobs/views.py, etc.
from .models import *
from .serializers import *
```

**Impacto:** 
- Contaminación del namespace
- Dificulta el debugging
- Oculta dependencias
- Conflictos potenciales

**Solución:**
```python
# ✅ CORRECTO
from users.models import User, UserProfile
from users.serializers import UserSerializer, UserProfileSerializer
```

---

#### 3. Base de Datos SQLite en Producción

**Problema:** SQLite no es adecuado para aplicaciones web en producción
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATA_DIR / 'db.sqlite3',
    }
}
```

**Impacto:**
- No soporta concurrencia
- Limitaciones de escalabilidad
- Sin capacidades de replicación

**Solución:** Migrar a PostgreSQL con `psycopg2` o `psycopg3`

---

### 🟡 ALTOS (Prioridad Media-Alta)

#### 4. Código Duplicado y Lógica en Vistas

**Problema:** Lógica de negocio compleja en vistas
```python
# ❌ PROBLEMA en jobs/views.py
class JobsOfferViwe(APIView):  # Typo en nombre
    def get(self, request):
        jobs = JobOffer.objects.all()
        user_skills = request.user.profile.skills
        filter_jobs = []
        for job in jobs:
            offer_skill = job.keywords.split(',')
            matched_skills = [kw for kw in offer_skill if kw.strip() and kw in user_skills.lower()]
            # ... lógica compleja ...
```

**Impacto:**
- Dificulta testing
- Código no reutilizable
- Violación de principios SOLID

**Solución:**
- Extraer lógica a servicios/managers
- Usar Django QuerySets optimizados
- Implementar capa de servicios

---

#### 5. Falta de Validación y Manejo de Errores

**Problema:** Validación insuficiente en múltiples endpoints
```python
# ❌ PROBLEMA en users/views.py
class UserProfileCheckView(APIView):
    def get(self, request):
        profile = request.user.profile  # ⚠️ Puede fallar
        if not profile.full_name:  # ⚠️ full_name no existe en el modelo
            return Response({"profile_complete": False})
```

**Impacto:**
- Errores no controlados
- Experiencia de usuario pobre
- Dificulta debugging

**Solución:**
```python
# ✅ CORRECTO
class UserProfileCheckView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = request.user.profile
            is_complete = all([
                profile.first_name,
                profile.last_name,
                profile.city,
                profile.phone
            ])
            return Response({"profile_complete": is_complete})
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
```

---

#### 6. Uso de APIView en lugar de ViewSets

**Problema:** Código repetitivo y no aprovecha DRF
```python
# ❌ PROBLEMA - Código repetitivo
class JobOfferDetailView(APIView):
    def get(self, request, pk):
        try:
            job = JobOffer.objects.get(pk=pk)
        except JobOffer.DoesNotExist:
            return Response({'error': "No existe"}, status=404)
        serializer = JobOfferSerializer(job)
        return Response(serializer.data)
```

**Solución:**
```python
# ✅ MEJOR - Usar ViewSets
from rest_framework import viewsets

class JobOfferViewSet(viewsets.ModelViewSet):
    queryset = JobOffer.objects.all()
    serializer_class = JobOfferSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Filtrado personalizado
        return super().get_queryset().filter(...)
```

---

#### 7. Scraper Sincrónico y Bloqueante

**Problema:** Web scraping bloquea el request
```python
# ❌ PROBLEMA en jobs/views.py
class JobScrapingView(APIView):
    def get(self, request):
        # ... 
        new_offers = scrap_computrabajo(query, location)  # ⚠️ Bloquea
        # ...
```

**Impacto:**
- Timeouts en requests
- Mala experiencia de usuario
- No escalable

**Solución:**
- Implementar Celery + Redis para tareas asíncronas
- Usar Django Channels para WebSockets (feedback en tiempo real)
- Pattern de Job Queue

---

### 🟢 MEDIOS (Prioridad Media)

#### 8. Falta de Caché

**Problema:** Sin estrategia de caché implementada

**Impacto:**
- Queries repetitivas innecesarias
- Performance subóptima
- Carga innecesaria en BD

**Solución:**
```python
# ✅ Implementar Redis + django-redis
from django.core.cache import cache

@method_decorator(cache_page(60 * 15))  # 15 minutos
def get(self, request):
    # ...
```

---

#### 9. Modelos Poco Optimizados

**Problema:** Falta de índices y optimizaciones
```python
# ⚠️ ACTUAL
class UserProfile(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.PROTECT, related_name="profile")
    number_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    # ...
```

**Solución:**
```python
# ✅ MEJORADO
class UserProfile(models.Model):
    user = models.OneToOneField(
        "users.User", 
        on_delete=models.CASCADE,  # PROTECT puede causar problemas
        related_name="profile"
    )
    number_id = models.CharField(
        max_length=20, 
        unique=True, 
        null=True, 
        blank=True,
        db_index=True  # Índice para búsquedas
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['city', 'professional_title']),
        ]
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
```

---

#### 10. CV Analyzer - Lógica Frágil

**Problema:** Parser de CV con muchas suposiciones
```python
# ⚠️ PROBLEMA en cv_analyzer.py
def extract_city(text, country_name):
    # Asume formato específico
    data = text.split('.')[0]  # ⚠️ Frágil
    # ...
```

**Impacto:**
- Fallos con formatos diferentes
- Baja tasa de extracción exitosa
- Mantenimiento difícil

**Solución:**
- Usar spaCy o librería NLP para extracción de entidades
- Implementar múltiples estrategias de parsing
- Machine Learning para mejorar extracción

---

#### 11. Serializers con Lógica Compleja

**Problema:** Serializers haciendo más de lo necesario
```python
# ⚠️ PROBLEMA
class UserProfileSerializer(serializers.ModelSerializer):    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.phone:
            parts = instance.phone.strip().split()
            if len(parts) >= 2:
                rep["phone_code"] = parts[0]
                rep["phone_number"] = " ".join(parts[1:])
        return rep
```

**Solución:**
- Usar `SerializerMethodField` para campos calculados
- Crear campos de solo lectura/escritura apropiadamente
- Considerar múltiples serializers para diferentes contextos

---

### 🔵 BAJOS (Prioridad Baja - Mejoras)

#### 12. Falta de Testing

**Problema:** No hay tests implementados

**Solución:**
```python
# ✅ Implementar tests
from django.test import TestCase
from rest_framework.test import APITestCase

class UserProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='test',
            email='test@test.com',
            password='password123'
        )
    
    def test_profile_creation(self):
        # ...
```

---

#### 13. Sin Documentación de API

**Problema:** No hay documentación automática

**Solución:**
- Implementar Swagger/OpenAPI con `drf-spectacular`
- Documentar endpoints con docstrings

---

#### 14. Logging Insuficiente

**Problema:** Solo `print()` para logging
```python
# ❌ PROBLEMA
print("❌ Error al analizar el archivo CV:", str(e))
```

**Solución:**
```python
# ✅ CORRECTO
import logging
logger = logging.getLogger(__name__)

logger.error(f"Error analyzing CV: {str(e)}", exc_info=True)
```

---

## 🚀 Plan de Refactorización

### Fase 1: Fundamentos y Seguridad (Semana 1-2)

#### 1.1 Configuración y Seguridad

**Objetivo:** Asegurar la aplicación y separar configuraciones

**Tareas:**
1. Instalar `python-decouple`
2. Crear archivo `.env` y `.env.example`
3. Actualizar `settings.py` para usar variables de entorno
4. Crear `settings/` con `base.py`, `development.py`, `production.py`
5. Configurar CORS apropiadamente
6. Implementar rate limiting con `django-ratelimit`

**Implementación:**

```python
# settings/base.py
from decouple import config
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# CORS
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
CORS_ALLOW_CREDENTIALS = True
```

```env
# .env.example
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=skillbridge_db
DB_USER=skillbridge_user
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:4200
```

---

#### 1.2 Limpieza de Imports

**Objetivo:** Eliminar wildcard imports

**Script de ayuda:**
```bash
# Buscar todos los wildcard imports
grep -r "from .* import \*" backend/ --include="*.py"
```

**Cambios:**
- Reemplazar todos los `from .models import *` con imports explícitos
- Actualizar todos los archivos afectados

---

#### 1.3 Migración a PostgreSQL

**Objetivo:** Preparar para producción

**Tareas:**
1. Instalar PostgreSQL localmente
2. Instalar `psycopg2-binary`
3. Crear base de datos y usuario
4. Actualizar configuración
5. Migrar datos si es necesario

```bash
# Crear base de datos PostgreSQL
createdb skillbridge_db
createuser skillbridge_user -P

# En psql
GRANT ALL PRIVILEGES ON DATABASE skillbridge_db TO skillbridge_user;
```

---

### Fase 2: Arquitectura y Código Limpio (Semana 3-4)

#### 2.1 Implementar Capa de Servicios

**Objetivo:** Separar lógica de negocio de las vistas

**Estructura propuesta:**
```
backend/
├── users/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── profile_service.py
│   └── ...
└── jobs/
    ├── services/
    │   ├── __init__.py
    │   ├── job_service.py
    │   └── matching_service.py
    └── ...
```

**Ejemplo de implementación:**

```python
# jobs/services/matching_service.py
from typing import List, Dict
from django.db.models import QuerySet
from jobs.models import JobOffer
from users.models import UserProfile

class JobMatchingService:
    """Servicio para matching de ofertas con perfiles de usuario"""
    
    @staticmethod
    def calculate_match_percentage(
        job_keywords: List[str], 
        user_skills: List[str]
    ) -> Dict[str, any]:
        """
        Calcula el porcentaje de match entre keywords de job y skills de usuario
        
        Args:
            job_keywords: Lista de keywords del trabajo
            user_skills: Lista de skills del usuario
            
        Returns:
            Dict con matched_skills, missing_skills, match_percentage
        """
        job_keywords_clean = [kw.strip().lower() for kw in job_keywords if kw.strip()]
        user_skills_clean = [skill.strip().lower() for skill in user_skills]
        
        if not job_keywords_clean:
            return {
                'matched_skills': [],
                'missing_skills': [],
                'match_percentage': 0
            }
        
        matched_skills = [
            kw for kw in job_keywords_clean 
            if kw in user_skills_clean
        ]
        missing_skills = [
            kw for kw in job_keywords_clean 
            if kw not in user_skills_clean
        ]
        
        match_percentage = round(
            (len(matched_skills) / len(job_keywords_clean)) * 100
        )
        
        return {
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'match_percentage': match_percentage
        }
    
    @staticmethod
    def filter_jobs_by_skills(
        jobs: QuerySet[JobOffer], 
        user_profile: UserProfile,
        min_match_percentage: int = 50
    ) -> List[JobOffer]:
        """
        Filtra jobs por skills del usuario
        
        Args:
            jobs: QuerySet de JobOffer
            user_profile: Perfil del usuario
            min_match_percentage: Porcentaje mínimo de match
            
        Returns:
            Lista de JobOffer filtrados y enriquecidos con datos de match
        """
        user_skills = user_profile.skills.split(',')
        filtered_jobs = []
        
        for job in jobs:
            job_keywords = job.keywords.split(',')
            match_data = JobMatchingService.calculate_match_percentage(
                job_keywords, 
                user_skills
            )
            
            if match_data['match_percentage'] >= min_match_percentage:
                # Enriquecer objeto con datos de match
                job.matched_skills = match_data['matched_skills']
                job.missing_skills = match_data['missing_skills']
                job.match_percentage = match_data['match_percentage']
                filtered_jobs.append(job)
        
        # Ordenar por porcentaje de match descendente
        filtered_jobs.sort(
            key=lambda x: x.match_percentage, 
            reverse=True
        )
        
        return filtered_jobs
```

**Vista refactorizada:**

```python
# jobs/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from jobs.models import JobOffer
from jobs.serializers import JobOfferSerializer
from jobs.services.matching_service import JobMatchingService

class JobOfferViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ofertas de trabajo"""
    
    queryset = JobOffer.objects.all()
    serializer_class = JobOfferSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def matched(self, request):
        """Endpoint para obtener ofertas matched con el usuario"""
        try:
            user_profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User profile not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        jobs = self.get_queryset()
        filtered_jobs = JobMatchingService.filter_jobs_by_skills(
            jobs, 
            user_profile,
            min_match_percentage=50
        )
        
        serializer = self.get_serializer(filtered_jobs, many=True)
        return Response(serializer.data)
```

---

#### 2.2 Refactorizar ViewSets

**Objetivo:** Usar ViewSets de DRF apropiadamente

**Cambios:**
- Convertir APIViews a ViewSets
- Usar Routers para URLs
- Implementar acciones personalizadas con `@action`

```python
# core/urls.py
from rest_framework.routers import DefaultRouter
from jobs.views import JobOfferViewSet
from users.views import UserProfileViewSet

router = DefaultRouter()
router.register(r'jobs', JobOfferViewSet, basename='job')
router.register(r'profiles', UserProfileViewSet, basename='profile')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auth/', include('users.urls')),
]
```

---

#### 2.3 Optimizar Queries

**Objetivo:** Reducir queries N+1 y optimizar rendimiento

**Implementación:**

```python
# jobs/views.py
class JobOfferViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        # Usar select_related y prefetch_related
        return JobOffer.objects.select_related(
            'company'
        ).prefetch_related(
            'skills'
        ).order_by('-created_at')

# users/views.py  
class UserProfileViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return UserProfile.objects.select_related(
            'user'
        ).only(
            'id', 'first_name', 'last_name', 
            'professional_title', 'city'
        )
```

---

### Fase 3: Tareas Asíncronas y Performance (Semana 5-6)

#### 3.1 Implementar Celery + Redis

**Objetivo:** Mover scraping a tareas asíncronas

**Instalación:**
```bash
pip install celery redis django-celery-beat django-celery-results
```

**Configuración:**

```python
# core/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('skillbridge')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# settings/base.py
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
```

**Tarea asíncrona:**

```python
# jobs/tasks.py
from celery import shared_task
from jobs.services.scraping_service import ScrapingService

@shared_task(bind=True, max_retries=3)
def scrape_job_offers_task(self, query: str, location: str):
    """
    Tarea asíncrona para scraping de ofertas
    
    Args:
        query: Término de búsqueda
        location: Ubicación
        
    Returns:
        Dict con resultado del scraping
    """
    try:
        service = ScrapingService()
        new_offers = service.scrape_computrabajo(query, location)
        
        return {
            'status': 'success',
            'new_offers_count': len(new_offers),
            'message': f'{len(new_offers)} nuevas ofertas agregadas'
        }
    except Exception as exc:
        # Reintentar en caso de error
        raise self.retry(exc=exc, countdown=60)
```

**Vista actualizada:**

```python
# jobs/views.py
from jobs.tasks import scrape_job_offers_task

class JobOfferViewSet(viewsets.ReadOnlyModelViewSet):
    @action(detail=False, methods=['post'])
    def trigger_scraping(self, request):
        """Dispara scraping asíncrono"""
        user_profile = request.user.profile
        
        # Encolar tarea
        task = scrape_job_offers_task.delay(
            query=user_profile.professional_title,
            location=user_profile.city
        )
        
        return Response({
            'status': 'scraping_started',
            'task_id': task.id,
            'message': 'El scraping ha iniciado. Recibirás una notificación cuando termine.'
        })
```

---

#### 3.2 Implementar Caché con Redis

**Objetivo:** Reducir carga en BD y mejorar performance

**Configuración:**

```python
# settings/base.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Configurar sesiones en Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

**Uso en código:**

```python
# jobs/services/job_service.py
from django.core.cache import cache
from django.conf import settings

class JobService:
    CACHE_TTL = 60 * 15  # 15 minutos
    
    @staticmethod
    def get_featured_jobs():
        """Obtiene jobs destacados con caché"""
        cache_key = 'featured_jobs'
        jobs = cache.get(cache_key)
        
        if jobs is None:
            jobs = list(
                JobOffer.objects.filter(
                    is_featured=True
                ).values()[:10]
            )
            cache.set(cache_key, jobs, JobService.CACHE_TTL)
        
        return jobs
    
    @staticmethod
    def invalidate_job_cache():
        """Invalida caché de jobs"""
        cache.delete('featured_jobs')
        cache.delete_pattern('job_list_*')
```

---

#### 3.3 Mejorar CV Analyzer con NLP

**Objetivo:** Extracción más robusta de información

**Instalación:**
```bash
pip install spacy
python -m spacy download es_core_news_sm
```

**Implementación:**

```python
# users/services/cv_analyzer_service.py
import spacy
from typing import Dict, Optional

class CVAnalyzerService:
    """Servicio mejorado para análisis de CVs"""
    
    def __init__(self):
        self.nlp = spacy.load('es_core_news_sm')
    
    def extract_entities(self, text: str) -> Dict[str, any]:
        """
        Extrae entidades del texto usando NLP
        
        Args:
            text: Texto del CV
            
        Returns:
            Dict con entidades extraídas
        """
        doc = self.nlp(text)
        
        entities = {
            'persons': [],
            'organizations': [],
            'locations': [],
            'emails': [],
            'phones': []
        }
        
        for ent in doc.ents:
            if ent.label_ == 'PER':
                entities['persons'].append(ent.text)
            elif ent.label_ == 'ORG':
                entities['organizations'].append(ent.text)
            elif ent.label_ == 'LOC':
                entities['locations'].append(ent.text)
        
        # Extraer emails y teléfonos con regex
        import re
        entities['emails'] = re.findall(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
            text
        )
        entities['phones'] = re.findall(
            r'(\+\d{1,4})?[\s\-]?\(?\d{2,4}\)?[\s\-]?\d{6,10}', 
            text
        )
        
        return entities
    
    def analyze_cv(self, file, filetype: str = 'pdf') -> Dict[str, any]:
        """
        Analiza CV y extrae información
        
        Args:
            file: Archivo del CV
            filetype: Tipo de archivo (pdf, docx)
            
        Returns:
            Dict con información extraída
        """
        # Extraer texto
        if filetype == 'pdf':
            text = self._extract_text_from_pdf(file)
        elif filetype == 'docx':
            text = self._extract_text_from_docx(file)
        else:
            raise ValueError(f"Unsupported file type: {filetype}")
        
        # Analizar con NLP
        entities = self.extract_entities(text)
        
        # Estructurar resultado
        result = {
            'first_name': entities['persons'][0].split()[0] if entities['persons'] else '',
            'last_name': ' '.join(entities['persons'][0].split()[1:]) if entities['persons'] else '',
            'email': entities['emails'][0] if entities['emails'] else '',
            'phone_code': entities['phones'][0].split()[0] if entities['phones'] else '',
            'phone_number': ' '.join(entities['phones'][0].split()[1:]) if entities['phones'] else '',
            'city': entities['locations'][0] if entities['locations'] else '',
            'companies': entities['organizations'],
            'skills': self._extract_skills(text),
            'summary': self._extract_summary(text),
        }
        
        return result
```

---

### Fase 4: Testing y Documentación (Semana 7-8)

#### 4.1 Implementar Testing

**Objetivo:** Cobertura de tests > 80%

**Instalación:**
```bash
pip install pytest pytest-django pytest-cov factory-boy faker
```

**Configuración:**

```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = core.settings.test
python_files = tests.py test_*.py *_tests.py
addopts = --cov=. --cov-report=html --cov-report=term-missing

# core/settings/test.py
from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Desactivar Celery en tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

**Tests de ejemplo:**

```python
# users/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model
from users.models import UserProfile

User = get_user_model()

@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
    
    def test_user_profile_created_automatically(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert hasattr(user, 'profile')
        assert isinstance(user.profile, UserProfile)

# users/tests/test_api.py
import pytest
from rest_framework.test import APIClient
from rest_framework import status

@pytest.mark.django_db
class TestUserRegistration:
    def test_register_user_success(self):
        client = APIClient()
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123'
        }
        response = client.post('/api/users/register/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'data' in response.data
    
    def test_register_user_duplicate_email(self):
        # Test para email duplicado
        pass
```

---

#### 4.2 Documentación con Swagger/OpenAPI

**Objetivo:** Documentación automática e interactiva

**Instalación:**
```bash
pip install drf-spectacular
```

**Configuración:**

```python
# settings/base.py
INSTALLED_APPS = [
    # ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # ...
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'SkillBridge API',
    'DESCRIPTION': 'API para plataforma de matching de ofertas laborales',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# core/urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # ...
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

**Documentar endpoints:**

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter

class JobOfferViewSet(viewsets.ReadOnlyModelViewSet):
    @extend_schema(
        summary="Obtener ofertas matched",
        description="Retorna ofertas de trabajo que coinciden con las habilidades del usuario",
        parameters=[
            OpenApiParameter(
                name='min_match',
                type=int,
                description='Porcentaje mínimo de match (default: 50)',
                required=False
            )
        ],
        responses={200: JobOfferSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def matched(self, request):
        # ...
```

---

#### 4.3 Logging Estructurado

**Objetivo:** Mejorar debugging y monitoreo

**Configuración:**

```python
# settings/base.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'users': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'jobs': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

**Uso:**

```python
# jobs/services/scraping_service.py
import logging

logger = logging.getLogger(__name__)

class ScrapingService:
    def scrape_computrabajo(self, query: str, location: str):
        logger.info(f"Starting scraping for query='{query}', location='{location}'")
        
        try:
            # ... scraping logic
            logger.info(f"Scraping completed. Found {len(offers)} offers")
        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}", exc_info=True)
            raise
```

---

## 💡 Mejoras Tecnológicas Propuestas

### 1. Stack Tecnológico Recomendado

```python
# requirements/base.txt
Django==5.2.3
djangorestframework==3.16.0
djangorestframework-simplejwt==5.5.0

# Database
psycopg2-binary==2.9.9

# Async Tasks
celery==5.3.4
redis==5.0.1
django-celery-beat==2.5.0
django-celery-results==2.5.1

# Caching
django-redis==5.4.0

# Configuration
python-decouple==3.8

# API Documentation
drf-spectacular==0.27.0

# NLP
spacy==3.7.2

# Monitoring
sentry-sdk==1.39.1

# Testing
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
factory-boy==3.3.0
faker==20.1.0

# Code Quality
black==23.12.1
flake8==7.0.0
isort==5.13.2
mypy==1.7.1
```

---

### 2. Herramientas de Desarrollo

```bash
# Instalar pre-commit hooks
pip install pre-commit
pre-commit install

# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--extend-ignore=E203']
```

---

### 3. Monitoreo y Observabilidad

**Sentry para error tracking:**

```python
# settings/production.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=config('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True,
    environment=config('ENVIRONMENT', default='production')
)
```

---

### 4. CI/CD Pipeline

**GitHub Actions workflow:**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ master, develop ]
  pull_request:
    branches: [ master, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements/test.txt
    
    - name: Run linting
      run: |
        black --check .
        flake8 .
        isort --check-only .
    
    - name: Run tests
      run: |
        pytest --cov --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## 🗺️ Roadmap de Implementación

### Sprint 1-2: Fundamentos (2 semanas)
- ✅ Configuración con variables de entorno
- ✅ Limpieza de imports wildcard
- ✅ Migración a PostgreSQL
- ✅ Configuración de seguridad básica
- ✅ Setup de desarrollo (pre-commit hooks)

### Sprint 3-4: Arquitectura (2 semanas)
- ✅ Implementar capa de servicios
- ✅ Refactorizar a ViewSets
- ✅ Optimizar queries
- ✅ Mejorar serializers
- ✅ Implementar validaciones robustas

### Sprint 5-6: Performance (2 semanas)
- ✅ Setup Celery + Redis
- ✅ Mover scraping a tareas asíncronas
- ✅ Implementar caché
- ✅ Mejorar CV analyzer con NLP
- ✅ Optimizar modelos (índices)

### Sprint 7-8: Quality Assurance (2 semanas)
- ✅ Implementar tests (>80% coverage)
- ✅ Documentación con Swagger
- ✅ Logging estructurado
- ✅ Setup CI/CD
- ✅ Code review y refactoring final

### Sprint 9+: Extras (ongoing)
- 🔄 Monitoring con Sentry
- 🔄 Rate limiting
- 🔄 API versioning
- 🔄 Paginación optimizada
- 🔄 Filtros avanzados
- 🔄 WebSockets para notificaciones real-time

---

## 📊 Métricas de Éxito

### Pre-Refactorización
- ❌ Cobertura de tests: 0%
- ❌ Seguridad: Múltiples vulnerabilidades
- ❌ Performance: Sin caché, queries N+1
- ❌ Mantenibilidad: Código acoplado

### Post-Refactorización
- ✅ Cobertura de tests: >80%
- ✅ Seguridad: Variables de entorno, CORS configurado
- ✅ Performance: Redis caché, queries optimizados
- ✅ Mantenibilidad: Código limpio, SOLID principles

---

## 🎓 Recursos y Referencias

### Documentación
- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Two Scoops of Django](https://www.feldroy.com/books/two-scoops-of-django-3-x)

### Herramientas
- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/)
- [Django Extensions](https://django-extensions.readthedocs.io/)
- [Django Silk](https://github.com/jazzband/django-silk) - Profiling

---

## ✅ Checklist de Implementación

### Seguridad
- [ ] Variables de entorno implementadas
- [ ] SECRET_KEY en .env
- [ ] DEBUG = False en producción
- [ ] ALLOWED_HOSTS configurado
- [ ] CORS configurado apropiadamente
- [ ] Rate limiting implementado
- [ ] HTTPS enforced en producción

### Código Limpio
- [ ] Todos los wildcard imports eliminados
- [ ] Lógica de negocio en servicios
- [ ] ViewSets implementados
- [ ] Validaciones robustas
- [ ] Logging estructurado
- [ ] Code style consistente (Black, isort)

### Performance
- [ ] PostgreSQL en producción
- [ ] Redis implementado
- [ ] Celery configurado
- [ ] Caché implementado
- [ ] Queries optimizados (select_related, prefetch_related)
- [ ] Índices en BD

### Testing
- [ ] Tests unitarios (>80% coverage)
- [ ] Tests de integración
- [ ] Tests de API
- [ ] CI/CD pipeline

### Documentación
- [ ] README actualizado
- [ ] API documentada (Swagger)
- [ ] Docstrings en código
- [ ] Guía de deployment

---

## 🚨 Consideraciones Finales

### Riesgos
1. **Migración de BD:** Backup completo antes de migrar a PostgreSQL
2. **Cambios Breaking:** Comunicar cambios de API al frontend
3. **Dependencias:** Verificar compatibilidad de todas las librerías

### Recomendaciones
1. Implementar cambios de forma incremental
2. Mantener rama de desarrollo separada
3. Realizar code reviews antes de merge
4. Testear en ambiente de staging antes de producción
5. Documentar todos los cambios significativos

---

## 📝 Conclusión

Este plan de refactorización transformará el backend de SkillBridge en una aplicación **robusta, escalable y mantenible**. La implementación debe ser **gradual y metódica**, priorizando seguridad y estabilidad.

**Tiempo estimado total:** 8-10 semanas  
**Esfuerzo recomendado:** 1-2 desarrolladores full-time

---

**Documento creado:** Diciembre 7, 2025  
**Última actualización:** Diciembre 7, 2025  
**Versión:** 1.0.0
