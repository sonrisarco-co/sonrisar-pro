"""Shared updates for HTML screens; actions, downloads and APIs never reload."""
from django.db.models import Count, Max
from .models import Activity
from .live import AGENDA_SECTIONS

SCOPES = {
    'agenda': AGENDA_SECTIONS,
    'pacientes': ('Pacientes', 'Agenda', 'Historia clínica', 'Avisos clínicos'),
    'clinica': ('Pacientes', 'Historia clínica', 'Avisos clínicos', 'Agenda'),
    'odontograma': ('Pacientes', 'Odontograma'),
    'presupuestos': ('Pacientes', 'Presupuestos', 'Ítems de presupuesto', 'Pagos de presupuesto', 'Ajustes de presupuesto', 'Transferencias de saldo', 'Pagos en Pro'),
    'pagos': ('Pacientes', 'Agenda', 'Presupuestos', 'Pagos de presupuesto', 'Ajustes de presupuesto', 'Transferencias de saldo', 'Pagos en Pro'),
    'protesis': ('Pacientes', 'Prótesis', 'Laboratorio', 'Pagos en Pro'),
    'tratamientos_geisha': ('Tratamientos de Geisha', 'Agenda', 'Pacientes', 'Procedimientos'),
    'inventario': ('Inventario', 'Movimientos de inventario'),
    'imagenes': ('Pacientes', 'Rayos X / Fotografías'),
    'general': None,
    'actividad': None,
}

# Editing pages receive notices only; their fields are never automatically reset.
VIEWS = {}
for scope, names in {
    'general': ('home', 'estadisticas', 'dashboard_asistencia'),
    'agenda': ('agenda_pro', 'agenda_week', 'agenda_month', 'agenda_calendar', 'agenda_horarios_dia', 'whatsapp_reminders'),
    'pacientes': ('patient_detail', 'patient_finances', 'patient_appointments', 'pacientes_inactivos'),
    'clinica': ('clinical_record_search', 'clinical_records_list', 'clinical_record_detail'),
    'presupuestos': ('budgets_list', 'budget_detail', 'patient_budgets'),
    'pagos': ('payments_list', 'deudores_general'),
    'protesis': ('protesis_list', 'protesis_detail', 'protesis_activas_informe', 'orden_laboratorio_detalle'),
    'inventario': ('inventory_list', 'inventory_history', 'inventory_shopping_list'),
    'imagenes': ('rayos_x_list',),
    'tratamientos_geisha': ('tratamientos_geisha',),
    'actividad': ('activity_daily',),
}.items():
    for name in names:
        VIEWS[name] = {'scope': scope, 'manual': False}

for scope, names in {
    'pacientes': ('patient_new', 'patient_edit'),
    'agenda': ('appointment_new', 'appointment_edit', 'agenda_reminder_create', 'agenda_reminder_edit'),
    'clinica': ('clinical_record_new', 'clinical_record_edit'),
    'odontograma': ('odontograma_paciente', 'odontograma_profesional'),
    'presupuestos': ('budget_new', 'budget_edit'),
    'protesis': ('protesis_new', 'protesis_edit', 'orden_laboratorio_nueva', 'orden_laboratorio_editar'),
    'inventario': ('inventory_new', 'inventory_edit', 'inventory_movement_new'),
    'imagenes': ('rayos_x_new', 'rayos_x_detail'),
}.items():
    for name in names:
        VIEWS[name] = {'scope': scope, 'manual': True}

FINANCIAL_VIEWS = {'home', 'agenda_pro', 'agenda_week', 'agenda_month', 'agenda_calendar', 'patient_finances', 'patient_detail', 'patient_appointments', 'deudores_general', 'protesis_list', 'protesis_detail', 'budgets_list', 'budget_detail', 'patient_budgets', 'payments_list'}

def revision(scope):
    records = Activity.objects.all()
    if scope != 'actividad':
        records = records.exclude(section='Acceso')
    if SCOPES[scope] is not None:
        records = records.filter(section__in=SCOPES[scope])
    values = records.aggregate(count=Count('id'), latest=Max('id'))
    return f"{values['count']}:{values['latest'] or 0}"

def prepare(request, view_name):
    profile = VIEWS.get(view_name)
    if request.method == 'GET' and profile and request.user.is_authenticated:
        # Before the view reads any data, so a concurrent change isn't lost.
        request.sonrisar_live = {**profile, 'revision': revision(profile['scope']),
                                'periodic': 60000 if view_name in FINANCIAL_VIEWS else 0}
