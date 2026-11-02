from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0068_birthday_greetings')]
    operations = [migrations.AddField(
        model_name='appointment', name='deuda_categoria',
        field=models.CharField(
            choices=[('auto', 'Automático según el tratamiento'), ('general', 'General'),
                     ('protesis', 'Prótesis'), ('endodoncia', 'Endodoncias'), ('corona', 'Coronas')],
            default='auto', max_length=20, verbose_name='Categoría de deuda / pago',
        ),
    )]
