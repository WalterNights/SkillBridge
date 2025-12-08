"""
Configuración de Celery para SkillBridge.
"""
import os
from celery import Celery
from decouple import config

# Configurar Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Crear instancia de Celery
app = Celery('skillbridge')

# Cargar configuración desde Django settings con namespace CELERY
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en todas las apps instaladas
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tarea de debug para verificar que Celery funciona"""
    print(f'Request: {self.request!r}')
