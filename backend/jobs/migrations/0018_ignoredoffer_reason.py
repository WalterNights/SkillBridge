from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0017_joboffer_salary_text"),
    ]

    operations = [
        migrations.AddField(
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
                    ("other", "Otro"),
                ],
                default="",
                max_length=32,
            ),
        ),
    ]
