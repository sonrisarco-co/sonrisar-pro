from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0057_rename_consulta_valoracion"),
    ]

    operations = [
        migrations.AddField(
            model_name="prosthesis",
            name="trabajos_unificados",
            field=models.JSONField(blank=True, default=list, verbose_name="Trabajos incluidos"),
        ),
    ]
