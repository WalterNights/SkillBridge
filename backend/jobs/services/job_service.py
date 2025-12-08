"""
Servicio para gestión de ofertas de trabajo.
"""
import logging
from typing import List, Optional
from django.db.models import QuerySet

from jobs.models import JobOffer
from jobs.utils.scraper import scrap_computrabajo

logger = logging.getLogger(__name__)


class JobService:
    """Servicio para operaciones con ofertas de trabajo"""
    
    @staticmethod
    def get_all_jobs() -> QuerySet[JobOffer]:
        """
        Obtiene todas las ofertas de trabajo.
        
        Returns:
            QuerySet de JobOffer ordenados por fecha de creación
        """
        return JobOffer.objects.all().order_by('-created_at')
    
    @staticmethod
    def get_job_by_id(job_id: int) -> Optional[JobOffer]:
        """
        Obtiene una oferta por su ID.
        
        Args:
            job_id: ID de la oferta
            
        Returns:
            JobOffer o None si no existe
        """
        try:
            return JobOffer.objects.get(pk=job_id)
        except JobOffer.DoesNotExist:
            logger.warning(f"Job with id {job_id} not found")
            return None
    
    @staticmethod
    def scrape_new_jobs(query: str, location: str) -> List[JobOffer]:
        """
        Ejecuta scraping de nuevas ofertas.
        
        Args:
            query: Término de búsqueda (título profesional)
            location: Ubicación
            
        Returns:
            Lista de JobOffer nuevas creadas
        """
        logger.info(f"Starting scraping for query='{query}', location='{location}'")
        
        try:
            new_offers = scrap_computrabajo(query, location)
            logger.info(f"Scraping completed. Found {len(new_offers)} new offers")
            return new_offers
        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def get_recent_jobs(limit: int = 20) -> QuerySet[JobOffer]:
        """
        Obtiene las ofertas más recientes.
        
        Args:
            limit: Número máximo de ofertas
            
        Returns:
            QuerySet de JobOffer
        """
        return JobOffer.objects.all().order_by('-created_at')[:limit]
    
    @staticmethod
    def search_jobs(keyword: str) -> QuerySet[JobOffer]:
        """
        Busca ofertas por palabra clave en título o resumen.
        
        Args:
            keyword: Palabra clave a buscar
            
        Returns:
            QuerySet de JobOffer que coinciden
        """
        from django.db.models import Q
        
        return JobOffer.objects.filter(
            Q(title__icontains=keyword) | 
            Q(summary__icontains=keyword) |
            Q(keywords__icontains=keyword)
        ).order_by('-created_at')
