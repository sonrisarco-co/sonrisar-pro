from django.db import migrations, models


def actualizar_odontologo(apps, schema_editor):
    OrdenLaboratorio = apps.get_model("core", "OrdenLaboratorio")
    OrdenLaboratorio.objects.filter(
        odontologo__in=["", "Rodrigo"]
    ).update(odontologo="Dr. Rodrigo Suma")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0055_prosthesis_color"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ordenlaboratorio",
            name="odontologo",
            field=models.CharField(blank=True, default="Dr. Rodrigo Suma", max_length=150),
        ),
        migrations.RunPython(actualizar_odontologo, migrations.RunPython.noop),
    ]
