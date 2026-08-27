from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0052_clinicalalert"),
    ]

    operations = [
        migrations.CreateModel(
            name="BudgetAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateField(default=django.utils.timezone.now)),
                ("monto", models.DecimalField(decimal_places=2, max_digits=10)),
                ("motivo", models.CharField(max_length=255)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("presupuesto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ajustes", to="core.budget")),
            ],
            options={"ordering": ["-fecha", "-id"]},
        ),
        migrations.CreateModel(
            name="BudgetCreditTransfer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateField(default=django.utils.timezone.now)),
                ("monto", models.DecimalField(decimal_places=2, max_digits=10)),
                ("motivo", models.CharField(max_length=255)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("presupuesto_destino", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_recibidas", to="core.budget")),
                ("presupuesto_origen", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transferencias_enviadas", to="core.budget")),
            ],
            options={"ordering": ["-fecha", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="budgetcredittransfer",
            constraint=models.CheckConstraint(condition=models.Q(("monto__gt", 0)), name="budget_credit_transfer_monto_positivo"),
        ),
        migrations.AddConstraint(
            model_name="budgetcredittransfer",
            constraint=models.CheckConstraint(condition=models.Q(("presupuesto_origen", models.F("presupuesto_destino")), _negated=True), name="budget_credit_transfer_presupuestos_distintos"),
        ),
    ]
