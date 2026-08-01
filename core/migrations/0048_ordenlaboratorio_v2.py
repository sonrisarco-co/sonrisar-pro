from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0047_agendareminder"),
    ]

    operations = [
        migrations.AddField(model_name="ordenlaboratorio", name="arcada", field=models.CharField(blank=True, choices=[("", "Seleccionar arcada"), ("superior", "Superior"), ("inferior", "Inferior"), ("ambas", "Ambas")], default="", max_length=20, verbose_name="Arcada")),
        migrations.AddField(model_name="ordenlaboratorio", name="piezas_removible", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="ordenlaboratorio", name="piezas_fija", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="ordenlaboratorio", name="odontologo", field=models.CharField(blank=True, default="Rodrigo", max_length=150)),
        migrations.AddField(model_name="ordenlaboratorio", name="parcial_cromo", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="parcial_acrilica", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="agregado_diente", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="agregado_gancho", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="corona_unitaria", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="provisorio_fijo", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="impresion_primaria", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="antagonista", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="enfilado_enviado", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="solicita_cubeta_individual", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="solicita_placa_articular", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="solicita_enfilado", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="solicita_terminacion", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="solicita_cromo", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="prueba_estructura", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="prueba_estetica", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="glaseado", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="material_metal", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="material_acrilico", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="material_ceromero", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="material_ceramica", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="material_zirconio", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordenlaboratorio", name="material_disilicato", field=models.BooleanField(default=False)),
    ]
