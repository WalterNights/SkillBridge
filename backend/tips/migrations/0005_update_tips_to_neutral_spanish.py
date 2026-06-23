"""Reescribe los 51 tips del seed original a español neutro (sin voseo).

Antes el seed estaba en voseo argentino ("Personalizá", "Postulá",
"tenés"). El producto apunta a toda Latam, así que cambiamos a
imperativos estándar ("Personaliza", "Postúlate", "tienes").

Estrategia: map old_text → new_text uno a uno. Si una fila no matchea
ningún old_text (porque fue editada a mano post-seed o es AI-generated
con copy nuevo), se deja como está. Idempotente — correr dos veces no
duplica nada y no rompe.

Reverse opcional, vuelve los neutros al voseo. Mantenemos por simetría
pero en práctica nunca se va a revertir.
"""

from django.db import migrations


# Mapping exhaustivo de los 51 tips originales del seed → versión neutra.
# Si añadimos tips manuales nuevos en el futuro, no entran acá; este
# migration solo cubre el set original.
_REWRITES: list[tuple[str, str]] = [
    # ----- CV / ATS -----
    (
        "Personalizá el resumen del CV para cada match. La IA detecta keywords del job post.",
        "Personaliza el resumen del CV para cada match. La IA detecta keywords del job post.",
    ),
    (
        'Usá los mismos términos que la oferta: si pide "JavaScript", no escribas "JS".',
        'Usa los mismos términos que la oferta: si pide "JavaScript", no escribas "JS".',
    ),
    (
        "Eliminá tablas e imágenes del CV — los ATS no las leen y descartan el resto.",
        "Elimina tablas e imágenes del CV — los ATS no las leen y descartan el resto.",
    ),
    (
        "Tu CV ideal tiene 1-2 páginas. Si tenés más de 7 años de experiencia, dos. Si menos, una.",
        "Tu CV ideal tiene 1-2 páginas. Si tienes más de 7 años de experiencia, dos. Si menos, una.",
    ),
    (
        "Empezá cada bullet con un verbo de acción: lideré, implementé, optimicé, reduje.",
        "Empieza cada bullet con un verbo de acción: lideré, implementé, optimicé, reduje.",
    ),
    (
        'Acompañá los logros con números: "Reduje el tiempo de carga 40%" pega más que "mejoré performance".',
        'Acompaña los logros con números: "Reduje el tiempo de carga 40%" pega más que "mejoré performance".',
    ),
    (
        'El "Sobre mí" del CV no es una bio — son 3 líneas sobre qué buscás y qué traés.',
        'El "Sobre mí" del CV no es una bio — son 3 líneas sobre qué buscas y qué traes.',
    ),
    (
        "Guardá el CV como PDF, nunca como .docx. El formato se rompe entre versiones de Word.",
        "Guarda el CV como PDF, nunca como .docx. El formato se rompe entre versiones de Word.",
    ),

    # ----- Búsqueda activa -----
    (
        "Postulá a 10 ofertas con CV personalizado antes que a 50 con el mismo PDF.",
        "Postúlate a 10 ofertas con CV personalizado antes que a 50 con el mismo PDF.",
    ),
    (
        "Activá las alertas: ver una oferta el día que sale tiene 3x más respuesta que verla a la semana.",
        "Activa las alertas: ver una oferta el día que sale tiene 3x más respuesta que verla a la semana.",
    ),
    (
        "Investigá la empresa antes de aplicar. Si no sabés qué hacen, el reclutador lo nota en 30 segundos.",
        "Investiga la empresa antes de aplicar. Si no sabes qué hacen, el reclutador lo nota en 30 segundos.",
    ),
    (
        "Las ofertas de viernes tarde suelen tener menos competencia el lunes a la mañana.",
        "Las ofertas de viernes en la tarde suelen tener menos competencia el lunes en la mañana.",
    ),
    (
        "Mirá si la empresa renueva la misma oferta cada mes — puede indicar rotación alta del rol.",
        "Mira si la empresa renueva la misma oferta cada mes — puede indicar rotación alta del rol.",
    ),

    # ----- Entrevistas -----
    (
        "Practicá tu pitch de 60 segundos antes de cualquier entrevista. Lo van a pedir.",
        "Practica tu pitch de 60 segundos antes de cualquier entrevista. Lo van a pedir.",
    ),
    (
        "Llegá 5 minutos antes a una entrevista virtual. No 15, no 0. Cinco.",
        "Llega 5 minutos antes a una entrevista virtual. No 15, no 0. Cinco.",
    ),
    (
        'La pregunta "¿tenés preguntas?" es la mitad de la entrevista. Llevá 3 preparadas.',
        'La pregunta "¿tienes preguntas?" es la mitad de la entrevista. Lleva 3 preparadas.',
    ),
    (
        "Preguntá por el equipo, no solo por el rol. Vas a trabajar con personas, no con un job description.",
        "Pregunta por el equipo, no solo por el rol. Vas a trabajar con personas, no con un job description.",
    ),
    (
        'Si no sabés algo en una técnica, decilo. "No lo sé pero así lo investigaría" pega mejor que inventar.',
        'Si no sabes algo técnico, dilo. "No lo sé pero así lo investigaría" pega mejor que inventar.',
    ),
    (
        "Repasá tu CV antes de la entrevista. Si no podés explicar algo que está ahí, sacalo.",
        "Repasa tu CV antes de la entrevista. Si no puedes explicar algo que está ahí, sácalo.",
    ),
    (
        "Después de una entrevista, mandá un mail corto agradeciendo el tiempo. Cuesta 2 min, pesa más de lo que parece.",
        "Después de una entrevista, manda un correo corto agradeciendo el tiempo. Cuesta 2 min, pesa más de lo que parece.",
    ),

    # ----- Networking -----
    (
        "Pediles a 3 colegas que te escriban una recommendation en LinkedIn. La conversion en mensajes sube notable.",
        "Pide a 3 colegas que te escriban una recommendation en LinkedIn. La conversión en mensajes sube notable.",
    ),
    (
        'No conectes con "Hola, vi tu perfil". Mencioná algo específico — un proyecto, un post, un proyecto en común.',
        'No conectes con "Hola, vi tu perfil". Menciona algo específico — un proyecto, un post, un interés en común.',
    ),
    (
        "Mostrá lo que estás aprendiendo, no solo lo que ya sabés. Recruiters le siguen a quien crece.",
        "Muestra lo que estás aprendiendo, no solo lo que ya sabes. Recruiters siguen a quien crece.",
    ),

    # ----- Soft skills / negociación -----
    (
        "No menciones tu sueldo actual hasta que te pregunten 2 veces. La primera oferta sale del rango que vos pidas.",
        "No menciones tu sueldo actual hasta que te pregunten 2 veces. La primera oferta sale del rango que tú pidas.",
    ),
    (
        "Si te ofrecen un rango, pedí el techo + 10%. Es estándar y muestra que sabés negociar.",
        "Si te ofrecen un rango, pide el techo + 10%. Es estándar y muestra que sabes negociar.",
    ),
    (
        'Antes de aceptar, pedí 24h para "revisar el paquete completo". Te respetan más por la pausa.',
        'Antes de aceptar, pide 24h para "revisar el paquete completo". Te respetan más por la pausa.',
    ),
    (
        "Beneficios > sueldo bruto si tenés flexibilidad. Home office, días extra y health insurance suman miles al año.",
        "Beneficios > sueldo bruto si tienes flexibilidad. Home office, días extra y seguro médico suman miles al año.",
    ),
    (
        "Si el proceso es lento (>4 semanas sin avance), tomalo como señal. Así trabajan internamente.",
        "Si el proceso es lento (>4 semanas sin avance), tómalo como señal. Así trabajan internamente.",
    ),

    # ----- Técnicas -----
    (
        "GitHub vacío es worse que GitHub con commits viejos. Pegale al menos 1 commit por mes a algo público.",
        "GitHub vacío es peor que GitHub con commits viejos. Haz al menos 1 commit por mes a algo público.",
    ),
    (
        'Si te piden "experiencia con X" y trabajaste un mes con X, decí "experiencia". No esperes 2 años.',
        'Si piden "experiencia con X" y trabajaste un mes con X, escribe "experiencia". No esperes 2 años.',
    ),
    (
        "Stack overflow profile, blog técnico o repos con stars pesan en técnicas. Mostralos en el CV.",
        "Stack overflow profile, blog técnico o repos con stars pesan en técnicas. Muéstralos en el CV.",
    ),
    (
        "Postulate a roles que pidan 70% de lo que sabés. El 30% restante se aprende y te pagan por aprenderlo.",
        "Postúlate a roles que pidan 70% de lo que sabes. El 30% restante se aprende y te pagan por aprenderlo.",
    ),
    (
        'Si la oferta lista 15 tecnologías, el 30% son "nice to have". No te autocenseures por no saber todas.',
        'Si la oferta lista 15 tecnologías, el 30% son "nice to have". No te autocensures por no saber todas.',
    ),

    # ----- SkilTak meta-tips -----
    (
        "Subí un CV completo a SkilTak. La IA matchea mejor con seniority, stack y location reales.",
        "Sube un CV completo a SkilTak. La IA hace mejor match con seniority, stack y ubicación reales.",
    ),
    (
        "Refrescá las ofertas cada 2-3 días. Los nuevos posts de LinkedIn entran rápido al feed.",
        "Refresca las ofertas cada 2-3 días. Los nuevos posts de LinkedIn entran rápido al feed.",
    ),
    (
        'Mirá los "Skills faltantes" del job-detail. Te dicen exactamente qué cerrar antes de aplicar a esa empresa.',
        'Mira los "Skills faltantes" del job-detail. Te dicen exactamente qué cerrar antes de aplicar a esa empresa.',
    ),
    (
        "Guardá las ofertas con +80% match aunque no apliques ya. Sirven para benchmark del mercado.",
        "Guarda las ofertas con +80% match aunque no apliques ya. Sirven para benchmark del mercado.",
    ),
    (
        'Si todos tus matches están abajo del 50%, ajustá el "Título profesional" del perfil. Es el mayor peso.',
        'Si todos tus matches están por debajo del 50%, ajusta el "Título profesional" del perfil. Es el mayor peso.',
    ),
    (
        "Marcá leídas las notificaciones que ya viste para no perder track de las nuevas.",
        "Marca como leídas las notificaciones que ya viste para no perder track de las nuevas.",
    ),

    # ----- Wellness -----
    (
        "Tomate medio día libre al cierre de cada sprint de búsqueda. La fatiga te baja el filtro de calidad.",
        "Tómate medio día libre al cierre de cada sprint de búsqueda. La fatiga te baja el filtro de calidad.",
    ),
    (
        "Llevá una hoja con las empresas a las que aplicaste: nombre, fecha, contacto, estado. Saber el embudo te calma.",
        "Lleva una hoja con las empresas a las que aplicaste: nombre, fecha, contacto, estado. Saber el embudo te calma.",
    ),
    (
        "Si rechazaron tu aplicación, pedí feedback breve. 1 de cada 3 te responde algo útil.",
        "Si rechazaron tu aplicación, pide feedback breve. 1 de cada 3 te responde algo útil.",
    ),
    (
        "No tomes los rechazos como referendum. La mayoría son timing, presupuesto, o un perfil que ya tenían.",
        "No tomes los rechazos como referéndum. La mayoría son timing, presupuesto, o un perfil que ya tenían.",
    ),
]


def rewrite_to_neutral(apps, schema_editor):
    Tip = apps.get_model("tips", "Tip")
    for old, new in _REWRITES:
        if old == new:
            continue
        Tip.objects.filter(text=old).update(text=new)


def revert_to_voseo(apps, schema_editor):
    Tip = apps.get_model("tips", "Tip")
    for old, new in _REWRITES:
        if old == new:
            continue
        Tip.objects.filter(text=new).update(text=old)


class Migration(migrations.Migration):

    dependencies = [
        ("tips", "0004_retag_tech_tips_to_tech_scope"),
    ]

    operations = [
        migrations.RunPython(rewrite_to_neutral, reverse_code=revert_to_voseo),
    ]
