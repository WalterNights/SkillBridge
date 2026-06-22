"""Clasifica el `professional_title` de un usuario en una categoría
profesional macro. Usado para filtrar tips relevantes y, a futuro,
adaptar el feed de ofertas.

Determinístico, sin AI: regex sobre keywords del título. Para la mayoría
de los títulos cae correctamente. Cuando un título es ambiguo o nuevo,
devolvemos `'general'` — el endpoint de tips trata `'general'` igual que
"sin profesión detectada" y devuelve solo tips con `scope='all'`.

Las categorías matchean 1:1 con los valores de `Tip.PROFESSION_SCOPE_CHOICES`.
"""

from __future__ import annotations

import re

ProfessionCategory = str  # 'tech' | 'design' | 'marketing' | ...

# Orden importa: el primer match gana. Más específicos arriba para no
# confundir, ej. "UX designer" no debería caer en design genérico si
# tenemos un grupo más fino — pero por ahora el granularidad es macro.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "tech",
        re.compile(
            r"\b(developer|engineer|programmer|programador|desarrollador|"
            r"devops|sysadmin|sre|qa|tester|architect|arquitecto|fullstack|"
            r"frontend|backend|mobile|ios|android|data scientist|"
            r"data engineer|data analyst|machine learning|ml engineer|"
            r"product owner|technical lead|tech lead|cto|cio)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "design",
        re.compile(
            r"\b(diseñador|disenador|designer|ux|ui|ux/ui|product designer|"
            r"graphic designer|motion designer|illustrator|ilustrador|"
            r"industrial designer|director de arte|art director)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "marketing",
        re.compile(
            r"\b(marketing|marketer|seo|sem|community manager|content|"
            r"copywriter|growth|brand|digital strategist|"
            r"social media|publicidad|advertising|performance)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "sales",
        re.compile(
            r"\b(ventas|vendedor|comercial|sales|account executive|"
            r"account manager|business development|sdr|bdr|"
            r"key account|customer success|kam|representante comercial)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "finance",
        re.compile(
            r"\b(contador|contadora|accountant|cfo|finance|finanzas|"
            r"financial|auditor|auditoría|auditoria|tesorero|controller|"
            r"analista financiero|treasury|fp&a|impuestos|tax)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "hr",
        re.compile(
            r"\b(rrhh|recursos humanos|hr|human resources|reclutador|"
            r"reclutadora|recruiter|talent|talent acquisition|"
            r"people|payroll|nominas|chro|gente y cultura)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "operations",
        re.compile(
            r"\b(operations|operaciones|supply chain|cadena de suministro|"
            r"logística|logistica|warehouse|almacén|almacen|"
            r"production manager|jefe de producción|jefe de produccion|"
            r"coo|director de operaciones|planning|planificación|"
            r"planificacion)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "health",
        re.compile(
            r"\b(médico|medico|doctor|enfermero|enfermera|nurse|"
            r"odontólogo|odontologo|psicólogo|psicologo|fisioterapeuta|"
            r"nutricionista|farmacéutico|farmaceutico|bioanalista|"
            r"radiólogo|radiologo|terapeuta)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "education",
        re.compile(
            r"\b(docente|profesor|profesora|teacher|maestra|maestro|"
            r"educador|educadora|tutor|coordinador académico|"
            r"coordinador academico|rector|director académico|"
            r"director academico)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "legal",
        re.compile(
            r"\b(abogado|abogada|lawyer|jurídico|juridico|legal counsel|"
            r"paralegal|notario|notaria|compliance officer|jurista)\b",
            re.IGNORECASE,
        ),
    ),
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
