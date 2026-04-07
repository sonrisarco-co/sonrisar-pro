from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_remove_clinicalrecord_paciente_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="clinicalrecord",
            name="patient",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="core.patient",
            ),
        ),
    ]
