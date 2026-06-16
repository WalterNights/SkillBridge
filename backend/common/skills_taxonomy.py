"""Taxonomía única de skills para todo el proyecto.

Fuente única de verdad para:
  - Matching de ofertas con perfiles (`JobMatchingService`)
  - Extracción de keywords del scraper (`jobs.adapters.scrapers.base.extract_keywords`)
  - Detección de skills en CVs (`users.services.nlp_service`)

Reemplaza las fuentes anteriores (eliminadas en este commit):
  - `jobs/keywords.py` (COMMON_KEYWORDS, ~90)
  - Set inline `technical_skills` en `nlp_service.py:89`
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Hard skills — nombres canónicos en minúsculas, sin puntos ni símbolos.
# ---------------------------------------------------------------------------
HARD_SKILLS: frozenset[str] = frozenset(
    {
        # Frontend core
        "html",
        "css",
        "sass",
        "less",
        "javascript",
        "typescript",
        "react",
        "angular",
        "vue",
        "next",
        "nuxt",
        "svelte",
        "tailwind",
        "bootstrap",
        "material ui",
        "chakra ui",
        # Backend languages & frameworks
        "python",
        "django",
        "flask",
        "fastapi",
        "node",
        "express",
        "nest",
        "java",
        "spring",
        "csharp",
        "dotnet",
        "aspnet",
        "blazor",
        "php",
        "laravel",
        "symfony",
        "codeigniter",
        "ruby",
        "rails",
        "go",
        "rust",
        "scala",
        "kotlin",
        # Cloud & DevOps
        "aws",
        "azure",
        "gcp",
        "heroku",
        "digitalocean",
        "vercel",
        "netlify",
        "docker",
        "kubernetes",
        "helm",
        "git",
        "github",
        "gitlab",
        "bitbucket",
        "jenkins",
        "circleci",
        "travisci",
        "ci/cd",
        "terraform",
        "ansible",
        "vagrant",
        "linux",
        "bash",
        "powershell",
        # API & protocols
        "rest",
        "graphql",
        "soap",
        "websocket",
        "json",
        "xml",
        # Architecture
        "microservices",
        "monolith",
        "serverless",
        "event-driven",
        "rabbitmq",
        "kafka",
        "mqtt",
        # Testing
        "jest",
        "mocha",
        "chai",
        "cypress",
        "playwright",
        "selenium",
        "postman",
        "junit",
        "pytest",
        "unittest",
        # Databases
        "sql",
        "mysql",
        "postgresql",
        "sqlite",
        "oracle",
        "mssql",
        "mongodb",
        "cassandra",
        "firebase",
        "redis",
        "elasticsearch",
        # Data & AI
        "pandas",
        "numpy",
        "scikit-learn",
        "tensorflow",
        "keras",
        "pytorch",
        "openai",
        "bigquery",
        "power bi",
        "tableau",
        "machine learning",
        "data science",
        # Project & agile
        "agile",
        "lean",
        "scrum",
        "kanban",
        "jira",
        "confluence",
        "notion",
        "clickup",
        "trello",
        "uml",
        "bpmn",
        # Design & marketing
        "figma",
        "photoshop",
        "illustrator",
        "xd",
        "seo",
        "sem",
        "ecommerce",
        "woocommerce",
        "shopify",
        # Office
        "excel",
        "word",
        "powerpoint",
        # Blockchain
        "blockchain",
        "solidity",
        "web3",
    }
)

# ---------------------------------------------------------------------------
# Soft skills — mantenidas separadas porque son un dominio distinto:
# no se miden con keywords técnicos y no se mezclan en el matching técnico.
# ---------------------------------------------------------------------------
SOFT_SKILLS: frozenset[str] = frozenset(
    {
        "liderazgo",
        "comunicación",
        "trabajo en equipo",
        "resolución de problemas",
        "adaptabilidad",
        "pensamiento crítico",
        "proactividad",
        "gestión del tiempo",
    }
)

# ---------------------------------------------------------------------------
# Aliases — variante en texto libre → nombre canónico.
# Antes de fusionar fuentes había keywords como `react.js` en una lista y
# `react` en otra, lo que provocaba match-percentage falsos.
# ---------------------------------------------------------------------------
ALIASES: dict[str, str] = {
    # Frontend
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "next.js": "next",
    "nextjs": "next",
    "nuxt.js": "nuxt",
    "nuxtjs": "nuxt",
    "html5": "html",
    "css3": "css",
    # Backend
    "node.js": "node",
    "nodejs": "node",
    "nest.js": "nest",
    "nestjs": "nest",
    "spring boot": "spring",
    "c#": "csharp",
    ".net": "dotnet",
    ".net core": "dotnet",
    "asp.net": "aspnet",
    "ruby on rails": "rails",
    "golang": "go",
    # Databases
    "postgres": "postgresql",
    "mongo": "mongodb",
    # Cloud
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    # APIs / protocols
    "restful": "rest",
    "api rest": "rest",
    # Tools
    "adobe xd": "xd",
    "adobe photoshop": "photoshop",
    "adobe illustrator": "illustrator",
}


def normalize(skill: str) -> str:
    """Normaliza un nombre de skill: lowercase, strip, aplica aliases.

    >>> normalize('  React.js ')
    'react'
    >>> normalize('Node.JS')
    'node'
    >>> normalize('python')
    'python'
    """
    cleaned = skill.strip().lower()
    return ALIASES.get(cleaned, cleaned)


def all_recognizable() -> frozenset[str]:
    """Todos los strings que podemos detectar en texto libre.

    Útil para el scraper, que recorre cada keyword conocida buscando
    coincidencias en la descripción de la oferta. Combina canónicas
    + aliases para no perder variantes.
    """
    return HARD_SKILLS | SOFT_SKILLS | frozenset(ALIASES.keys())
