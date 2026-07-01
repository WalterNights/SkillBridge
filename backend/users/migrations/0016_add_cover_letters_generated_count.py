from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0015_alter_userprofile_visible_to_companies"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="cover_letters_generated_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
