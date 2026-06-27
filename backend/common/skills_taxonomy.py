"""Taxonomía única de skills para todo el proyecto.

Fuente única de verdad para:
  - Matching de ofertas con perfiles (`JobMatchingService`)
  - Extracción de keywords del scraper (`jobs.adapters.scrapers.base.extract_keywords`)
  - Detección de skills en CVs (`users.services.nlp_service`)

Cobertura multi-profesión: tech, diseño, marketing, ventas, finanzas,
RRHH, operaciones, salud, educación, legal, oficio profesional general.
Antes de este split la taxonomía era ~200 entradas todas tech, lo que
dejaba el matching en 0% para cualquier perfil no-dev. Sin esto, el
scraper guarda ofertas con `keywords=""` y el matching cae a fallback
de título-solo — usable pero pierde precisión.

Reglas para agregar términos:
  - Lowercase, sin acentos en aliases (sí en canónicos donde aplique)
  - Una entrada por concepto; variantes ortográficas van a ALIASES
  - Si pensás "esto solo aparece en industria X muy rara", probablemente
    no vale el ruido — la taxonomía debe seleccionar términos con peso
    de matching real, no exhaustividad enciclopédica
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Hard skills — nombres canónicos en minúsculas, sin puntos ni símbolos.
# Organizado por vertical profesional. Cada sección busca cubrir el ~80%
# de las menciones más frecuentes en job posts LATAM.
# ---------------------------------------------------------------------------
HARD_SKILLS: frozenset[str] = frozenset(
    {
        # ============ TECH ============
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
        "deep learning",
        "nlp",
        "computer vision",
        # Blockchain
        "blockchain",
        "solidity",
        "web3",

        # ============ DISEÑO ============
        # Tools (UI/UX + gráfico)
        "figma",
        "sketch",
        "photoshop",
        "illustrator",
        "xd",
        "indesign",
        "after effects",
        "premiere",
        "lightroom",
        "canva",
        "framer",
        "invision",
        "miro",
        "zeplin",
        "principle",
        "blender",
        # 3D / VFX / motion (mercado creativo LATAM crece rápido — perfiles
        # tipo "diseñador 3D + animación" no son tech-dev pero generaban
        # 0% match porque ninguna de estas herramientas estaba en taxonomy)
        "cinema 4d",
        "maya",
        "unreal engine",
        "unity",
        "houdini",
        "zbrush",
        "substance painter",
        "substance designer",
        "nuke",
        "davinci resolve",
        "final cut pro",
        # Video edition (separado de premiere/after effects que ya estaban)
        "video editing",
        # Animación
        "2d animation",
        "3d animation",
        # VFX / composición / extended reality
        "visual effects",
        "augmented reality",
        "virtual reality",
        # Métodos / outputs
        "wireframes",
        "prototyping",
        "user research",
        "usability testing",
        "design system",
        "design thinking",
        "ux writing",
        "responsive design",
        "accessibility",
        "wcag",
        "branding",
        "brand identity",
        "typography",
        "color theory",
        "motion graphics",
        "3d modeling",
        "illustration",
        "vector illustration",
        "logo design",
        "content creation",

        # ============ MARKETING DIGITAL ============
        # Ads platforms
        "google ads",
        "meta ads",
        "facebook ads",
        "instagram ads",
        "tiktok ads",
        "linkedin ads",
        "twitter ads",
        "amazon ads",
        "youtube ads",
        # Analytics
        "google analytics",
        "ga4",
        "google tag manager",
        "hotjar",
        "mixpanel",
        "amplitude",
        "looker",
        "data studio",
        # SEO/SEM
        "seo",
        "sem",
        "semrush",
        "ahrefs",
        "moz",
        "search console",
        "keyword research",
        "link building",
        "on-page seo",
        "off-page seo",
        # Email & automation
        "mailchimp",
        "hubspot",
        "marketo",
        "activecampaign",
        "klaviyo",
        "sendgrid",
        "convertkit",
        "email marketing",
        "marketing automation",
        # Social / content
        "social media",
        "community management",
        "content marketing",
        "copywriting",
        "storytelling",
        "branding",
        "influencer marketing",
        "buffer",
        "hootsuite",
        "later",
        "metricool",
        # Ecommerce
        "ecommerce",
        "woocommerce",
        "shopify",
        "magento",
        "vtex",
        "prestashop",
        "tiendanube",
        # CRM marketing
        "salesforce marketing cloud",
        "pardot",
        "growth hacking",
        "inbound marketing",
        "performance marketing",

        # ============ VENTAS / COMERCIAL ============
        "crm",
        "salesforce",
        "hubspot crm",
        "pipedrive",
        "zoho crm",
        "monday sales",
        "outreach",
        "salesloft",
        "linkedin sales navigator",
        "apollo",
        "prospección",
        "prospeccion",
        "cold calling",
        "cold email",
        "lead generation",
        "lead qualification",
        "sdr",
        "bdr",
        "account executive",
        "key account",
        "b2b",
        "b2c",
        "ventas consultivas",
        "negociación",
        "negociacion",
        "cierre de ventas",
        "post venta",
        "customer success",
        "spin selling",
        "challenger sale",
        "pipeline",
        "forecast",
        "kpi",
        "okr",

        # ============ FINANZAS / CONTABILIDAD ============
        "excel avanzado",
        "google sheets",
        "macros",
        "vba",
        "sap",
        "oracle ebs",
        "siigo",
        "contpaq",
        "world office",
        "nominaplus",
        "quickbooks",
        "xero",
        "netsuite",
        "tally",
        "ifrs",
        "niif",
        "gaap",
        "us gaap",
        "consolidación",
        "consolidacion",
        "presupuesto",
        "presupuestos",
        "forecasting",
        "modelado financiero",
        "valoración",
        "valoracion",
        "due diligence",
        "tesorería",
        "tesoreria",
        "conciliación bancaria",
        "conciliacion bancaria",
        "facturación electrónica",
        "facturacion electronica",
        "contabilidad",
        "auditoría",
        "auditoria",
        "impuestos",
        "renta",
        "iva",
        "retención",
        "retencion",
        "nómina",
        "nomina",
        "payroll",
        "análisis financiero",
        "analisis financiero",
        "controlling",
        "fp&a",

        # ============ RRHH / PEOPLE OPS ============
        "reclutamiento",
        "selección",
        "seleccion",
        "headhunting",
        "sourcing",
        "linkedin recruiter",
        "bamboohr",
        "workday",
        "successfactors",
        "personio",
        "factorial",
        "rippling",
        "greenhouse",
        "lever",
        "ats",
        "onboarding",
        "offboarding",
        "people analytics",
        "compensación",
        "compensacion",
        "beneficios",
        "engagement",
        "clima organizacional",
        "cultura organizacional",
        "desarrollo organizacional",
        "capacitación",
        "capacitacion",
        "training",
        "evaluación de desempeño",
        "evaluacion de desempeno",
        "succession planning",
        "dei",
        "diversidad e inclusión",
        "diversidad e inclusion",

        # ============ OPERACIONES / SUPPLY CHAIN ============
        "lean",
        "six sigma",
        "kaizen",
        "5s",
        "tpm",
        "smed",
        "value stream mapping",
        "erp",
        "sap mm",
        "sap pp",
        "sap wm",
        "oracle scm",
        "supply chain",
        "logística",
        "logistica",
        "inventarios",
        "compras",
        "abastecimiento",
        "almacenes",
        "wms",
        "tms",
        "demand planning",
        "s&op",
        "iso 9001",
        "iso 14001",
        "iso 45001",
        "haccp",
        "calidad",
        "control de calidad",
        "qaqc",
        "mantenimiento",
        "productividad",
        "operaciones",

        # ============ SALUD ============
        "soap",  # nota: tambien existe como protocolo tech — aceptable
        "historia clínica",
        "historia clinica",
        "hce",
        "rip",
        "cums",
        "siau",
        "habilitación",
        "habilitacion",
        "enfermería",
        "enfermeria",
        "auxiliar de enfermería",
        "auxiliar de enfermeria",
        "medicina general",
        "epidemiología",
        "epidemiologia",
        "salud ocupacional",
        "sst",
        "bioseguridad",
        "farmacovigilancia",

        # ============ EDUCACIÓN ============
        "lms",
        "moodle",
        "canvas",
        "blackboard",
        "google classroom",
        "microsoft teams for education",
        "pedagogía",
        "pedagogia",
        "didáctica",
        "didactica",
        "currículo",
        "curriculo",
        "evaluación educativa",
        "evaluacion educativa",
        "metodologías activas",
        "metodologias activas",
        "aprendizaje basado en proyectos",
        "edtech",
        "diseño instruccional",
        "diseno instruccional",

        # ============ LEGAL ============
        "derecho civil",
        "derecho laboral",
        "derecho comercial",
        "derecho penal",
        "derecho administrativo",
        "derecho tributario",
        "litigios",
        "litigation",
        "compliance",
        "gobierno corporativo",
        "contratos",
        "fusiones y adquisiciones",
        "propiedad intelectual",
        "protección de datos",
        "proteccion de datos",
        "gdpr",
        "habeas data",
        "lawyaw",
        "case management",

        # ============ OFFICE / PROFESIONAL GENERAL ============
        "excel",
        "word",
        "powerpoint",
        "outlook",
        "google workspace",
        "google docs",
        "google slides",
        "office 365",
        "microsoft 365",
        "sharepoint",
        "onedrive",
        "drive",
        "zoom",
        "teams",
        "slack",
        "asana",
        "monday",
        "trello",  # también está abajo en project; ALIASES dedupa
        # Project & agile (transversal — aplica tech y no tech)
        "agile",
        "lean",  # mismo nombre que método ops; ok un solo canónico
        "scrum",
        "kanban",
        "jira",
        "confluence",
        "notion",
        "clickup",
        "trello",
        "uml",
        "bpmn",
        "waterfall",
        "pmp",
        "prince2",
        "gestión de proyectos",
        "gestion de proyectos",
        "project management",

        # ============ IDIOMAS ============
        "inglés",
        "ingles",
        "español",
        "espanol",
        "portugués",
        "portugues",
        "francés",
        "frances",
        "alemán",
        "aleman",
        "italiano",
        "mandarín",
        "mandarin",
        "japonés",
        "japones",
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
        "comunicacion",
        "trabajo en equipo",
        "resolución de problemas",
        "resolucion de problemas",
        "adaptabilidad",
        "pensamiento crítico",
        "pensamiento critico",
        "proactividad",
        "gestión del tiempo",
        "gestion del tiempo",
        "orientación al cliente",
        "orientacion al cliente",
        "orientación al detalle",
        "orientacion al detalle",
        "empatía",
        "empatia",
        "creatividad",
        "innovación",
        "innovacion",
        "autonomía",
        "autonomia",
        "atención al detalle",
        "atencion al detalle",
        "tolerancia a la presión",
        "tolerancia a la presion",
    }
)

# ---------------------------------------------------------------------------
# Aliases — variante en texto libre → nombre canónico.
# Indispensable porque las ofertas mezclan "React.js", "ReactJS", "react",
# y sin esto el matching contaba como tres skills distintas.
# ---------------------------------------------------------------------------
ALIASES: dict[str, str] = {
    # ===== Tech: Frontend =====
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "next.js": "next",
    "nextjs": "next",
    "nuxt.js": "nuxt",
    "nuxtjs": "nuxt",
    "angular.js": "angular",
    "angularjs": "angular",
    "svelte.js": "svelte",
    "sveltejs": "svelte",
    "html5": "html",
    "css3": "css",
    # ===== Tech: Backend =====
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
    # ===== Tech: Databases =====
    "postgres": "postgresql",
    "mongo": "mongodb",
    # ===== Tech: Cloud =====
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    # ===== Tech: APIs / protocols =====
    "restful": "rest",
    "api rest": "rest",
    # ===== Diseño =====
    "adobe xd": "xd",
    "adobe photoshop": "photoshop",
    "adobe illustrator": "illustrator",
    "adobe indesign": "indesign",
    "adobe after effects": "after effects",
    "adobe premiere": "premiere",
    "adobe lightroom": "lightroom",
    "ui design": "design system",
    "ux design": "user research",
    # 3D / VFX — abreviaciones comunes y nombres alternos
    "c4d": "cinema 4d",
    "ue5": "unreal engine",
    "ue4": "unreal engine",
    "unreal": "unreal engine",
    "autodesk maya": "maya",
    "3ds max": "maya",  # cercano - en LATAM se cita junto y muchos perfiles cubren ambos
    "vfx": "visual effects",
    "efectos visuales": "visual effects",
    "compositing": "visual effects",
    # Animación — plural y traducción
    "2d animations": "2d animation",
    "3d animations": "3d animation",
    "animación 2d": "2d animation",
    "animacion 2d": "2d animation",
    "animación 3d": "3d animation",
    "animacion 3d": "3d animation",
    # Realidad extendida — abreviaciones y traducciones
    "ar": "augmented reality",
    "vr": "virtual reality",
    "realidad aumentada": "augmented reality",
    "realidad virtual": "virtual reality",
    "mixed reality": "augmented reality",  # cercano, agrupamos
    "xr": "augmented reality",
    # Video — traducción y nombres alternos
    "video edition": "video editing",
    "edición de video": "video editing",
    "edicion de video": "video editing",
    "video editor": "video editing",
    # Diseño / branding — variantes
    "vector illustrations": "vector illustration",
    "ilustración vectorial": "vector illustration",
    "ilustracion vectorial": "vector illustration",
    "identidad de marca": "brand identity",
    "creación de contenido": "content creation",
    "creacion de contenido": "content creation",
    # ===== Marketing =====
    "facebook ads manager": "facebook ads",
    "meta business": "meta ads",
    "google analytics 4": "ga4",
    "tag manager": "google tag manager",
    "adwords": "google ads",
    "search engine optimization": "seo",
    "search engine marketing": "sem",
    # ===== Ventas =====
    "hubspot sales": "hubspot crm",
    "sales navigator": "linkedin sales navigator",
    "kpis": "kpi",
    "okrs": "okr",
    # ===== Finanzas =====
    "ms excel": "excel",
    "microsoft excel": "excel",
    "ifrs/niif": "ifrs",
    "us-gaap": "us gaap",
    # ===== Idiomas (variantes con acento) =====
    "ingles avanzado": "inglés",
    "inglés avanzado": "inglés",
    "english": "inglés",
    "portuguese": "portugués",
    "french": "francés",
    "german": "alemán",
}


def normalize(skill: str) -> str:
    """Normaliza un nombre de skill: lowercase, strip, aplica aliases.

    Si después de aplicar ALIASES el término sigue terminando en `.js`
    o `js` y la versión sin sufijo está en HARD_SKILLS, devolvemos la
    versión sin sufijo. Cubre el caso "Tailwind.js", "Express.js" y
    cualquier framework JS nuevo que aparezca antes de que lo agreguemos
    explícitamente a ALIASES.

    >>> normalize('  React.js ')
    'react'
    >>> normalize('Angular.js')
    'angular'
    >>> normalize('Node.JS')
    'node'
    >>> normalize('python')
    'python'
    """
    cleaned = skill.strip().lower()
    aliased = ALIASES.get(cleaned, cleaned)
    if aliased not in HARD_SKILLS and aliased not in SOFT_SKILLS:
        # Fallback: strippear .js / js trailing si el resto matchea.
        for suffix in (".js", "js"):
            if aliased.endswith(suffix):
                stem = aliased[: -len(suffix)].rstrip(".")
                if stem and stem in HARD_SKILLS:
                    return stem
    return aliased


def all_recognizable() -> frozenset[str]:
    """Todos los strings que podemos detectar en texto libre.

    Útil para el scraper, que recorre cada keyword conocida buscando
    coincidencias en la descripción de la oferta. Combina canónicas
    + aliases para no perder variantes.
    """
    return HARD_SKILLS | SOFT_SKILLS | frozenset(ALIASES.keys())
