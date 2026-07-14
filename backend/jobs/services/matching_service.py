"""
Servicio para matching de ofertas de trabajo con perfiles de usuario.

Diseño del scoring (Julio 2026 — rewrite honesto):
El score anterior (60% titulo / 40% skills + boost de vertical) infla el
match cuando el titulo calza pero faltan skills. Un user Fullstack
Developer veia "Desarrollador FullStack (Middle)" al 90% con solo 4 de
13 skills — sensacion de engano. El nuevo scoring es explicito:

    match = max(0, title_score - skill_penalty)

Componentes:

1) title_score — cascada de casos, no un simple recall de tokens:

   - Tokens iguales (post-normalizacion): 100
   - user_tokens ⊆ job_tokens (user es subset del job): 90
     Ejemplo: user "Fullstack Developer" vs job "Fullstack Developer .NET"
   - job_tokens ⊆ user_tokens (job mas generico): 85
     Ejemplo: user "Senior Backend Developer" vs job "Backend Developer"
   - Overlap parcial de tokens: (overlap/user_tokens) * 80
     Cap a 80 porque el rol no calza del todo.
   - Sin overlap pero misma categoria macro (agro/tech/etc): 45
     Piso vertical que rescata perfiles como Fabio (zootecnista) viendo
     ofertas de "Medico Veterinario" — pero YA NO a 90%, ahora honesto.
   - Sin overlap ni categoria compartida: 15
     Ultimo recurso; el offer aparece bien al fondo del feed.

2) skill_penalty — proporcional al tamano del stack pedido:

   - Si el job no lista skills (job_keywords vacio): penalty = 0
     No penalizamos por falta de datos del portal.
   - Si el job lista skills: penalty = (missing / total) * 100
     Cada skill faltante vale (100/N). Un job con 3 skills penaliza
     33.3% por cada faltante; con 12 skills, 8.3% por cada faltante.

3) Combinacion:  match = max(0, title_score - skill_penalty)

Ejemplos verificados:
  - Walter (Fullstack Developer · python, angular, node) vs...
    - "Fullstack Developer" sin skills → title 100, penalty 0 → 100
    - "Fullstack Developer .NET" · [.net, docker, mongo] → title 90,
      penalty 100 → 0 (le faltan las 3)
    - "Desarrollador FullStack (Middle)" · 13 skills, 4 matched →
      title 90, penalty 69 → 21 (el famoso 90% ahora es honesto)
  - Fabio zootecnista vs "Medico Veterinario" sin skills → title 45
    (piso vertical), penalty 0 → 45 (pasa el threshold del feed).

Threshold del feed subio de 25% a 40% para acompanar esta formula —
matches por debajo de 40 son ruido, no relevancia.
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
# ("Designer, Developer y Artist" / "Designer / Developer | Artist" /
# "Zootecnista - Peluquero canino"). Incluimos guiones (-, –, —) y middle
# dot (·) SOLO cuando vienen rodeados de espacios — sino "Front-End
# Developer" o "Full-Stack" se partirían incorrectamente.
# El `/` se incluye porque después de proteger _PROTECTED_SLASH_TERMS lo
# que queda son slash que sí separan roles distintos.
_PRIMARY_ROLE_SPLIT_RE = re.compile(
    r"[,/|]|\sand\s|\sy\s|\s[-–—·]\s", re.IGNORECASE
)


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
    # ---- Roles tech / ingeniería ----
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
    # ---- Roles de gestión / mando ----
    "lider": "lead",
    "líder": "lead",
    "lead": "lead",
    "coordinador": "coordinator",
    "coordinadora": "coordinator",
    "coordinator": "coordinator",
    "gerente": "manager",
    "manager": "manager",
    "supervisor": "supervisor",
    "supervisora": "supervisor",
    "director": "director",
    "directora": "director",
    "jefe": "chief",
    "jefa": "chief",
    "chief": "chief",
    # ---- Roles asistencia / soporte ----
    "asistente": "assistant",
    "assistant": "assistant",
    "auxiliar": "assistant",
    # ---- Roles expertos / consultores ----
    "especialista": "specialist",
    "specialist": "specialist",
    "consultor": "consultant",
    "consultora": "consultant",
    "consultant": "consultant",
    "asesor": "advisor",
    "asesora": "advisor",
    "advisor": "advisor",
    "advisora": "advisor",
    # ---- Roles técnicos / operativos ----
    "técnico": "technician",
    "tecnico": "technician",
    "técnica": "technician",
    "tecnica": "technician",
    "technician": "technician",
    "operador": "operator",
    "operadora": "operator",
    "operator": "operator",
    "operario": "operator",
    "operaria": "operator",
    # ---- Educación ----
    "profesor": "teacher",
    "profesora": "teacher",
    "docente": "teacher",
    "maestro": "teacher",
    "maestra": "teacher",
    "teacher": "teacher",
    "educador": "teacher",
    "educadora": "teacher",
    # ---- Oficios comunes ----
    "mecánico": "mechanic",
    "mecanico": "mechanic",
    "mecánica": "mechanic",
    "mecanica": "mechanic",
    "mechanic": "mechanic",
    "conductor": "driver",
    "conductora": "driver",
    "chofer": "driver",
    "driver": "driver",
    # ---- Salud (traducciones más comunes) ----
    "médico": "doctor",
    "medico": "doctor",
    "doctor": "doctor",
    "enfermero": "nurse",
    "enfermera": "nurse",
    "nurse": "nurse",
    # ---- Ventas ----
    "vendedor": "salesperson",
    "vendedora": "salesperson",
    "salesperson": "salesperson",
    # ---- Seniority (no traducir, alias) ----
    "senior": "senior",
    "sr": "senior",
    "junior": "junior",
    "jr": "junior",
    "ssr": "semi-senior",
}


# Compound words tech con dos formas comunes en la industria: concatenada
# ("fullstack") y separada/hifenada ("full stack" / "full-stack"). Los
# portales las mezclan sin criterio — algunos anuncios usan una, otros
# la otra, y a veces la misma empresa varía entre listings. Sin este
# mapeo, un user "FullStack Developer" no matcheaba con "Full Stack
# Developer" del mismo listing → title_score cae de 100 a 40, la oferta
# ranquea en el fondo o queda por debajo del threshold del feed.
# Reportado por el user 2026-07-13 con capturas del email de LinkedIn:
# ofertas de Wompi/Fracttal/GFT/etc no aparecian porque el matcher las
# calificaba al 40% cuando eran perfect fit.
_COMPOUND_WORD_CANON: dict[str, str] = {
    # ---- Tech ----
    # `full stack` / `full-stack` → `fullstack`
    "full stack": "fullstack",
    "full-stack": "fullstack",
    # `front end` / `front-end` → `frontend`
    "front end": "frontend",
    "front-end": "frontend",
    # `back end` / `back-end` → `backend`
    "back end": "backend",
    "back-end": "backend",
    # DevOps y variantes
    "dev ops": "devops",
    "dev-ops": "devops",
    # `sys admin` / `sys-admin` / `system administrator` → `sysadmin`
    "sys admin": "sysadmin",
    "sys-admin": "sysadmin",
    "system administrator": "sysadmin",
    "systems administrator": "sysadmin",
    # `tech lead` / `technical lead` → `techlead`
    "tech lead": "techlead",
    "technical lead": "techlead",
    # `machine learning` → `machinelearning`. NOTA: dejamos `ml` por
    # separado — es abreviatura común pero también significa mililitros
    # y aparece en títulos no-ML. Si el user pone "ML Engineer" queda
    # como {ml, engineer} y el matcher usa piso vertical de tech.
    "machine learning": "machinelearning",
    "deep learning": "deeplearning",
    # `data science` / `data scientist` — la palabra "data" sola es muy
    # genérica; canonicalizamos el par para que funcione como rol.
    "data science": "datascience",
    # Java Script como palabra separada (raro pero pasa)
    "java script": "javascript",
    # Product Owner / Product Manager — dos palabras muy comunes
    "product owner": "productowner",
    "product manager": "productmanager",
    "project manager": "projectmanager",

    # ---- HR ----
    # RRHH / Recursos Humanos / HR / Human Resources → `rrhh`
    "recursos humanos": "rrhh",
    "human resources": "rrhh",
    "talent acquisition": "talentacquisition",
    "adquisicion de talento": "talentacquisition",
    "adquisición de talento": "talentacquisition",

    # ---- Ventas ----
    "customer success": "customersuccess",
    "customer service": "customerservice",
    "atencion al cliente": "customerservice",
    "atención al cliente": "customerservice",
    "servicio al cliente": "customerservice",
    "business development": "businessdevelopment",
    "desarrollo de negocios": "businessdevelopment",
    "account manager": "accountmanager",
    "key account": "keyaccount",
    "cuenta clave": "keyaccount",

    # ---- Operations / Logistica ----
    "supply chain": "supplychain",
    "cadena de suministro": "supplychain",
    "cadena de abastecimiento": "supplychain",
    "cadena de valor": "supplychain",

    # ---- Marketing ----
    "community manager": "communitymanager",
    "social media": "socialmedia",
    "digital marketing": "digitalmarketing",
    "marketing digital": "digitalmarketing",
    "growth marketing": "growthmarketing",
    "growth hacker": "growthmarketing",

    # ---- Salud ----
    "medico general": "medico",
    "médico general": "medico",
    "medico veterinario": "veterinario",
    "médico veterinario": "veterinario",

    # UI/UX ya se maneja en `_PROTECTED_SLASH_TERMS` — no necesita
    # canonicalizar acá.
}


def _canonicalize_compounds(text: str) -> str:
    """Reemplaza compound words separadas por su forma concatenada.

    Aplicado SOBRE el título en lowercase antes del split de tokens.
    Case-insensitive porque el input ya viene en lowercase. Ordenado
    por longitud desc para que `front-end` matchee antes que `end`
    solo.
    """
    for variant, canonical in sorted(
        _COMPOUND_WORD_CANON.items(), key=lambda kv: -len(kv[0])
    ):
        text = text.replace(variant, canonical)
    return text


def _tokenize_title(title: str) -> set[str]:
    """Saca stopwords, normaliza sinónimos rol/función y devuelve un set."""
    if not title:
        return set()
    # Canonicalizar compound words ANTES del split — sin esto,
    # "full stack" se rompe en {"full", "stack"} y pierde match con
    # "fullstack" que Walter escribió como una palabra.
    canonicalized = _canonicalize_compounds(title.lower())
    # Reemplazar todo lo que no sea alfanumérico/espacio/acento por espacio
    cleaned = re.sub(r"[^\w\sáéíóúñ]+", " ", canonicalized, flags=re.UNICODE)
    tokens = set()
    for raw in cleaned.split():
        raw = raw.strip()
        if not raw or raw in _TITLE_STOPWORDS:
            continue
        tokens.add(_TITLE_SYNONYMS.get(raw, raw))
    return tokens


# Piso vertical: cuando titulo del job y del user no comparten tokens
# pero pertenecen a la misma categoria macro (tech, agro, etc.). Reemplaza
# el "boost a 90%" del scoring anterior con un piso mas honesto — Fabio
# (zootecnista) sigue viendo ofertas de "Medico Veterinario" pero al 45%,
# no al 90%.
_TITLE_SCORE_SAME_VERTICAL = 45

# Piso ultimo: sin overlap ni vertical compartido. El offer aparece bien
# al fondo del ranking, casi seguro se filtra por el threshold del feed.
_TITLE_SCORE_NO_MATCH = 15


def _calc_title_score(
    job_title: str,
    user_title: str,
    job_category: str | None = None,
    user_category: str | None = None,
) -> int:
    """Calcula el score de titulo por cascada de casos:

    1. Tokens iguales → 100
    2. user ⊆ job (rol especifico dentro de titulo mas largo) → 90
    3. job ⊆ user (job mas generico que el rol del user) → 85
    4. Overlap parcial → (overlap/user_tokens) * 80
    5. Sin overlap pero misma categoria macro → 45 (piso vertical)
    6. Sin overlap ni categoria → 15 (piso minimo)

    La cascada refleja la logica que un humano usa para juzgar "que tan
    bien calza este rol": exacto > subset > overlap > mismo area > nada.
    """
    user_tokens = _tokenize_title(user_title)
    if not user_tokens:
        return 0
    job_tokens = _tokenize_title(job_title)
    if not job_tokens:
        return 0

    if user_tokens == job_tokens:
        return 100

    if user_tokens.issubset(job_tokens):
        # Rol del user esta contenido tal cual en el titulo del job —
        # el job es una variante mas especifica del mismo rol.
        return 90

    if job_tokens.issubset(user_tokens):
        # Job es una version mas generica del rol del user (raro pero
        # valido: user "Senior Backend Developer" vs job "Backend
        # Developer"). Ligeramente menor que 90 porque el user perdio
        # especificidad (seniority, etc.) al matchear.
        return 85

    overlap = user_tokens & job_tokens
    if overlap:
        # Overlap parcial. Cap a 80 — nunca llega a 90 (reservado a
        # coincidencias subset o exactas).
        return round((len(overlap) / len(user_tokens)) * 80)

    # Sin overlap directo. Piso vertical si comparten categoria macro.
    same_vertical = (
        user_category is not None
        and user_category != "general"
        and job_category == user_category
    )
    if same_vertical:
        return _TITLE_SCORE_SAME_VERTICAL
    return _TITLE_SCORE_NO_MATCH


class JobMatchingService:
    """Servicio para matching de ofertas con perfiles de usuario"""

    @staticmethod
    def calculate_match_percentage(
        job_keywords: list[str],
        user_skills: list[str],
        use_semantic: bool = False,
        job_title: str | None = None,
        user_title: str | None = None,
        job_category: str | None = None,
        user_category: str | None = None,
    ) -> dict[str, any]:
        """
        Calcula el porcentaje de match entre un job y un user.

        Formula:  match = max(0, title_score - skill_penalty)
        Detalles completos en el docstring del modulo.

        Args:
            job_keywords: Lista de keywords del job
            user_skills: Lista de skills del user
            use_semantic: Si True, usa similaridad semantica NLP
            job_title: Titulo del job (habilita cascada de titulo)
            user_title: Cargo del user
            job_category: Categoria macro del job (tech, agro, etc.)
            user_category: Categoria macro del user

        Returns:
            Dict con matched_skills, missing_skills, match_percentage.
            Cuando hay job_title y user_title tambien incluye
            title_score, skill_score y skill_penalty para diagnostico.
        """
        # Normalizar (lowercase + strip + aliases del taxonomia)
        job_keywords_clean = [normalize(kw) for kw in job_keywords if kw.strip()]
        user_skills_clean = [normalize(skill) for skill in user_skills if skill.strip()]

        # Skills matcheadas / faltantes (exact match sobre normalized).
        matched_skills = [kw for kw in job_keywords_clean if kw in user_skills_clean]
        missing_skills = [kw for kw in job_keywords_clean if kw not in user_skills_clean]

        # Matching semantico opcional para las skills faltantes.
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

        # Modo legacy: sin info de titulo → comportamiento original (solo skills).
        # Preserva backward-compat con consumidores que todavia no pasan titulos.
        if not job_title or not user_title:
            return {
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "match_percentage": skill_score,
            }

        # Normalizamos el user title al rol PRINCIPAL antes de calcular
        # el title_score. Sin esto, perfiles multi-rol ("UI/UX Designer/
        # Industrial designer/expert in 3d") generan tantos tokens que
        # ninguna oferta real pasa el threshold. Ver docstring de
        # `_extract_primary_role`.
        normalized_user_title = _extract_primary_role(user_title)
        title_score = _calc_title_score(
            job_title,
            normalized_user_title,
            job_category=job_category,
            user_category=user_category,
        )

        # Skill penalty proporcional al total de skills del job. Si el
        # job no lista skills → no penalizamos (no castigar por falta de
        # datos del portal). Con skills → cada faltante vale (100/N).
        if job_keywords_clean:
            missing_count = len(missing_skills)
            total_count = len(job_keywords_clean)
            skill_penalty = round((missing_count / total_count) * 100)
        else:
            skill_penalty = 0

        combined = max(0, title_score - skill_penalty)

        return {
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "match_percentage": combined,
            "title_score": title_score,
            "skill_score": skill_score,
            "skill_penalty": skill_penalty,
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
        from users.services.profession_classifier import infer_profession_category

        user_skills = (user_profile.skills or "").split(",")
        user_title = user_profile.professional_title or ""
        user_category = infer_profession_category(user_title)
        for job in offers:
            job_keywords = (job.keywords or "").split(",")
            match_data = JobMatchingService.calculate_match_percentage(
                job_keywords,
                user_skills,
                job_title=job.title,
                user_title=user_title,
                job_category=getattr(job, "category", None),
                user_category=user_category,
            )
            job.matched_skills = match_data["matched_skills"]
            job.missing_skills = match_data["missing_skills"]
            job.match_percentage = match_data["match_percentage"]

    @staticmethod
    def filter_jobs_by_skills(
        jobs: QuerySet[JobOffer], user_profile: UserProfile, min_match_percentage: int = 40
    ) -> list[JobOffer]:
        """
        Filtra jobs por match combinado y porcentaje minimo.

        El umbral default subio a 40% (era 25%) para acompanar la formula
        nueva (title_score - skill_penalty). Con la formula anterior un
        job vago sin skills salia en 30-42%; con la nueva, matches por
        debajo de 40 son ruido, no relevancia. El piso vertical (45)
        garantiza que perfiles como Fabio (zootecnista) sigan viendo
        ofertas de "Medico Veterinario" — al 45, no al 90.

        Args:
            jobs: QuerySet de JobOffer
            user_profile: Perfil del usuario
            min_match_percentage: Porcentaje minimo de match (default: 40)

        Returns:
            Lista de JobOffer filtrados y enriquecidos con datos de match
        """
        # Sin skills ni título no hay nada con qué matchear — devolvemos []
        # para evitar inundar al usuario con la DB entera.
        if not user_profile.skills and not user_profile.professional_title:
            return []

        from users.services.profession_classifier import infer_profession_category

        user_skills = (user_profile.skills or "").split(",")
        user_title = user_profile.professional_title or ""
        user_category = infer_profession_category(user_title)
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
                job_category=getattr(job, "category", None),
                user_category=user_category,
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
            # Mismo threshold que el feed (40): con el matcher nuevo,
            # matches < 40 son ruido no relevancia.
            min_match_percentage=40,
        )

        result = filtered_jobs[:limit]

        if use_cache:
            cache.set(cache_key, result, 600)

        return result
