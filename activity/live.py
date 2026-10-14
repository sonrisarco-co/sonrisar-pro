from django.db.models import Count, Max
from .models import Activity

# Includes patient names, appointments, blocks, reminders and balances displayed
# by the day agenda. Login/logout and unrelated inventory edits do not refresh it.
AGENDA_SECTIONS = (
    'Pacientes', 'Procedimientos', 'Agenda', 'Bloqueos de agenda', 'Recordatorios',
    'Presupuestos', 'Ítems de presupuesto', 'Pagos de presupuesto',
    'Ajustes de presupuesto', 'Transferencias de saldo', 'Pagos en Pro',
    'Historia clínica', 'Avisos clínicos',
)
def agenda_revision():
    values = Activity.objects.filter(section__in=AGENDA_SECTIONS).aggregate(
        count=Count('id'), latest=Max('id'))
    # Count also detects an earlier ID committing after a later ID, which can
    # happen with concurrent PostgreSQL transactions. Max alone would miss it.
    return f"{values['count']}:{values['latest'] or 0}"
