from django.db import migrations, models


class Migration(migrations.Migration):
    """CV multi-idioma (Español + English) + preferencias de display.

    Agregamos 5 campos con sufijo _en (versiones inglesas del contenido
    editable) + 3 preferencias que controlan el render del CV (idioma
    activo, alineación de texto, tamaño de fuente).

    Los campos ES existentes NO se tocan — se mantienen como el "primary"
    implícito para preservar backwards compat de API/serializer. Cuando
    el user activa EN en el editor, edita los campos _en por separado.
    Los datos personales (nombre, teléfono, city) y los factuales
    (languages que habla) NO se duplican: no son traducibles.
    """

    dependencies = [
        ("users", "0017_alter_userprofile_resume"),
    ]

    operations = [
        # Contenido editable duplicado en inglés.
        migrations.AddField(
            model_name="userprofile",
            name="summary_en",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="education_en",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="skills_en",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="experience_en",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="soft_skills_en",
            field=models.TextField(blank=True, default=""),
        ),
        # Preferencias de display del CV.
        migrations.AddField(
            model_name="userprofile",
            name="cv_active_language",
            field=models.CharField(
                choices=[("es", "Español"), ("en", "English")],
                default="es",
                max_length=4,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="cv_text_align",
            field=models.CharField(
                choices=[
                    ("left", "Alineado a la izquierda"),
                    ("justify", "Justificado"),
                ],
                default="left",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="cv_font_size",
            field=models.CharField(
                choices=[("sm", "Pequeño"), ("md", "Mediano"), ("lg", "Grande")],
                default="md",
                max_length=2,
            ),
        ),
    ]
