"""
Servicio para matching de ofertas de trabajo con perfiles de usuario.
"""
from typing import List, Dict
from django.db.models import QuerySet
from django.core.cache import cache

from jobs.models import JobOffer
from users.models import UserProfile
from users.services.nlp_service import NLPService


class JobMatchingService:
    """Servicio para matching de ofertas con perfiles de usuario"""
    
    @staticmethod
    def calculate_match_percentage(
        job_keywords: List[str], 
        user_skills: List[str],
        use_semantic: bool = False
    ) -> Dict[str, any]:
        """
        Calcula el porcentaje de match entre keywords de job y skills de usuario.
        
        Args:
            job_keywords: Lista de keywords del trabajo
            user_skills: Lista de skills del usuario
            use_semantic: Si True, usa similaridad semántica con NLP
            
        Returns:
            Dict con matched_skills, missing_skills, match_percentage
        """
        # Limpiar y normalizar keywords
        job_keywords_clean = [
            kw.strip().lower() 
            for kw in job_keywords 
            if kw.strip()
        ]
        user_skills_clean = [
            skill.strip().lower() 
            for skill in user_skills
        ]
        
        if not job_keywords_clean:
            return {
                'matched_skills': [],
                'missing_skills': [],
                'match_percentage': 0
            }
        
        # Calcular skills que coinciden (matching exacto)
        matched_skills = [
            kw for kw in job_keywords_clean 
            if kw in user_skills_clean
        ]
        
        # Calcular skills faltantes
        missing_skills = [
            kw for kw in job_keywords_clean 
            if kw not in user_skills_clean
        ]
        
        # Si se usa matching semántico, buscar similitudes
        if use_semantic and missing_skills:
            semantic_matches = JobMatchingService._find_semantic_matches(
                missing_skills, 
                user_skills_clean
            )
            matched_skills.extend(semantic_matches)
            missing_skills = [
                skill for skill in missing_skills 
                if skill not in semantic_matches
            ]
        
        # Calcular porcentaje
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
        Filtra jobs por skills del usuario y porcentaje mínimo de match.
        
        Args:
            jobs: QuerySet de JobOffer
            user_profile: Perfil del usuario
            min_match_percentage: Porcentaje mínimo de match (default: 50)
            
        Returns:
            Lista de JobOffer filtrados y enriquecidos con datos de match
        """
        if not user_profile.skills:
            return []
        
        user_skills = user_profile.skills.split(',')
        filtered_jobs = []
        
        for job in jobs:
            if not job.keywords:
                continue
                
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
    
    @staticmethod
    def _find_semantic_matches(
        missing_skills: List[str], 
        user_skills: List[str],
        threshold: float = 0.8
    ) -> List[str]:
        """
        Encuentra matches semánticos entre skills usando NLP.
        
        Args:
            missing_skills: Skills que no tuvieron match exacto
            user_skills: Skills del usuario
            threshold: Umbral de similaridad (0-1)
            
        Returns:
            Lista de skills con match semántico
        """
        semantic_matches = []
        
        for missing_skill in missing_skills:
            for user_skill in user_skills:
                # Calcular similaridad semántica
                similarity = NLPService.calculate_text_similarity(
                    missing_skill,
                    user_skill
                )
                
                if similarity >= threshold:
                    semantic_matches.append(missing_skill)
                    break  # Ya encontramos match para esta skill
        
        return semantic_matches
    
    @staticmethod
    def get_top_matched_jobs(
        user_profile: UserProfile,
        limit: int = 10,
        use_cache: bool = True
    ) -> List[JobOffer]:
        """
        Obtiene los top N jobs mejor matched con el usuario.
        Usa caché para mejorar performance.
        
        Args:
            user_profile: Perfil del usuario
            limit: Número máximo de jobs a retornar
            use_cache: Si True, usa caché de Redis
            
        Returns:
            Lista de JobOffer ordenados por match
        """
        cache_key = f'top_jobs_user_{user_profile.user.id}_limit_{limit}'
        
        # Intentar obtener desde caché
        if use_cache:
            cached_results = cache.get(cache_key)
            if cached_results:
                return cached_results
        
        # Si no hay caché, calcular
        all_jobs = JobOffer.objects.all()
        filtered_jobs = JobMatchingService.filter_jobs_by_skills(
            all_jobs,
            user_profile,
            min_match_percentage=30  # Umbral más bajo para top matches
        )
        
        result = filtered_jobs[:limit]
        
        # Guardar en caché por 10 minutos
        if use_cache:
            cache.set(cache_key, result, 600)
        
        return result
