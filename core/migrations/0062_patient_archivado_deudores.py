from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0061_alter_appointment_estado"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="archivado_deudores",
            field=models.BooleanField(
                default=False,
                db_index=True,
                verbose_name="Archivado en Deudores",
            ),
        ),
    ]
