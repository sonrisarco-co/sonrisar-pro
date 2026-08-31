from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0053_budgetadjustment_budgetcredittransfer"),
    ]

    operations = [
        migrations.AddField(
            model_name="ordenlaboratorio",
            name="modelo_trabajo",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="ordenlaboratorio",
            name="solicita_bizcocho",
            field=models.BooleanField(default=False),
        ),
    ]
