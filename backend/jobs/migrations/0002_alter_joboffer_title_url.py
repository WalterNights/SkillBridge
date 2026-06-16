"""Aumenta max_length de title y url para soportar URLs largas de Computrabajo
y títulos de oferta que superan 255 caracteres en algunos portales.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='joboffer',
            name='title',
            field=models.CharField(max_length=500),
        ),
        migrations.AlterField(
            model_name='joboffer',
            name='url',
            field=models.URLField(max_length=500, unique=True),
        ),
    ]
