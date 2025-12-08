# SkillBridge Backend

Backend API para la plataforma SkillBridge - Sistema de matching de ofertas laborales con análisis de CVs.

## 🚀 Características

- ✅ Autenticación JWT
- ✅ Análisis automático de CVs (PDF/DOCX)
- ✅ Web scraping de ofertas laborales
- ✅ Matching inteligente basado en habilidades
- ✅ API REST completa
- ✅ Panel administrativo Django

## 📋 Requisitos

- Python 3.11+
- PostgreSQL (recomendado para producción) o SQLite (desarrollo)
- pip

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd SkillBridge/backend
```

### 2. Crear entorno virtual

```bash
python -m venv env
```

**Windows:**
```bash
env\Scripts\activate
```

**Linux/Mac:**
```bash
source env/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia el archivo `.env.example` a `.env`:

```bash
cp .env.example .env
```

Edita el archivo `.env` con tus configuraciones:

```env
SECRET_KEY=tu-secret-key-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:4200
```

**⚠️ IMPORTANTE:** Genera una nueva SECRET_KEY para producción:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Ejecutar migraciones

```bash
python manage.py migrate
```

### 6. Crear superusuario (opcional)

```bash
python manage.py createsuperuser
```

### 7. Ejecutar servidor de desarrollo

```bash
python manage.py runserver
```

El servidor estará disponible en: `http://localhost:8000`

## 📁 Estructura del Proyecto

```
backend/
├── core/                   # Configuración principal de Django
│   ├── settings.py        # Configuración (usa variables de entorno)
│   ├── urls.py            # URLs principales
│   └── wsgi.py
├── users/                 # App de usuarios y perfiles
│   ├── models.py          # User, UserProfile
│   ├── views.py           # Registro, perfil, análisis de CV
│   ├── serializers.py     # Serializers DRF
│   └── utils/             # Utilidades (analizador de CV)
├── jobs/                  # App de ofertas de trabajo
│   ├── models.py          # JobOffer
│   ├── views.py           # Scraping, matching, listado
│   ├── serializers.py
│   └── utils/             # Scraper, filtros
├── dashboard/             # App del dashboard
├── manage.py
├── requirements.txt
├── .env.example          # Ejemplo de variables de entorno
└── .gitignore
```

## 🔐 Endpoints Principales

### Autenticación
- `POST /api/token/` - Obtener token JWT
- `POST /api/token/refresh/` - Refrescar token
- `POST /api/token/login/` - Login con datos adicionales

### Usuarios
- `POST /api/users/register/` - Registro de usuario
- `POST /api/users/profile/` - Crear/actualizar perfil
- `GET /api/users/profile/check/` - Verificar si perfil está completo
- `POST /api/users/resume-analyzer/` - Analizar CV (PDF/DOCX)

### Ofertas de Trabajo
- `GET /api/jobs/jobs-offer/` - Listar ofertas matched con usuario
- `GET /api/jobs/jobs-details/<id>/` - Detalle de oferta
- `GET /api/jobs/scrap-jobs/` - Ejecutar scraping de nuevas ofertas

### Dashboard
- `GET /api/dashboard/` - Listar todos los perfiles

## 🔒 Configuración de Seguridad

### Variables de Entorno Importantes

```env
# Producción
SECRET_KEY=tu-secret-key-super-segura
DEBUG=False
ALLOWED_HOSTS=tudominio.com,www.tudominio.com

# Base de datos PostgreSQL (recomendado)
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=skillbridge_db
DATABASE_USER=skillbridge_user
DATABASE_PASSWORD=tu-password-seguro
DATABASE_HOST=localhost
DATABASE_PORT=5432

# CORS
CORS_ALLOWED_ORIGINS=https://tudominio.com
```

### Checklist de Seguridad para Producción

- [ ] Cambiar `SECRET_KEY` a un valor único y seguro
- [ ] Configurar `DEBUG=False`
- [ ] Configurar `ALLOWED_HOSTS` correctamente
- [ ] Usar PostgreSQL en lugar de SQLite
- [ ] Configurar CORS apropiadamente
- [ ] Usar HTTPS
- [ ] Configurar variables de entorno, nunca hardcodear credenciales
- [ ] Implementar rate limiting
- [ ] Configurar logs apropiadamente

## 🧪 Testing

```bash
# Ejecutar todos los tests (cuando estén implementados)
python manage.py test

# Con pytest (recomendado para futuro)
pytest
```

## 📊 Cambios Recientes - Fase 1 de Refactorización

### ✅ Implementado (Diciembre 2025)

1. **Variables de Entorno**
   - Implementado `python-decouple`
   - Creado `.env` y `.env.example`
   - Refactorizado `settings.py` para usar variables de entorno
   - SECRET_KEY, DEBUG, ALLOWED_HOSTS ahora configurables

2. **Código Limpio**
   - ❌ Eliminados todos los wildcard imports (`from .models import *`)
   - ✅ Imports explícitos en todos los archivos
   - ✅ Corregidos typos: `JobsOfferViwe` → `JobsOfferView`
   - ✅ Corregido error en `dashboardUserData` (`.daya` → `.data`)
   - ✅ Corregida validación en `UserProfileCheckView`

3. **Configuración Mejorada**
   - Agregada configuración de JWT (timeouts, refresh)
   - Configurada paginación por defecto en DRF
   - CORS configurado apropiadamente
   - Creado `.gitignore` completo

4. **Documentación**
   - README.md completo
   - Documentación de instalación
   - Guía de configuración
   - Checklist de seguridad

### 🔄 Próximos Pasos (Fase 2)

Ver el archivo `ANALISIS_Y_REFACTORIZACION.md` para el plan completo:

1. **Fase 2:** Arquitectura y Código Limpio (Semanas 3-4)
   - Implementar capa de servicios
   - Refactorizar a ViewSets
   - Optimizar queries

2. **Fase 3:** Performance (Semanas 5-6)
   - Celery + Redis para tareas asíncronas
   - Caché con Redis
   - Mejorar CV analyzer con NLP

3. **Fase 4:** Testing y Documentación (Semanas 7-8)
   - Tests unitarios >80% coverage
   - Documentación Swagger/OpenAPI
   - CI/CD pipeline

## 🐛 Problemas Conocidos

- ⚠️ Warning de `pkg_resources` deprecado (librería de terceros)
- 📝 Falta implementar tests
- 📝 Scraping es síncrono (bloqueante)
- 📝 Sin caché implementado

## 📚 Recursos

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [JWT Authentication](https://django-rest-framework-simplejwt.readthedocs.io/)

## 👥 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es privado.

---

**Última actualización:** Diciembre 7, 2025  
**Versión:** 1.0.0 (Post-Refactorización Fase 1)
