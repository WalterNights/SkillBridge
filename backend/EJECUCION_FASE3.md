# Guía de Ejecución - Fase 3: Celery y Redis

## Requisitos Previos

1. **Redis instalado y ejecutándose**
2. **Modelo spaCy descargado**

## Instalación de Redis

### Windows
```powershell
# Opción 1: Windows Subsystem for Linux (WSL)
wsl --install
# Dentro de WSL:
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start

# Opción 2: Redis para Windows (Memurai)
# Descargar desde: https://www.memurai.com/

# Opción 3: Docker
docker run -d -p 6379:6379 redis:latest
```

### Linux/Mac
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Mac
brew install redis
brew services start redis
```

## Descargar Modelo de spaCy

```bash
# Activar entorno virtual
.\env\Scripts\Activate.ps1  # Windows
source env/bin/activate     # Linux/Mac

# Descargar modelo en inglés
python -m spacy download en_core_web_sm
```

## Ejecución del Sistema

### 1. Iniciar Redis
```bash
# Verificar que Redis esté ejecutándose
redis-cli ping
# Debe retornar: PONG
```

### 2. Iniciar Django
```bash
python manage.py runserver
```

### 3. Iniciar Celery Worker (Terminal separado)
```bash
# Activar entorno virtual
.\env\Scripts\Activate.ps1

# Iniciar worker
celery -A core worker --loglevel=info --pool=solo
```

### 4. (Opcional) Iniciar Celery Beat para tareas periódicas
```bash
celery -A core beat --loglevel=info
```

## Verificar Funcionamiento

### Test de Redis
```bash
redis-cli
> SET test "Hello Redis"
> GET test
> EXIT
```

### Test de Celery
```python
from jobs.tasks import scrape_job_offers

# Ejecutar tarea asíncrona
result = scrape_job_offers.delay("Python Developer", "Bogotá")
print(f"Task ID: {result.id}")
print(f"Status: {result.status}")
```

### Test de NLP
```python
from users.services.nlp_service import NLPService

text = "I'm a Python developer with experience in Django and React"
skills = NLPService.extract_skills_nlp(text)
print(f"Skills found: {skills}")
```

## Endpoints con Caché

Los siguientes endpoints usan caché de Redis:

- `GET /api/jobs/jobs/matched/` - Caché de 10 minutos
- Top matched jobs por usuario - Caché de 10 minutos

Para limpiar el caché:
```python
from django.core.cache import cache
cache.clear()
```

## Tareas Asíncronas Disponibles

### Scraping de Ofertas
```python
from jobs.tasks import scrape_job_offers

result = scrape_job_offers.delay(
    query="Software Engineer",
    location="Colombia"
)
```

### Análisis de CV
```python
from users.tasks import analyze_cv_async

result = analyze_cv_async.delay(
    cv_file_path="/path/to/cv.pdf",
    user_id=1
)
```

### Limpieza de Ofertas Antiguas
```python
from jobs.tasks import clean_old_offers

result = clean_old_offers.delay(days_old=30)
```

## Monitoreo

### Ver tareas en ejecución
```bash
celery -A core inspect active
```

### Ver workers registrados
```bash
celery -A core inspect registered
```

### Ver estadísticas
```bash
celery -A core inspect stats
```

## Troubleshooting

### Redis no conecta
```bash
# Verificar que Redis esté ejecutándose
netstat -an | findstr :6379  # Windows
netstat -an | grep 6379      # Linux/Mac

# Verificar configuración en .env
CELERY_BROKER_URL=redis://localhost:6379/0
```

### Celery no encuentra tareas
```bash
# Verificar que las apps estén en INSTALLED_APPS
# Verificar que los archivos tasks.py existan en cada app
```

### spaCy model no found
```bash
python -m spacy download en_core_web_sm
```

## Performance Tips

1. **Múltiples Workers**: Ejecutar varios workers Celery en paralelo
```bash
celery -A core worker --concurrency=4
```

2. **Monitoreo con Flower**: Interface web para Celery
```bash
pip install flower
celery -A core flower
# Abrir http://localhost:5555
```

3. **Caché Agresivo**: Aumentar TTL para datos estables
```python
cache.set(key, value, 3600)  # 1 hora
```
