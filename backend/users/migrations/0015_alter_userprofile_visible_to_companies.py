"""Cambia el default de visible_to_companies a True + activa los perfiles
existentes.

Hasta el 2026-06-27, el default era False (opt-in explícito desde
Settings). Resultado: la bolsa de profesionales quedaba vacía porque
los usuarios se registraban en plataforma de empleo y nunca entendían
que tenían que ir a privacidad a activarse para ser encontrados.

Cambio: default True. Los perfiles existentes con False venian todos
del default histórico (NADIE habia hecho opt-out explícito todavía),
así que es seguro pasarlos a True con este UPDATE.

Si en algún momento hay un perfil que hizo opt-out explícito y queremos
respetarlo, esta migration NO debería correr de nuevo. Está hecha para
correr UNA vez en la transición 2026-06-27.
"""

from django.db import migrations, models


def activate_existing_profiles(apps, schema_editor):
    """Setea visible_to_companies=True para todos los perfiles que
    están en False — venían del default viejo, nadie los apagó a mano."""
    UserProfile = apps.get_model("users", "UserProfile")
    UserProfile.objects.filter(visible_to_companies=False).update(
        visible_to_companies=True
    )


def reverse_noop(apps, schema_editor):
    """No reversible — no sabemos qué perfiles eran originalmente False
    por default vs apagados a mano."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_companyinterest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='visible_to_companies',
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.RunPython(activate_existing_profiles, reverse_code=reverse_noop),
    ]
