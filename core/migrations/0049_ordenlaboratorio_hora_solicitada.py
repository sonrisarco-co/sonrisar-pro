from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0048_ordenlaboratorio_v2"),
    ]

    operations = [
        migrations.AddField(
            model_name="ordenlaboratorio",
            name="hora_entrega_solicitada",
            field=models.TimeField(
                blank=True,
                null=True,
                verbose_name="Hora solicitada",
            ),
        ),
        migrations.AlterField(
            model_name="ordenlaboratorio",
            name="fecha_entrega_prometida",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Solicitado para",
            ),
        ),
    ]
