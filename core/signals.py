from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from .models import Appointment
from .tratamientos import sincronizar_tratamientos


@receiver(post_save, sender=Appointment)
def actualizar_tratamientos(sender, instance, raw=False, using="default", **kwargs):
    if not raw and instance.estado == "asistio":
        sincronizar_tratamientos(instance.pk, using=using)


@receiver(m2m_changed, sender=Appointment.procedimientos.through)
def actualizar_procedimientos(sender, instance, action, reverse, pk_set, using="default", **kwargs):
    if reverse and action == "pre_clear":
        instance._tratamientos_citas_ids = list(instance.appointments.using(using).values_list("pk", flat=True))
        return
    if reverse and action == "post_clear":
        pk_set = getattr(instance, "_tratamientos_citas_ids", [])
    if action not in {"post_add", "post_remove", "post_clear"}:
        return
    if not reverse:
        sincronizar_tratamientos(instance.pk, using=using)
    elif pk_set:
        for cita_id in pk_set:
            sincronizar_tratamientos(cita_id, using=using)
