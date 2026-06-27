"""
Servicio para matching de ofertas de trabajo con perfiles de usuario.

Diseño del scoring (post-Junio 2026):
- El cargo profesional pesa MÁS que la lista de skills extraídas, porque
  muchos posts de empleo no enumeran un stack en el body ("Buscamos
  desarrollador con experiencia") y antes esos quedaban en 0% y se
  filtraban. Ahora un job sin keywords cuyo título matchea con el cargo
  del usuario recibe un score basado en el título solo (capado a 70%
  para reservar el 100% a coincidencias completas).
- Cuando el job SÍ trae skills detectadas, el score combina:
      match_percentage = 60% * title_score + 40% * skill_score
  El peso favorece al título porque es el indicador más confiable: si
  no coincide el rol, las skills compartidas suelen ser coincidencias
  ruidosas (alguien que sabe Python pero el job es "Data Scientist"
  no es un buen match para un Full Stack Developer).
"""

from __future__ import annotations

import re

from django.core.cache import cache
from django.db.models import QuerySet

from common.skills_taxonomy import normalize
from jobs.models import JobOffer
from users.models import UserProfile
from users.services.nlp_service import NLPService

# Palabras que aportan ruido al comparar títulos profesionales. ES + EN
# porque mezclamos portales en ambos idiomas.
_TITLE_STOPWORDS: frozenset[str] = frozenset({
    "de", "del", "el", "la", "los", "las", "en", "para", "con", "y", "o",
    "un", "una", "the", "a", "an", "of", "for", "in", "and", "or", "with",
})

# Abreviaturas con `/` que SON parte del rol y no separadores de roles
# distintos. Si splitteamos por `/` ingenuamente, "UI/UX Designer" se
# rompe en ["UI", "UX Designer"] y perdemos el rol. Las protegemos
# temporalmente antes del split.
_PROTECTED_SLASH_TERMS: tuple[str, ...] = (
    "UI/UX",
    "UX/UI",
    "AI/ML",
    "ML/AI",
    "I/O",
    "B2B/B2C",
    "B2C/B2B",
    "Pre/Post",
    "Front/Back",
    "Back/Front",
)

# Separadores que indican multi-rol en el `professional_title` del user
# ("Designer, Developer y Artist" / "Designer / Developer | Artist").
# El `/` se incluye porque después de proteger _PROTECTED_SLASH_TERMS lo
# que queda son slash que sí separan roles distintos.
_PRIMARY_ROLE_SPLIT_RE = re.compile(r"[,/|]|\sand\s|\sy\s", re.IGNORECASE)


def _extract_primary_role(title: str) -> str:
    """Devuelve el rol principal de un `professional_title` posiblemente
    multi-rol.

    Sin esto, perfiles con título largo ("UI/UX Designer/Industrial
    designer/expert in 3d, augmented reality and animation") generan
    9+ tokens en `_calc_title_score` — la fórmula `overlap/user_tokens`
    los penaliza tanto que NI siquiera una oferta de "Diseñador UI/UX
    Senior" llega al 60% de match. Tomar solo el primer rol baja los
    user_tokens a 3-4 y el matching vuelve a ser realista.

    Estrategia: split por separadores estándar (`,`, `|`, ` and `,
    ` y `, `/`), tomar el primer fragmento no vacío. Las abreviaciones
    con slash que son parte de un rol (UI/UX, AI/ML, etc.) se protegen
    antes del split para no quebrar incorrectamente.

    >>> _extract_primary_role('UI/UX Designer/Industrial designer/expert in 3d')
    'UI/UX Designer'
    >>> _extract_primary_role('Senior Backend Developer')
    'Senior Backend Developer'
    >>> _extract_primary_role('Data Scientist, ML Engineer y AI Researcher')
    'Data Scientist'
    >>> _extract_primary_role('')
    ''
    """
    if not title or not title.strip():
        return ""

    # Proteger abreviaturas con slash que NO separan roles. Reemplazo
    # case-insensitive pero recordamos la ortografía original para
    # restaurar al final.
    protected = title
    placeholders: list[tuple[str, str]] = []
    for i, term in enumerate(_PROTECTED_SLASH_TERMS):
        placeholder = f"__PROT{i}__"
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        match = pattern.search(protected)
        if match:
            placeholders.append((placeholder, match.group(0)))
            protected = pattern.sub(placeholder, protected)

    parts = _PRIMARY_ROLE_SPLIT_RE.split(protected)
    primary = next((p.strip() for p in parts if p.strip()), title.strip())

    for placeholder, original in placeholders:
        primary = primary.replace(placeholder, original)
    return primary

# Equivalencias bidireccionales para rol/función. Sin esto, un cargo
# "Desarrollador Full Stack" no matchearía con jobs titulados "Full
# Stack Developer" (palabras compartidas: full, stack — pierde el rol).
_TITLE_SYNONYMS: dict[str, str] = {
    "desarrollador": "developer",
    "desarrolladora": "developer",
    "developer": "developer",
    "programador": "developer",
    "programadora": "developer",
    "dev": "developer",
    "ingeniero": "engineer",
    "ingeniera": "engineer",
    "engineer": "engineer",
    "diseñador": "designer",
    "diseñadora": "designer",
    "designer": "designer",
    "analista": "analyst",
    "analyst": "analyst",
    "arquitecto": "architect",
    "arquitecta": "architect",
    "architect": "architect",
    "lider": "lead",
    "líder": "lead",
    "lead": "lead",
    "senior": "senior",
    "sr": "senior",
    "junior": "junior",
    "jr": "junior",
    "ssr": "semi-senior",
}


def _tokenize_title(title: str) -> set[str]:
    """Saca stopwords, normaliza sinónimos rol/función y devuelve un set."""
    if not title:
        return set()
    # Reemplazar todo lo que no sea alfanumérico/espacio/acento por espacio
    cleaned = re.sub(r"[^\w\sáéíóúñ]+", " ", title.lower(), flags=re.UNICODE)
    tokens = set()
    for raw in cleaned.split():
        raw = raw.strip()
        if not raw or raw in _TITLE_STOPWORDS:
            continue
        tokens.add(_TITLE_SYNONYMS.get(raw, raw))
    return tokens


def _calc_title_score(job_title: str, user_title: str) -> int:
    """Mide qué tan bien el cargo del job calza con el cargo del usuario.

    Recall sobre el cargo del usuario: ¿qué fracción de las palabras
    significativas del cargo del usuario aparecen en el título del job?
    Recall (no precisión) porque el título del job suele tener palabras
    extra (seniority, modalidad) que no son ruido para el match —
    "Senior Full Stack Developer Remote" sigue siendo un match para
    "Full Stack Developer".
    """
    user_tokens = _tokenize_title(user_title)
    if not user_tokens:
        return 0
    job_tokens = _tokenize_title(job_title)
    overlap = user_tokens & job_tokens
    return round((len(overlap) / len(user_tokens)) * 100)


class JobMatchingService:
    """Servicio para matching de ofertas con perfiles de usuario"""

    @staticmethod
    def calculate_match_percentage(
        job_keywords: list[str],
        user_skills: list[str],
        use_semantic: bool = False,
        job_title: str | None = None,
        user_title: str | None = None,
    ) -> dict[str, any]:
        """
        Calcula el porcentaje de match entre keywords de job y skills de usuario.

        Las skills se normalizan vía `common.skills_taxonomy.normalize` antes
        de comparar — así `React.js` y `react` cuentan como la misma skill.

        Args:
            job_keywords: Lista de keywords del trabajo
            user_skills: Lista de skills del usuario
            use_semantic: Si True, usa similaridad semántica con NLP
            job_title: Título del job (opcional, habilita scoring combinado)
            user_title: Cargo profesional del usuario (opcional)

        Returns:
            Dict con matched_skills, missing_skills, match_percentage.
            Cuando se pasan `job_title` y `user_title` también incluye
            `title_score` y `skill_score` para diagnóstico.
        """
        # Normalizar (lowercase + strip + aliases del taxonomía)
        job_keywords_clean = [normalize(kw) for kw in job_keywords if kw.strip()]
        user_skills_clean = [normalize(skill) for skill in user_skills if skill.strip()]

        # Calcular skills que coinciden (matching exacto)
        matched_skills = [kw for kw in job_keywords_clean if kw in user_skills_clean]
        missing_skills = [kw for kw in job_keywords_clean if kw not in user_skills_clean]

        # Matching semántico opcional para las skills faltantes
        if use_semantic and missing_skills:
            semantic_matches = JobMatchingService._find_semantic_matches(
                missing_skills, user_skills_clean
            )
            matched_skills.extend(semantic_matches)
            missing_skills = [s for s in missing_skills if s not in semantic_matches]

        skill_score = (
            round((len(matched_skills) / len(job_keywords_clean)) * 100)
            if job_keywords_clean
            else 0
        )

        # Modo legacy: sin info de título → comportamiento original (solo skills).
        # Preserva backward-compat con consumidores que todavía no pasan títulos.
        if not job_title or not user_title:
            return {
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "match_percentage": skill_score,
            }

        # Normalizamos el title del usuario al rol PRINCIPAL antes de
        # calcular el score. Sin esto, perfiles multi-rol ("UI/UX
        # Designer/Industrial designer/expert in 3d") generan tantos
        # user_tokens que ninguna oferta real llega al 60% (incluso una
        # oferta perfecta de "Diseñador UI/UX" saca 33%). Ver el
        # docstring de `_extract_primary_role` para el racional completo.
        # El job_title NO se normaliza — los títulos de ofertas son por
        # diseño un único rol, agregar más overhead no aporta.
        normalized_user_title = _extract_primary_role(user_title)
        title_score = _calc_title_score(job_title, normalized_user_title)

        if not job_keywords_clean:
            # Descripción vaga sin stack listado — confiamos en el título
            # solo, capado a 70% para reservar 100% a evidencia completa.
            combined = min(title_score, 70)
        else:
            # Pesos: 60% título / 40% skills. El título es el indicador
            # de rol; las skills sin contexto de rol ruidean fácil.
            combined = round(0.6 * title_score + 0.4 * skill_score)

        return {
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "match_percentage": combined,
            "title_score": title_score,
            "skill_score": skill_score,
        }

    @staticmethod
    def enrich_with_match(
        offers,
        user_profile: UserProfile,
    ) -> None:
        """Asigna `match_percentage`, `matched_skills` y `missing_skills` a
        cada oferta in-place. No filtra — solo enriquece para que el
        serializer pueda mostrar el badge en cualquier listing.

        Si el usuario no tiene skills definidas, los atributos quedan
        con defaults (0% / [] / keywords del job como missing).
        """
        user_skills = (user_profile.skills or "").split(",")
        user_title = user_profile.professional_title or ""
        for job in offers:
            job_keywords = (job.keywords or "").split(",")
            match_data = JobMatchingService.calculate_match_percentage(
                job_keywords,
                user_skills,
                job_title=job.title,
                user_title=user_title,
            )
            job.matched_skills = match_data["matched_skills"]
            job.missing_skills = match_data["missing_skills"]
            job.match_percentage = match_data["match_percentage"]

    @staticmethod
    def filter_jobs_by_skills(
        jobs: QuerySet[JobOffer], user_profile: UserProfile, min_match_percentage: int = 25
    ) -> list[JobOffer]:
        """
        Filtra jobs por match combinado (cargo + skills) y porcentaje mínimo.

        El umbral default bajó a 25% (era 50%) para acompañar la nueva
        fórmula combinada: un job vago con título matcheado puede caer
        en ~30-42% y antes se filtraba.

        Args:
            jobs: QuerySet de JobOffer
            user_profile: Perfil del usuario
            min_match_percentage: Porcentaje mínimo de match (default: 25)

        Returns:
            Lista de JobOffer filtrados y enriquecidos con datos de match
        """
        # Sin skills ni título no hay nada con qué matchear — devolvemos []
        # para evitar inundar al usuario con la DB entera.
        if not user_profile.skills and not user_profile.professional_title:
            return []

        user_skills = (user_profile.skills or "").split(",")
        user_title = user_profile.professional_title or ""
        filtered_jobs = []

        for job in jobs:
            # A diferencia del legacy, NO saltamos jobs sin keywords —
            # el título alone puede levantarlos por encima del umbral.
            job_keywords = (job.keywords or "").split(",")
            match_data = JobMatchingService.calculate_match_percentage(
                job_keywords,
                user_skills,
                job_title=job.title,
                user_title=user_title,
            )

            if match_data["match_percentage"] >= min_match_percentage:
                job.matched_skills = match_data["matched_skills"]
                job.missing_skills = match_data["missing_skills"]
                job.match_percentage = match_data["match_percentage"]
                filtered_jobs.append(job)

        filtered_jobs.sort(key=lambda x: x.match_percentage, reverse=True)
        return filtered_jobs

    @staticmethod
    def _find_semantic_matches(
        missing_skills: list[str], user_skills: list[str], threshold: float = 0.8
    ) -> list[str]:
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
                similarity = NLPService.calculate_text_similarity(missing_skill, user_skill)
                if similarity >= threshold:
                    semantic_matches.append(missing_skill)
                    break

        return semantic_matches

    @staticmethod
    def get_top_matched_jobs(
        user_profile: UserProfile, limit: int = 10, use_cache: bool = True
    ) -> list[JobOffer]:
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
        cache_key = f"top_jobs_user_{user_profile.user.id}_limit_{limit}"

        if use_cache:
            cached_results = cache.get(cache_key)
            if cached_results:
                return cached_results

        all_jobs = JobOffer.objects.all()
        filtered_jobs = JobMatchingService.filter_jobs_by_skills(
            all_jobs,
            user_profile,
            min_match_percentage=20,  # Umbral más bajo para top matches
        )

        result = filtered_jobs[:limit]

        if use_cache:
            cache.set(cache_key, result, 600)

        return result
