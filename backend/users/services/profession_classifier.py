"""Clasifica el `professional_title` de un usuario en una categoría
profesional macro. Usado para filtrar tips relevantes y para taggear
ofertas (la categoría queda en `JobOffer.category` y el feed filtra
por la categoría del user).

Determinístico, sin AI: regex sobre keywords del título. Para la mayoría
de los títulos cae correctamente. Cuando un título es ambiguo o nuevo,
devolvemos `'general'`.

Plurales en español: usamos `_word_with_plurals` para que cada keyword
matchee también su plural común sin tener que listar las dos formas.
Bug reportado 2026-06-27: "Empresas agrícolas" / "Zootecnistas" /
"Veterinarios" caían en `general` porque el patrón solo tenía la
forma singular y `\b` en el word boundary excluye la `s` final.

Las categorías matchean 1:1 con los valores de `Tip.PROFESSION_SCOPE_CHOICES`.
"""

from __future__ import annotations

import re

ProfessionCategory = str  # 'tech' | 'design' | 'marketing' | ...


def _word_with_plurals(word: str) -> str:
    """Devuelve el regex de `word` aceptando su plural común en español.

    Reglas:
      - Si la palabra YA termina en 's' (ej. 'sales', 'finanzas',
        'operaciones'), no agregamos sufijo.
      - Si la palabra tiene ≤2 caracteres alfanuméricos (ej. 'hr', 'ui',
        'qa'), NO agregamos plural — son siglas/abreviaturas que casi
        siempre matcheean falsos positivos. Bug real (2026-06-29):
        "FT 42 Hrs" en titulos retail matcheaba "hr" + plural "hrs",
        clasificando ofertas operario como HR. Para abreviaturas
        cortas, exigir el word boundary exacto sin plural.
      - Si termina en vocal (a/e/i/o/u): aceptar `s?` opcional
        ('diseñador' → 'diseñador'; 'designer' → 'designers').
      - Si termina en consonante: aceptar `(?:es|s)?` opcional
        ('agrícola' → 'agrícolas'; 'contador' → 'contadores'). Incluir
        `s` directo cubre formas anglicistas ('developer' → 'developers').
      - Si termina en símbolo (`/`, `&`, etc.) no agregamos plural —
        casos como `ux/ui`, `fp&a` no tienen plural natural.
    """
    base = re.escape(word)
    if not word:
        return base
    if word.endswith("s"):
        return base
    if len(word) <= 2:
        return base
    last = word[-1].lower()
    if not last.isalpha():
        return base
    if last in "aeiouáéíóú":
        return f"{base}s?"
    return f"{base}(?:es|s)?"


def _build_pattern(words: tuple[str, ...]) -> re.Pattern[str]:
    """Compila un patrón regex case-insensitive con word boundaries que
    matchea cada `word` y sus plurales. El alternation usa `|` ordenado
    por LONGITUD DESCENDENTE para que `data scientist` matchee antes
    que `data` solo (regex es greedy pero el alternation evalúa orden)."""
    parts = sorted(words, key=len, reverse=True)
    flexible = [_word_with_plurals(w) for w in parts]
    return re.compile(r"\b(?:" + "|".join(flexible) + r")\b", re.IGNORECASE)


# Lista de palabras por categoría. Plurales se generan automáticamente
# en `_build_pattern` — solo listar la forma singular (o el plural fijo
# para términos que solo existen en plural, ej. "finanzas").
#
# Ambos géneros listados explícitamente (abogado + abogada) porque el
# helper solo genera plurales, no traduce género.
#
# Orden importa: el primer match gana. Más específicos arriba para no
# confundir; agro va ANTES que health para que "Médico Veterinario"
# matchee veterinaria (animal) y no salud humana.

_TECH_WORDS = (
    "developer", "engineer", "programmer", "programador", "programadora",
    "desarrollador", "desarrolladora", "devops", "sysadmin", "sre", "qa",
    "tester", "architect", "arquitecto", "arquitecta", "fullstack",
    "frontend", "backend", "mobile", "ios", "android",
    "data scientist", "data engineer", "data analyst",
    "machine learning", "ml engineer", "product owner",
    "technical lead", "tech lead", "cto", "cio",
    "ingeniero de sistemas", "ingeniera de sistemas",
    "ingeniero de software", "ingeniera de software",
    "ingeniero en sistemas", "ingeniera en sistemas",
    "ingeniero informático", "ingeniero informatico",
    "ingeniera informática", "ingeniera informatica",
    "ingeniero en computación", "ingeniero en computacion",
    "ingeniero de datos", "ingeniera de datos",
)

_DESIGN_WORDS = (
    "diseñador", "diseñadora", "disenador", "disenadora", "designer",
    "ux", "ui", "ux/ui", "product designer", "graphic designer",
    "motion designer", "illustrator", "ilustrador", "ilustradora",
    "industrial designer", "director de arte", "art director",
)

_MARKETING_WORDS = (
    "marketing", "marketer", "seo", "sem", "community manager",
    "content", "copywriter", "growth", "brand", "digital strategist",
    "social media", "publicidad", "advertising", "performance",
)

_SALES_WORDS = (
    "ventas", "vendedor", "vendedora", "comercial", "sales",
    "account executive", "account manager", "business development",
    "sdr", "bdr", "key account", "customer success", "kam",
    "representante comercial",
)

_FINANCE_WORDS = (
    "contador", "contadora", "accountant", "cfo", "finance", "finanzas",
    "financial", "auditor", "auditora", "auditoría", "auditoria",
    "tesorero", "tesorera", "controller", "analista financiero",
    "treasury", "fp&a", "impuestos", "tax",
)

_HR_WORDS = (
    "rrhh", "recursos humanos", "hr", "human resources",
    "reclutador", "reclutadora", "recruiter", "talent",
    "talent acquisition", "people", "payroll", "nominas", "chro",
    "gente y cultura",
)

_OPERATIONS_WORDS = (
    "operations", "operaciones", "supply chain", "cadena de suministro",
    "logística", "logistica", "warehouse", "almacén", "almacen",
    "production manager", "jefe de producción", "jefe de produccion",
    "coo", "director de operaciones", "planning", "planificación",
    "planificacion",
)

# 'agro' va ANTES que 'health' (ver docstring del módulo).
# Cubre TODO el universo animal/agropecuario: producción animal y vegetal,
# veterinaria (también docencia veterinaria — "veterinaria" matchea
# tanto el rol como el área), servicios para mascotas (peluquero/
# estilista/adiestrador canino), y agroindustria. Si un día separamos
# "mascotas/pet care" como categoría propia, los términos canino/felino
# se mueven a esa.
_AGRO_WORDS = (
    "zootecnista", "zootecnia",
    "veterinario", "veterinaria",
    "médico veterinario", "medico veterinario", "mvz",
    "agrónomo", "agrónoma", "agronomo", "agronoma",
    "agronomía", "agronomia",
    "ingeniero agrónomo", "ingeniero agronomo",
    "ingeniera agrónoma", "ingeniera agronoma",
    "ganadero", "ganadera", "ganadería", "ganaderia",
    "agricultor", "agricultora", "agrícola", "agricola",
    "agropecuario", "agropecuaria",
    "agroindustria", "agroindustrial",
    "avicultor", "avicultora", "avicultura",
    "porcicultor", "porcicultora", "porcicultura",
    "nutrición animal", "nutricion animal", "nutricionista animal",
    "producción animal", "produccion animal",
    "producción pecuaria", "produccion pecuaria",
    "fitomejorador", "agronegocios",
    # Servicios para mascotas / pet care
    "peluquero canino", "peluquera canina",
    "estilista canino", "estilista canina",
    "groomer",
    "adiestrador canino", "adiestradora canina",
    "entrenador canino", "entrenadora canina",
    "paseador de perros", "paseadora de perros",
    "cuidador de animales", "cuidadora de animales",
    "cuidador canino", "cuidadora canina",
    "criador", "criadora",
    "etólogo animal", "etologo animal",
    "auxiliar veterinario", "auxiliar veterinaria",
    "asistente veterinario", "asistente veterinaria",
)

_HEALTH_WORDS = (
    "médico", "medico", "doctor", "enfermero", "enfermera", "nurse",
    "odontólogo", "odontologo", "odontóloga", "odontologa",
    "psicólogo", "psicologo", "psicóloga", "psicologa",
    "fisioterapeuta", "nutricionista",
    "farmacéutico", "farmaceutico", "farmacéutica", "farmaceutica",
    "bioanalista", "radiólogo", "radiologo", "terapeuta",
)

_EDUCATION_WORDS = (
    "docente", "profesor", "profesora", "teacher", "maestra", "maestro",
    "educador", "educadora", "tutor", "tutora",
    "coordinador académico", "coordinador academico",
    "rector", "rectora",
    "director académico", "director academico",
)

_LEGAL_WORDS = (
    "abogado", "abogada", "lawyer", "jurídico", "juridico",
    "legal counsel", "paralegal", "notario", "notaria",
    "compliance officer", "jurista",
)

# Solo términos puramente administrativos — sino captura "Gerente
# Comercial" (debería ir a sales) o "Director de Operaciones".
_ADMIN_WORDS = (
    "administrador", "administradora", "administracion", "administración",
    "gerente general", "director general", "directora general", "ceo",
    "secretaria", "secretario", "recepcionista",
)

# Oficios concretos + servicios. Va al final por el mismo motivo que
# admin — "técnico" solo capturaría demasiado.
_TRADES_WORDS = (
    "plomero", "plomera", "electricista",
    "mecánico", "mecanico", "mecánica", "mecanica",
    "soldador", "soldadora",
    "carpintero", "carpintera", "albañil", "albanil",
    "pintor", "pintora", "cerrajero", "cerrajera",
    "técnico en refrigeración", "tecnico en refrigeracion",
    "técnico mecánico", "tecnico mecanico",
    "técnico electricista", "tecnico electricista",
    "técnico industrial", "tecnico industrial",
    "operario", "operaria",
    "conductor", "conductora", "chofer",
    "mensajero", "mensajera",
    "vigilante", "vigilancia", "guardia de seguridad",
    "servicios generales", "aseo", "limpieza",
    "jardinero", "jardinera",
)

# Admin tiene patrón especial: incluye comodines `\w*` para variantes
# como "asistente administrativ*" (asistente administrativo /
# administrativa). Eso no encaja en _build_pattern — lo definimos a mano.
_ADMIN_EXTRA_PATTERN = re.compile(
    r"\b(asistente administrativ\w*|auxiliar administrativ\w*|"
    r"jefe administrativ\w*|director administrativ\w*|"
    r"gerente administrativ\w*|coordinador administrativ\w*|"
    r"asistente ejecutiv\w*)\b",
    re.IGNORECASE,
)


_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tech", _build_pattern(_TECH_WORDS)),
    ("design", _build_pattern(_DESIGN_WORDS)),
    ("marketing", _build_pattern(_MARKETING_WORDS)),
    ("sales", _build_pattern(_SALES_WORDS)),
    ("finance", _build_pattern(_FINANCE_WORDS)),
    ("hr", _build_pattern(_HR_WORDS)),
    ("operations", _build_pattern(_OPERATIONS_WORDS)),
    # IMPORTANTE: 'agro' va ANTES que 'health' porque "Médico
    # Veterinario" matchea 'médico' del patrón health primero.
    ("agro", _build_pattern(_AGRO_WORDS)),
    ("health", _build_pattern(_HEALTH_WORDS)),
    ("education", _build_pattern(_EDUCATION_WORDS)),
    ("legal", _build_pattern(_LEGAL_WORDS)),
    # admin tiene dos patrones: el de palabras simples + el extra
    # con `\w*` para "asistente administrativ*" etc.
    ("admin", _build_pattern(_ADMIN_WORDS)),
    ("admin", _ADMIN_EXTRA_PATTERN),
    ("trades", _build_pattern(_TRADES_WORDS)),
]


def infer_profession_category(title: str | None) -> ProfessionCategory:
    """Mapea un título profesional libre a una categoría macro.

    Devuelve 'general' si el título es vacío o no matchea ningún patrón
    conocido. Eso permite que el endpoint de tips degrade limpio:
    'general' → solo tips con scope='all', sin filtro adicional.

    >>> infer_profession_category('Senior Backend Developer')
    'tech'
    >>> infer_profession_category('Diseñadora UX/UI')
    'design'
    >>> infer_profession_category('Community Manager')
    'marketing'
    >>> infer_profession_category('Contador Público')
    'finance'
    >>> infer_profession_category('')
    'general'
    >>> infer_profession_category(None)
    'general'
    """
    if not title:
        return "general"
    for category, pattern in _PATTERNS:
        if pattern.search(title):
            return category
    return "general"
