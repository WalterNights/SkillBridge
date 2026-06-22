"""Seed inicial de tips manuales — los mismos 52 que estaban en
`frontend/src/app/shell/daily-tips.ts`. A partir de acá la fuente de
verdad es la DB y el frontend hidrata via `/api/tips/today/`.

El array static del frontend queda como fallback offline-first; si el
endpoint falla, el sidebar igual muestra un tip.

Migración data-only, idempotente (`get_or_create` por `text`).
"""

from django.db import migrations


_INITIAL_TIPS = [
    # ----- CV / ATS -----
    ("cv", "Personalizá el resumen del CV para cada match. La IA detecta keywords del job post."),
    ("cv", 'Usá los mismos términos que la oferta: si pide "JavaScript", no escribas "JS".'),
    ("cv", "Eliminá tablas e imágenes del CV — los ATS no las leen y descartan el resto."),
    ("cv", "Tu CV ideal tiene 1-2 páginas. Si tenés más de 7 años de experiencia, dos. Si menos, una."),
    ("cv", "Empezá cada bullet con un verbo de acción: lideré, implementé, optimicé, reduje."),
    ("cv", 'Acompañá los logros con números: "Reduje el tiempo de carga 40%" pega más que "mejoré performance".'),
    ("cv", 'El "Sobre mí" del CV no es una bio — son 3 líneas sobre qué buscás y qué traés.'),
    ("cv", "Guardá el CV como PDF, nunca como .docx. El formato se rompe entre versiones de Word."),

    # ----- Búsqueda activa -----
    ("search", "Postulá a 10 ofertas con CV personalizado antes que a 50 con el mismo PDF."),
    ("search", "Activá las alertas: ver una oferta el día que sale tiene 3x más respuesta que verla a la semana."),
    ("search", "Investigá la empresa antes de aplicar. Si no sabés qué hacen, el reclutador lo nota en 30 segundos."),
    ("search", "No filtres por salario si el rango no aparece. Mejor preguntar en la primera llamada."),
    ("search", "Las ofertas de viernes tarde suelen tener menos competencia el lunes a la mañana."),
    ("search", "Si una oferta lleva más de 30 días publicada, ya bajó la prioridad del HR. No te ilusiones."),
    ("search", "Mirá si la empresa renueva la misma oferta cada mes — puede indicar rotación alta del rol."),

    # ----- Entrevistas -----
    ("interview", "Practicá tu pitch de 60 segundos antes de cualquier entrevista. Lo van a pedir."),
    ("interview", "Llegá 5 minutos antes a una entrevista virtual. No 15, no 0. Cinco."),
    ("interview", 'La pregunta "¿tenés preguntas?" es la mitad de la entrevista. Llevá 3 preparadas.'),
    ("interview", "Preguntá por el equipo, no solo por el rol. Vas a trabajar con personas, no con un job description."),
    ("interview", 'Si no sabés algo en una técnica, decilo. "No lo sé pero así lo investigaría" pega mejor que inventar.'),
    ("interview", "Repasá tu CV antes de la entrevista. Si no podés explicar algo que está ahí, sacalo."),
    ("interview", "Después de una entrevista, mandá un mail corto agradeciendo el tiempo. Cuesta 2 min, pesa más de lo que parece."),

    # ----- Networking / marca personal -----
    ("networking", "Un LinkedIn con foto y headline claro recibe 14x más visitas que uno sin foto."),
    ("networking", "Pediles a 3 colegas que te escriban una recommendation en LinkedIn. La conversion en mensajes sube notable."),
    ("networking", "Tu URL de LinkedIn debería ser tu nombre. /walternights vs /walter-juan-perez-12345 — cambia mucho."),
    ("networking", "Comentar 1 post por día en tu industria te hace más visible que postear 1 vez por semana."),
    ("networking", 'No conectes con "Hola, vi tu perfil". Mencioná algo específico — un proyecto, un post, un proyecto en común.'),
    ("networking", "Mostrá lo que estás aprendiendo, no solo lo que ya sabés. Recruiters le siguen a quien crece."),

    # ----- Soft skills / negociación -----
    ("soft", "No menciones tu sueldo actual hasta que te pregunten 2 veces. La primera oferta sale del rango que vos pidas."),
    ("soft", "Si te ofrecen un rango, pedí el techo + 10%. Es estándar y muestra que sabés negociar."),
    ("soft", 'Antes de aceptar, pedí 24h para "revisar el paquete completo". Te respetan más por la pausa.'),
    ("soft", "Beneficios > sueldo bruto si tenés flexibilidad. Home office, días extra y health insurance suman miles al año."),
    ("soft", "Si el proceso es lento (>4 semanas sin avance), tomalo como señal. Así trabajan internamente."),

    # ----- Técnicas / industry-specific -----
    ("tech", "GitHub vacío es worse que GitHub con commits viejos. Pegale al menos 1 commit por mes a algo público."),
    ("tech", "Un README bien escrito en tu repo más visible pesa más que 10 repos sin descripción."),
    ("tech", 'Si te piden "experiencia con X" y trabajaste un mes con X, decí "experiencia". No esperes 2 años.'),
    ("tech", "Stack overflow profile, blog técnico o repos con stars pesan en técnicas. Mostralos en el CV."),
    ("tech", "Postulate a roles que pidan 70% de lo que sabés. El 30% restante se aprende y te pagan por aprenderlo."),
    ("tech", 'Si la oferta lista 15 tecnologías, el 30% son "nice to have". No te autocenseures por no saber todas.'),

    # ----- SkilTak meta-tips -----
    ("product", "Subí un CV completo a SkilTak. La IA matchea mejor con seniority, stack y location reales."),
    ("product", "Refrescá las ofertas cada 2-3 días. Los nuevos posts de LinkedIn entran rápido al feed."),
    ("product", 'Mirá los "Skills faltantes" del job-detail. Te dicen exactamente qué cerrar antes de aplicar a esa empresa.'),
    ("product", "Guardá las ofertas con +80% match aunque no apliques ya. Sirven para benchmark del mercado."),
    ("product", 'Si todos tus matches están abajo del 50%, ajustá el "Título profesional" del perfil. Es el mayor peso.'),
    ("product", "Marcá leídas las notificaciones que ya viste para no perder track de las nuevas."),

    # ----- Diversificación / wellness -----
    ("wellness", "No apliques en pánico un viernes a las 11 de la noche. El lunes con calma vas a postular mejor."),
    ("wellness", "Tomate medio día libre al cierre de cada sprint de búsqueda. La fatiga te baja el filtro de calidad."),
    ("wellness", "Llevá una hoja con las empresas a las que aplicaste: nombre, fecha, contacto, estado. Saber el embudo te calma."),
    ("wellness", "Tener una entrevista por semana es saludable. Más, es estrés. Menos, falta de pipeline."),
    ("wellness", "Si rechazaron tu aplicación, pedí feedback breve. 1 de cada 3 te responde algo útil."),
    ("wellness", "No tomes los rechazos como referendum. La mayoría son timing, presupuesto, o un perfil que ya tenían."),
]


def seed_tips(apps, schema_editor):
    Tip = apps.get_model("tips", "Tip")
    for category, text in _INITIAL_TIPS:
        Tip.objects.get_or_create(
            text=text,
            defaults={"category": category, "source": "manual", "is_active": True},
        )


def unseed_tips(apps, schema_editor):
    """Rollback solo borra los que coinciden exactamente por texto.
    Conservador: si en prod alguien editó la copia, no la pisamos."""
    Tip = apps.get_model("tips", "Tip")
    Tip.objects.filter(text__in=[t for _, t in _INITIAL_TIPS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tips", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_tips, reverse_code=unseed_tips),
    ]
