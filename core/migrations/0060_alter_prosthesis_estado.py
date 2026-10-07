from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0059_alter_clinicalrecord_fecha")]

    operations = [
        migrations.AlterField(
            model_name="prosthesis",
            name="estado",
            field=models.CharField(
                choices=[
                    ("laboratorio", "En laboratorio"),
                    ("proceso", "En proceso"),
                    ("prueba", "En consultorio"),
                    ("entrega", "Lista para entrega"),
                    ("entregada", "Entregada"),
                ],
                default="laboratorio",
                max_length=20,
                verbose_name="Estado",
            ),
        ),
    ]
