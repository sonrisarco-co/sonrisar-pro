from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_patient_fecha_nacimiento'),
]

  

    operations = [
        migrations.AddField(
            model_name="patient",
            name="fecha_nacimiento",
            field=models.DateField(null=True, blank=True),
        ),
    ]
