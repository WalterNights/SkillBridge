"""Agrega `weworkremotely` a las choices del campo `portal`.

Choices se aplican a nivel form/admin (Django no impone constraint en DB),
pero la migración mantiene el historial alineado con el modelo.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0003_joboffer_portal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="joboffer",
            name="portal",
            field=models.CharField(
                choices=[
                    ("computrabajo", "Computrabajo"),
                    ("weworkremotely", "We Work Remotely"),
                    ("elempleo", "Elempleo"),
                    ("infojobs", "InfoJobs"),
                    ("magneto", "Magneto"),
                    ("bumeran", "Bumeran"),
                    ("indeed", "Indeed"),
                    ("linkedin", "LinkedIn"),
                    ("other", "Otro"),
                ],
                db_index=True,
                default="computrabajo",
                help_text="Portal de origen de la oferta",
                max_length=32,
            ),
        ),
    ]
