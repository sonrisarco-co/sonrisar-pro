from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0054_ordenlaboratorio_modelo_trabajo_bizcocho"),
    ]

    operations = [
        migrations.AddField(
            model_name="prosthesis",
            name="color",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="Color"),
        ),
    ]
