"""Contenido inicial del portafolio `walternightsdev`.

Se usa desde la data migration 0002 para bootstrap del sitio. Una vez
seedado, el editor admin sobreescribe estos valores en DB — este archivo
NO es la fuente de verdad en runtime.

Espejo del contenido que hoy vive en:
  frontend/src/app/portfolio/i18n/{es,en}.json

Si los JSONs del frontend divergen, este archivo no se auto-actualiza:
sirve solo para deployments limpios sin registro previo.
"""

from __future__ import annotations


WALTERNIGHTSDEV_ES: dict = {
    "meta": {
        "title": "Walter Nights — Fullstack Engineer",
        "description": (
            "Fullstack Engineer construyendo plataformas SaaS con IA aplicada. "
            "Portafolio de proyectos personales y empresariales."
        ),
    },
    "sidebar": {
        "role": "Fullstack Engineer",
        "tagline": "Construyo plataformas SaaS con IA aplicada.",
        "nav": {
            "about": "Sobre mí",
            "experience": "Experiencia",
            "projects": "Proyectos",
            "contact": "Contacto",
        },
        "techLabel": "Stack",
        "socials": [
            {"id": "github", "url": "https://github.com/WalterNights"},
            {"id": "linkedin", "url": "https://www.linkedin.com/in/walternightsdev/"},
            {"id": "email", "url": "mailto:walter@geeks5g.com"},
        ],
        "tech": [
            "python", "django", "fastapi", "typescript", "angular", "react",
            "nextjs", "nestjs", "postgresql", "redis", "docker", "gcp",
        ],
    },
    "hero": {
        "eyebrow": "WALTER NIGHTS ─ FULLSTACK ENGINEER",
        "titleTop": "Ideas que",
        "titleBottom": "corren en producción.",
        "subtitle": (
            "Diseño y construyo sistemas SaaS end-to-end — desde el modelo de "
            "datos hasta la interfaz — con foco en IA aplicada, integraciones "
            "y velocidad de entrega."
        ),
        "cta": {"projects": "Ver proyectos", "contact": "Contactarme"},
    },
    "about": {
        "eyebrow": "SOBRE MÍ",
        "title": "Un ingeniero que piensa en el negocio antes que en el código.",
        "paragraphs": [
            (
                "Trabajo como Fullstack Engineer en <strong>Geeks5G</strong>, donde "
                "lidero y construyo plataformas SaaS que combinan automatización, IA "
                "y operaciones diarias reales — desde marketing digital hasta "
                "contabilidad y educación."
            ),
            (
                "Me interesa la intersección donde el producto se cruza con la "
                "ingeniería: entender por qué el negocio necesita una feature antes "
                "de decidir cómo implementarla. Cuando algo se puede simplificar en "
                "tres líneas, prefiero eso a inventar una abstracción para seis "
                "casos hipotéticos."
            ),
            (
                "Fuera del trabajo mantengo proyectos personales que me obligan a "
                "probar stacks nuevos — así es como llego a los repos con criterio "
                "y no solo con curiosidad."
            ),
        ],
    },
    "experience": {
        "eyebrow": "EXPERIENCIA",
        "title": "Trayectoria",
        "items": [
            {
                "period": "2023 — PRESENTE",
                "role": "Fullstack Engineer",
                "company": "Geeks5G",
                "url": "https://geeks5g.com",
                "description": (
                    "Construyo y mantengo las plataformas internas de la agencia "
                    "— RankTitan, OptimAds, Google Services API — cubriendo "
                    "backend, frontend, infra y decisiones de producto. Integro "
                    "APIs de Google (Ads, GMB, Analytics), automatizo procesos "
                    "de local SEO y trabajo con LLMs para generación de "
                    "contenido y análisis."
                ),
                "stack": [
                    "Python", "Django", "FastAPI", "Angular", "React",
                    "Next.js", "PostgreSQL", "OpenAI", "Google APIs",
                ],
            }
        ],
    },
    "projects": {
        "eyebrow": "PROYECTOS",
        "title": "Cosas que construí",
        "note": (
            "Mezcla de proyectos personales y trabajo empresarial. Algunos "
            "son cerrados por NDA — muestro capturas y descripción, sin "
            "código público."
        ),
        "filters": {"all": "Todos", "personal": "Personales", "enterprise": "Empresariales"},
        "labels": {
            "personal": "Personal",
            "enterprise": "Empresarial",
            "live": "En producción",
            "private": "Privado",
            "wip": "En desarrollo",
            "viewSite": "Ver sitio",
            "viewRepo": "Ver repo",
            "screenshot": "Captura pendiente",
        },
        "items": [
            {
                "id": "ranktitan",
                "name": "RankTitan",
                "kind": "enterprise",
                "status": "live",
                "description": (
                    "Sistema de posicionamiento para Google My Business, Google "
                    "Ads y Local SEO. Automatiza auditorías de fichas GMB, "
                    "gestiona campañas y genera reportes de ranking por keyword."
                ),
                "stack": ["Python", "FastAPI", "Angular", "PostgreSQL", "Google APIs", "OpenAI"],
                "href": "",
                "repo": "",
            },
            {
                "id": "tax-bookkeeping",
                "name": "Tax Bookkeeping",
                "kind": "enterprise",
                "status": "live",
                "description": (
                    "Sistema de manejo de pagos y cuentas bancarias para pymes. "
                    "Concilia transacciones, genera plan de cuentas y produce "
                    "reportes fiscales listos para el contador."
                ),
                "stack": ["Node.js", "NestJS", "Next.js", "PostgreSQL", "Prisma", "Stripe"],
                "href": "",
                "repo": "",
            },
            {
                "id": "google-services",
                "name": "Google Services API",
                "kind": "enterprise",
                "status": "live",
                "description": (
                    "API central que orquesta automatizaciones sobre Google Ads, "
                    "GMB, Local SEO y Analytics. Es la base sobre la que corren "
                    "RankTitan y OptimAds."
                ),
                "stack": ["Python", "FastAPI", "Google Ads API", "GMB API", "Analytics"],
                "href": "",
                "repo": "",
            },
            {
                "id": "skiltak",
                "name": "SkilTak",
                "kind": "personal",
                "status": "live",
                "description": (
                    "Plataforma personal para centralizar la búsqueda de empleo: "
                    "agrega ofertas de múltiples portales, matchea con el perfil "
                    "vía IA y genera CVs y cover letters a medida."
                ),
                "stack": ["Python", "Django", "Angular", "PostgreSQL", "OpenAI"],
                "href": "https://skiltak.com",
                "repo": "",
            },
            {
                "id": "optimads",
                "name": "OptimAds",
                "kind": "enterprise",
                "status": "live",
                "description": (
                    "Sistema de monitoreo de campañas de ads y CRM de análisis "
                    "de local SEO. Detecta anomalías de gasto y sugiere ajustes "
                    "de estrategia con IA."
                ),
                "stack": ["Python", "FastAPI", "Next.js", "React", "PostgreSQL"],
                "href": "",
                "repo": "",
            },
            {
                "id": "estudiant",
                "name": "Estudiant",
                "kind": "enterprise",
                "status": "wip",
                "description": (
                    "Plataforma de gestión académica y campus virtual para "
                    "entidades educativas. Cubre matrícula, oferta académica, "
                    "calendario, evaluaciones y comunicación docente-alumno."
                ),
                "stack": ["Node.js", "NestJS", "Angular", "PostgreSQL"],
                "href": "",
                "repo": "",
            },
            {
                "id": "archtomatic",
                "name": "Archtomatic",
                "kind": "enterprise",
                "status": "wip",
                "description": (
                    "Plataforma para arquitectos: inventario, cotizaciones, "
                    "presupuestos y generación de renders y planos a partir de "
                    "descripciones en lenguaje natural."
                ),
                "stack": ["Python", "FastAPI", "Next.js", "OpenAI", "Blender"],
                "href": "",
                "repo": "",
            },
        ],
    },
    "contact": {
        "eyebrow": "CONTACTO",
        "title": "¿Trabajamos juntos?",
        "body": (
            "Estoy abierto a colaboraciones, proyectos freelance y "
            "conversaciones sobre producto. La forma más rápida de llegarme "
            "es por email."
        ),
        "cta": "Escribirme",
        "email": "walter@geeks5g.com",
    },
    "footer": {
        "built": "Diseñado y construido por Walter Nights.",
        "stack": "Angular · Tailwind · sin frameworks de más.",
    },
    "langToggle": {"label": "Idioma", "es": "ES", "en": "EN"},
}


WALTERNIGHTSDEV_EN: dict = {
    "meta": {
        "title": "Walter Nights — Fullstack Engineer",
        "description": (
            "Fullstack Engineer building AI-powered SaaS platforms. "
            "A portfolio of personal and enterprise projects."
        ),
    },
    "sidebar": {
        "role": "Fullstack Engineer",
        "tagline": "I build AI-powered SaaS platforms.",
        "nav": {
            "about": "About",
            "experience": "Experience",
            "projects": "Projects",
            "contact": "Contact",
        },
        "techLabel": "Stack",
        "socials": [
            {"id": "github", "url": "https://github.com/WalterNights"},
            {"id": "linkedin", "url": "https://www.linkedin.com/in/walternightsdev/"},
            {"id": "email", "url": "mailto:walter@geeks5g.com"},
        ],
        "tech": [
            "python", "django", "fastapi", "typescript", "angular", "react",
            "nextjs", "nestjs", "postgresql", "redis", "docker", "gcp",
        ],
    },
    "hero": {
        "eyebrow": "WALTER NIGHTS ─ FULLSTACK ENGINEER",
        "titleTop": "Ideas that",
        "titleBottom": "run in production.",
        "subtitle": (
            "I design and build SaaS systems end-to-end — from the data "
            "model to the interface — with a focus on applied AI, "
            "integrations, and shipping speed."
        ),
        "cta": {"projects": "View projects", "contact": "Get in touch"},
    },
    "about": {
        "eyebrow": "ABOUT",
        "title": "An engineer who thinks about the business before the code.",
        "paragraphs": [
            (
                "I work as a Fullstack Engineer at <strong>Geeks5G</strong>, "
                "where I lead and build SaaS platforms that mix automation, "
                "AI, and real daily operations — from digital marketing to "
                "bookkeeping and education."
            ),
            (
                "I like the intersection where product meets engineering: "
                "understanding why the business needs a feature before "
                "deciding how to implement it. When something can be "
                "simplified into three lines, I prefer that over inventing "
                "an abstraction for six hypothetical cases."
            ),
            (
                "Outside of work I keep personal projects that force me to "
                "try new stacks — that's how I show up to a repo with "
                "judgment, not just curiosity."
            ),
        ],
    },
    "experience": {
        "eyebrow": "EXPERIENCE",
        "title": "Track record",
        "items": [
            {
                "period": "2023 — PRESENT",
                "role": "Fullstack Engineer",
                "company": "Geeks5G",
                "url": "https://geeks5g.com",
                "description": (
                    "Build and maintain the agency's internal platforms — "
                    "RankTitan, OptimAds, Google Services API — covering "
                    "backend, frontend, infra, and product decisions. "
                    "Integrate Google APIs (Ads, GMB, Analytics), automate "
                    "local SEO processes, and work with LLMs for content "
                    "generation and analysis."
                ),
                "stack": [
                    "Python", "Django", "FastAPI", "Angular", "React",
                    "Next.js", "PostgreSQL", "OpenAI", "Google APIs",
                ],
            }
        ],
    },
    "projects": {
        "eyebrow": "PROJECTS",
        "title": "Things I've built",
        "note": (
            "A mix of personal projects and enterprise work. Some are "
            "closed under NDA — I show screenshots and description, no "
            "public code."
        ),
        "filters": {"all": "All", "personal": "Personal", "enterprise": "Enterprise"},
        "labels": {
            "personal": "Personal",
            "enterprise": "Enterprise",
            "live": "Live",
            "private": "Private",
            "wip": "In progress",
            "viewSite": "View site",
            "viewRepo": "View repo",
            "screenshot": "Screenshot pending",
        },
        "items": [
            {
                "id": "ranktitan",
                "name": "RankTitan",
                "kind": "enterprise",
                "status": "live",
                "description": (
                    "SEO ranking platform for Google My Business, Google "
                    "Ads, and Local SEO. Automates GMB profile audits, "
                    "manages campaigns, and generates keyword ranking reports."
                ),
                "stack": ["Python", "FastAPI", "Angular", "PostgreSQL", "Google APIs", "OpenAI"],
                "href": "",
                "repo": "",
            },
            {
                "id": "tax-bookkeeping",
                "name": "Tax Bookkeeping",
                "kind": "enterprise",
                "status": "live",
                "description": (
                    "Payment and bank account management system for SMBs. "
                    "Reconciles transactions, generates chart of accounts, "
                    "and produces accountant-ready tax reports."
                ),
                "stack": ["Node.js", "NestJS", "Next.js", "PostgreSQL", "Prisma", "Stripe"],
                "href": "",
                "repo": "",
            },
            {
                "id": "google-services",
                "name": "Google Services API",
                "kind": "enterprise",
                "status": "live",
                "description": (
                    "Central API orchestrating automation across Google "
                    "Ads, GMB, Local SEO, and Analytics. The foundation "
                    "RankTitan and OptimAds run on."
                ),
                "stack": ["Python", "FastAPI", "Google Ads API", "GMB API", "Analytics"],
                "href": "",
                "repo": "",
            },
            {
                "id": "skiltak",
                "name": "SkilTak",
                "kind": "personal",
                "status": "live",
                "description": (
                    "Personal platform to centralize the job hunt: "
                    "aggregates offers from multiple portals, matches them "
                    "against the profile via AI, and generates tailored "
                    "CVs and cover letters."
                ),
                "stack": ["Python", "Django", "Angular", "PostgreSQL", "OpenAI"],
                "href": "https://skiltak.com",
                "repo": "",
            },
            {
                "id": "optimads",
                "name": "OptimAds",
                "kind": "enterprise",
                "status": "live",
                "description": (
                    "Ad campaign monitoring system and CRM for local SEO "
                    "analysis. Detects spend anomalies and suggests strategy "
                    "adjustments with AI."
                ),
                "stack": ["Python", "FastAPI", "Next.js", "React", "PostgreSQL"],
                "href": "",
                "repo": "",
            },
            {
                "id": "estudiant",
                "name": "Estudiant",
                "kind": "enterprise",
                "status": "wip",
                "description": (
                    "Academic management platform and virtual campus for "
                    "educational institutions. Covers enrollment, course "
                    "catalog, calendar, evaluations, and teacher-student "
                    "communication."
                ),
                "stack": ["Node.js", "NestJS", "Angular", "PostgreSQL"],
                "href": "",
                "repo": "",
            },
            {
                "id": "archtomatic",
                "name": "Archtomatic",
                "kind": "enterprise",
                "status": "wip",
                "description": (
                    "Platform for architects: inventory, quotes, budgets, "
                    "and generation of renders and blueprints from "
                    "natural-language descriptions."
                ),
                "stack": ["Python", "FastAPI", "Next.js", "OpenAI", "Blender"],
                "href": "",
                "repo": "",
            },
        ],
    },
    "contact": {
        "eyebrow": "CONTACT",
        "title": "Want to work together?",
        "body": (
            "I'm open to collaborations, freelance projects, and product "
            "conversations. The fastest way to reach me is by email."
        ),
        "cta": "Send an email",
        "email": "walter@geeks5g.com",
    },
    "footer": {
        "built": "Designed and built by Walter Nights.",
        "stack": "Angular · Tailwind · nothing more than needed.",
    },
    "langToggle": {"label": "Language", "es": "ES", "en": "EN"},
}
