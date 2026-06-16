"""Agrega el campo `portal` a JobOffer para identificar de dónde viene
cada oferta. Las filas existentes (cargadas hasta ahora desde Computrabajo)
quedan con el default 'computrabajo'.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_alter_joboffer_title_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='joboffer',
            name='portal',
            field=models.CharField(
                choices=[
                    ('computrabajo', 'Computrabajo'),
                    ('elempleo', 'Elempleo'),
                    ('infojobs', 'InfoJobs'),
                    ('magneto', 'Magneto'),
                    ('bumeran', 'Bumeran'),
                    ('indeed', 'Indeed'),
                    ('linkedin', 'LinkedIn'),
                    ('other', 'Otro'),
                ],
                db_index=True,
                default='computrabajo',
                help_text='Portal de origen de la oferta',
                max_length=32,
            ),
        ),
    ]
