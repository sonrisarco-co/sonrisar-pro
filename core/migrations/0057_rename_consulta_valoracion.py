from django.db import migrations


OLD_NAMES = ("Consulta / diagnóstico", "Consulta/Diagnostico", "Consulta/Diagnóstico", "Consulta / diagnostico")


def rename_consulta(apps, schema_editor):
    Procedure = apps.get_model("core", "Procedure")
    Appointment = apps.get_model("core", "Appointment")
    alias = schema_editor.connection.alias
    procedures = Procedure.objects.using(alias)
    for old in procedures.filter(nombre__in=OLD_NAMES):
        target = procedures.filter(nombre="Valoración").first()
        if target is None:
            old.nombre = "Valoración"
            old.save(using=alias, update_fields=["nombre"])
        else:
            links = Appointment.procedimientos.through.objects.using(alias)
            for appointment_id in links.filter(procedure_id=old.pk).values_list("appointment_id", flat=True):
                links.get_or_create(appointment_id=appointment_id, procedure_id=target.pk)
            old.delete(using=alias)
    Appointment.objects.using(alias).filter(motivo__in=OLD_NAMES).update(motivo="Valoración")


class Migration(migrations.Migration):
    dependencies = [("core", "0056_alter_ordenlaboratorio_odontologo")]
    operations = [migrations.RunPython(rename_consulta, migrations.RunPython.noop)]
