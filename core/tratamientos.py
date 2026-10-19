"""Seguimiento por procedimiento de las atenciones efectivas de Geisha."""
from django.db import transaction
from .models import Appointment, TratamientoGeisha


@transaction.atomic
def sincronizar_tratamientos(cita_id, using="default"):
    cita = (Appointment.objects.using(using).select_for_update()
            .select_related("odontologo").filter(pk=cita_id).first())
    if not cita or cita.odontologo.codigo != "geisha" or cita.estado != "asistio":
        return
    procedimientos = list(cita.procedimientos.using(using).all())
    nombres = {f"procedimiento:{p.pk}": p.nombre for p in procedimientos}
    if not nombres:
        nombres = {"motivo": cita.motivo.strip() or "Atención odontológica"}
    registros = TratamientoGeisha.objects.using(using)
    for clave, nombre in nombres.items():
        registro, creado = registros.get_or_create(cita=cita, clave=clave, defaults={"nombre": nombre})
        if not creado and registro.nombre != nombre:
            registro.nombre = nombre
            registro.save(using=using, update_fields=["nombre"])
    # Una corrección de los procedimientos de la cita se refleja en el informe.
    # Los estados de los procedimientos que permanecen no se modifican.
    registros.filter(cita=cita).exclude(clave__in=nombres).delete()
