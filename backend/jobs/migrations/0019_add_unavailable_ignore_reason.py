from django.db import migrations, models


class Migration(migrations.Migration):
    """Agrega el motivo 'unavailable' (Oferta no disponible) al set de
    choices de IgnoredOffer.reason.

    Motivo cruzado: si un user reporta que el portal externo bajo la
    oferta, es una señal fuerte para verify_active_offers de que le
    escapo esa fila. Con 2+ reportes independientes podemos marcarla
    is_active=False directamente sin esperar al cron.
    """

    dependencies = [
        ("jobs", "0018_ignoredoffer_reason"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ignoredoffer",
            name="reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("salary", "Sueldo bajo"),
                    ("location", "Ubicación"),
                    ("stack", "Stack"),
                    ("company", "Empresa"),
                    ("already_applied", "Ya apliqué"),
                    ("unavailable", "Oferta no disponible"),
                    ("other", "Otro"),
                ],
                default="",
                max_length=32,
            ),
        ),
    ]
