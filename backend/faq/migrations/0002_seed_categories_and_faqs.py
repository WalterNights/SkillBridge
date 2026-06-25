"""Seed inicial del FAQ: 5 categorías + 10 preguntas curadas.

Estas preguntas son las dudas más probables de un user nuevo. Apuntan
a explicar el "modelo mental" de SkilTak: cómo matcheamos, qué hace
la AI, qué pasa con su CV/data, cuánto cuesta. Se cargan como
`source='seed'` + `status='published'` así aparecen en `/faq`
inmediatamente — sin pasar por moderación.

Si el admin las quiere editar, lo hace desde `/admin/faqs`. Si las
quiere borrar, las marca como `rejected`. Estos seeds NO son
idempotentes a la inversa: no remueven nada en la migración de
reversa (`reverse_code=migrations.RunPython.noop`) porque pueden
haber sido editados a mano.
"""

from django.db import migrations
from django.utils.text import slugify


# ──────────────────────────────────────────────────────────────────────
# Seed data — editable sin afectar el schema. Cualquier cambio acá
# REQUIERE una nueva migración data (no editar esta).
# ──────────────────────────────────────────────────────────────────────

CATEGORIES = [
    {
        "name": "Cuenta",
        "description": "Registro, login, perfil y seguridad de tu cuenta.",
        "display_order": 10,
    },
    {
        "name": "CV",
        "description": "Cómo cargar y mejorar tu CV con AI.",
        "display_order": 20,
    },
    {
        "name": "Matches",
        "description": "Cómo calculamos qué ofertas se ajustan a tu perfil.",
        "display_order": 30,
    },
    {
        "name": "Postulaciones",
        "description": "Aplicar a ofertas y seguimiento.",
        "display_order": 40,
    },
    {
        "name": "Privacidad",
        "description": "Qué datos guardamos y cómo los usamos.",
        "display_order": 50,
    },
]


FAQS = [
    # ─── Matches (lo primero que el usuario quiere entender) ──────────
    {
        "category": "Matches",
        "question": "¿Cómo se calcula el porcentaje de match con una oferta?",
        "answer": (
            "Comparamos las skills de tu perfil contra las que la oferta menciona "
            "explícitamente. El porcentaje refleja cuántas skills coinciden y qué tan "
            "centrales son para el puesto. Un match del 70% o más suele indicar que "
            "vale la pena postularte aunque te falte parte del stack."
        ),
        "display_order": 10,
    },
    {
        "category": "Matches",
        "question": "¿De qué portales vienen las ofertas?",
        "answer": (
            "Actualmente leemos Computrabajo, Elempleo, LinkedIn, WeWorkRemotely y "
            "Trabajos Colombia. El listado se actualiza varias veces por día. "
            "Pronto sumamos más portales según la demanda."
        ),
        "display_order": 20,
    },
    {
        "category": "Matches",
        "question": "¿Cada cuánto se actualizan las ofertas?",
        "answer": (
            "El scraper corre cada pocas horas, así que ves ofertas nuevas durante "
            "todo el día. Si una oferta deja de existir en el portal original, la "
            "marcamos como vencida y desaparece de tu feed automáticamente."
        ),
        "display_order": 30,
    },
    # ─── CV ───────────────────────────────────────────────────────────
    {
        "category": "CV",
        "question": "¿Cómo subo mi CV?",
        "answer": (
            "Ve a 'Mi CV' desde el menú lateral. Puedes subirlo en PDF o llenarlo "
            "campo por campo. Lo que cargues alimenta el matching — cuanto más "
            "completo, más precisas las ofertas que te recomendamos."
        ),
        "display_order": 10,
    },
    {
        "category": "CV",
        "question": "¿Qué hace 'Mejorar CV con AI'?",
        "answer": (
            "La AI reescribe tu resumen profesional con más impacto, cuantifica los "
            "bullets de experiencia (donde puede inferir métricas razonables) y "
            "reordena tus skills. NO inventa empresas, fechas ni roles — solo "
            "mejora la presentación. Es 1 uso por cuenta para evitar que el modelo "
            "se 'sobreescriba' a sí mismo."
        ),
        "display_order": 20,
    },
    {
        "category": "CV",
        "question": "¿Por qué mi CV mejorado se ve diferente al original?",
        "answer": (
            "Si tu CV original estaba en español, la AI mantiene el español. Si "
            "estaba en inglés, mantiene inglés. Las fechas obvias mal escritas (ej. "
            "'2026' en un trabajo pasado) se corrigen automáticamente y te las "
            "marcamos antes de aplicar el cambio."
        ),
        "display_order": 30,
    },
    # ─── Cuenta ───────────────────────────────────────────────────────
    {
        "category": "Cuenta",
        "question": "¿Qué cuenta como 'perfil completo'?",
        "answer": (
            "Un perfil completo tiene nombre, apellido, ciudad, teléfono, título "
            "profesional Y un CV cargado. Hasta que no llenes todo eso, no podemos "
            "calcular tu match real ni notificarte ofertas relevantes."
        ),
        "display_order": 10,
    },
    {
        "category": "Cuenta",
        "question": "Olvidé mi contraseña, ¿cómo la recupero?",
        "answer": (
            "Desde la pantalla de login, haz clic en '¿La olvidaste?'. Te enviamos "
            "un código de 8 dígitos al correo registrado. El código expira en 15 "
            "minutos por seguridad. Si no llega, revisa spam."
        ),
        "display_order": 20,
    },
    # ─── Postulaciones ────────────────────────────────────────────────
    {
        "category": "Postulaciones",
        "question": "¿Qué pasa cuando ignoro una oferta?",
        "answer": (
            "Esa oferta se mueve a 'Ofertas ignoradas' y deja de aparecer en tu "
            "feed principal. Puedes deshacer la acción desde esa misma sección. "
            "Usar 'Ignorar' nos ayuda a calibrar qué tipo de ofertas no son para ti."
        ),
        "display_order": 10,
    },
    # ─── Privacidad ───────────────────────────────────────────────────
    {
        "category": "Privacidad",
        "question": "¿Qué hacen con mi CV y mis datos?",
        "answer": (
            "Tu CV y datos personales se usan ÚNICAMENTE para calcular tu match "
            "con las ofertas que ves en tu feed. NO los compartimos con empresas, "
            "ni los vendemos a terceros, ni los usamos para entrenar modelos. "
            "Puedes borrar tu cuenta desde Configuración cuando quieras."
        ),
        "display_order": 10,
    },
]


def create_seed(apps, schema_editor):
    FaqCategory = apps.get_model("faq", "FaqCategory")
    FaqQuestion = apps.get_model("faq", "FaqQuestion")

    category_by_name: dict[str, object] = {}
    for cat in CATEGORIES:
        obj, _ = FaqCategory.objects.update_or_create(
            name=cat["name"],
            defaults={
                "slug": slugify(cat["name"])[:80],
                "description": cat["description"],
                "display_order": cat["display_order"],
                "is_active": True,
            },
        )
        category_by_name[cat["name"]] = obj

    for faq in FAQS:
        # `update_or_create` por `question` para que re-correr la
        # migración (en testing) no duplique entries. Si el admin ya
        # editó la respuesta en producción, esta migración NO la pisa
        # porque la match key es la pregunta literal (no el ID).
        FaqQuestion.objects.update_or_create(
            question=faq["question"],
            defaults={
                "answer": faq["answer"],
                "category": category_by_name[faq["category"]],
                "source": "seed",
                "status": "published",
                "display_order": faq["display_order"],
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("faq", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_seed, reverse_code=migrations.RunPython.noop),
    ]
