"""
Tareas asíncronas para el módulo de jobs.
"""
from celery import shared_task
import logging

from jobs.utils.scraper import scrap_computrabajo
from jobs.models import JobOffer

logger = logging.getLogger(__name__)


@shared_task(name='jobs.scrape_job_offers')
def scrape_job_offers(query: str, location: str):
    """
    Tarea asíncrona para scraping de ofertas de trabajo.
    
    Args:
        query: Término de búsqueda (título profesional)
        location: Ubicación para buscar ofertas
        
    Returns:
        Dict con número de ofertas creadas
    """
    logger.info(f"Starting async scraping task: query='{query}', location='{location}'")
    
    try:
        new_offers = scrap_computrabajo(query, location)
        count = len(new_offers)
        
        logger.info(f"Scraping task completed successfully. Created {count} offers")
        
        return {
            'status': 'success',
            'offers_created': count,
            'query': query,
            'location': location
        }
    except Exception as e:
        logger.error(f"Scraping task failed: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'query': query,
            'location': location
        }


@shared_task(name='jobs.clean_old_offers')
def clean_old_offers(days_old: int = 30):
    """
    Tarea asíncrona para limpiar ofertas antiguas.
    
    Args:
        days_old: Número de días para considerar una oferta como antigua
        
    Returns:
        Dict con número de ofertas eliminadas
    """
    from datetime import timedelta
    from django.utils import timezone
    
    logger.info(f"Starting cleanup task for offers older than {days_old} days")
    
    try:
        cutoff_date = timezone.now() - timedelta(days=days_old)
        deleted_count, _ = JobOffer.objects.filter(created_at__lt=cutoff_date).delete()
        
        logger.info(f"Cleanup completed. Deleted {deleted_count} old offers")
        
        return {
            'status': 'success',
            'offers_deleted': deleted_count,
            'days_old': days_old
        }
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }
