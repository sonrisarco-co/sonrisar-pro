from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0060_alter_prosthesis_estado")]
    operations = [
        migrations.AlterField(
            model_name="appointment",
            name="estado",
            field=models.CharField(
                choices=[("pendiente", "Pendiente"), ("En espera", "En espera"),
                         ("confirmado", "Confirmado"), ("sin_respuesta", "Sin respuesta"),
                         ("asistio", "Asistió"), ("no_asistio", "No asistió"),
                         ("cancelado", "Cancelado")],
                default="pendiente", max_length=20,
            ),
        ),
    ]
