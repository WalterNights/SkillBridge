EDUCATION_KEYWORDS = [
    "universidad", "universitario", "formación académica", "educación",
    "título", "licenciatura", "ingeniería", "pregrado", "maestría",
    "doctorado", "tecnólogo", "tecnico", "estudios", "facultad", "carrera",
    "profesional en", "egresado", "grado", "especialización"
]

TITLE_KEYWORDS = [
    "Desarrollador de Software", "Desarrollador Web", "Ingeniero", "Analista", "Full Stack", "Backend", "Frontend", 
    "Developer", "Architect", "Programador", "Software Engineer"
]

SKILLS_KEYWORDS = [
    # Tecnologías
    "python", "java", "javascript", "typescript", "fetch", "jquery", "angular", "react",
    "vue", "node", "excpress", "django", "api rest", "flask", "spring", "git", "github", "html", "css",
    "sql", "mysql", "postgresql", "mongodb", "docker", "kubernetes",
    "aws", "azure", "linux", "bash", "graphql",

    # Habilidades blandas
    "liderazgo", "comunicación", "trabajo en equipo", "resolución de problemas",
    "adaptabilidad", "pensamiento crítico", "proactividad", "gestión del tiempo",

    # Herramientas
    "jira", "trello", "figma", "adobe xd", "photoshop", "postman"
]

PROFESSIONAL_RESUME_KEYWORDS = [
    "perfil profesional", "título profesional", "professional title", "ocupación", "cargo", "aspiración laboral",
    "resumen profesional", "resumen", "perfil", "professional profile", "professional summary"
]

EXPERIENCE_KEYWORDS = ["experiencia", "historial laboral", "trayectoria", "laboral"]

PHONE_KEYWORDS = ["teléfono", "celular", "número de contacto"]

LINKEDIN_KEYWORDS = ["linkedin"]

PORTFOLIO_KEYWORDS = ["portafolio", "portfolio"]

CITY_KEYWORDS = [
    "Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", 
    "Buenos Aires", "Madrid", "Barcelona", "Lima", "Santiago", "Quito", 
    "New York", "San Francisco", "London"
]

STOP_KEYWORDS = {
    "summary": EXPERIENCE_KEYWORDS + EDUCATION_KEYWORDS,
    "experience": EDUCATION_KEYWORDS + SKILLS_KEYWORDS,
    "education": SKILLS_KEYWORDS + ["idiomas", "certificaciones", "otros"],
    "skills": ["idiomas", "languages", "otros"]
}