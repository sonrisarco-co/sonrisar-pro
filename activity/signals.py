import json
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_save, post_save, pre_delete, m2m_changed
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .middleware import current_request, manager
from .models import Activity

SECTIONS = {'Patient': 'Pacientes', 'Procedure': 'Procedimientos', 'Appointment': 'Agenda',
    'DayBlock': 'Bloqueos de agenda', 'TimeBlock': 'Bloqueos de agenda', 'AgendaReminder': 'Recordatorios',
    'ClinicalRecord': 'Historia clínica', 'ClinicalAlert': 'Avisos clínicos', 'OdontogramTooth': 'Odontograma',
    'OdontogramaCara': 'Odontograma', 'Budget': 'Presupuestos', 'BudgetItem': 'Ítems de presupuesto',
    'BudgetPayment': 'Pagos de presupuesto', 'BudgetAdjustment': 'Ajustes de presupuesto',
    'BudgetCreditTransfer': 'Transferencias de saldo', 'Payment': 'Pagos en Pro', 'Prosthesis': 'Prótesis',
    'OrdenLaboratorio': 'Laboratorio', 'Inventory': 'Inventario', 'InventoryMovement': 'Movimientos de inventario',
    'RayosX': 'Rayos X / Fotografías', 'TratamientoGeisha': 'Tratamientos de Geisha', 'CobroTratamientoGeisha': 'Comisiones de Geisha', 'LiquidacionGeisha': 'Comisiones de Geisha', 'DetalleLiquidacionGeisha': 'Comisiones de Geisha'}
def snapshot(instance):
    return json.loads(json.dumps({f.name: f.value_from_object(instance) for f in instance._meta.concrete_fields}, cls=DjangoJSONEncoder))
def record(action, instance=None, changes=None, user=None):
    request = current_request.get()
    user = user or (getattr(request, 'user', None) if request else None)
    Activity.objects.create(user=user if user and user.is_authenticated else None,
        username=user.get_username() if user and user.is_authenticated else 'Sistema / tarea automática',
        action=action, section=SECTIONS.get(type(instance).__name__, str(instance._meta.verbose_name)) if instance else 'Acceso',
        object_id=str(instance.pk) if instance else '', description=str(instance)[:500] if instance else '', changes=changes or {})
@receiver(pre_save)
def before_save(sender, instance, raw=False, **kwargs):
    if sender._meta.app_label != 'core' or raw: return
    old = sender.objects.filter(pk=instance.pk).first() if instance.pk else None
    instance._audit_before = snapshot(old) if old else None
@receiver(post_save)
def after_save(sender, instance, created, raw=False, **kwargs):
    if sender._meta.app_label != 'core' or raw: return
    before = getattr(instance, '_audit_before', None) or {}
    after = snapshot(instance)
    changes = {k: {'antes': before.get(k), 'después': v} for k,v in after.items() if before.get(k) != v}
    if created or changes: record('Agregó' if created else 'Modificó', instance, changes)
@receiver(pre_delete)
def before_delete(sender, instance, **kwargs):
    if sender._meta.app_label != 'core': return
    request = current_request.get()
    if sender.__name__ in {'Patient', 'ClinicalRecord'} and request and not manager(request.user):
        raise PermissionDenied('No tenés permiso para eliminar pacientes o historias clínicas.')
    record('Eliminó', instance, {k: {'antes': v, 'después': None} for k,v in snapshot(instance).items()})
@receiver(m2m_changed)
def relations(sender, instance, action, pk_set, **kwargs):
    if instance._meta.app_label == 'core' and action in {'post_add','post_remove','post_clear'}:
        record('Modificó relación', instance, {'relación': {'antes': None, 'después': {'tabla': sender._meta.label, 'acción': action, 'ids': sorted(pk_set or [])}}})
@receiver(user_logged_in)
def logged_in(sender, user, **kwargs): record('Ingresó', user=user)
@receiver(user_logged_out)
def logged_out(sender, user, **kwargs): record('Salió', user=user)
