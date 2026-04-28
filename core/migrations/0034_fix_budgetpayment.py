from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_alter_patient_ci_alter_patient_telefono'),
    ]

    operations = [
        migrations.CreateModel(
            name='BudgetPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(max_length=50)),
                ('observacion', models.TextField(blank=True, null=True)),
                ('budget', models.ForeignKey(on_delete=models.CASCADE, to='core.budget')),
            ],
        ),
    ]