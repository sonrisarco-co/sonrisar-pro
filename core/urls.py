from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views
from core.views import budget_print
from core.views import protesis_print




urlpatterns = [

    # =====================
    # HOME
    # =====================
    path("", views.home, name="home"),


    # =====================
    # PACIENTES
    # =====================
    path("pacientes/", views.patient_list, name="patient_list"),
    path("pacientes/nuevo/", views.patient_new, name="patient_new"),
    path("pacientes/<int:id>/", views.patient_detail, name="patient_detail"),
    path("pacientes/editar/<int:id>/", views.patient_edit, name="patient_edit"),
    path("pacientes/eliminar/<int:id>/", views.patient_delete, name="patient_delete"),
    path("paciente/<int:patient_id>/citas/", views.patient_appointments, name="patient_appointments"),
    path("paciente/<int:patient_id>/presupuestos/", views.patient_budgets, name="patient_budgets"),
    path("pacientes/quick-new/", views.patient_quick_new, name="patient_quick_new"),


    

    # =====================
    # 📅 CITAS / AGENDA
    # =====================

    path("agenda/", views.agenda_hoy, name="agenda"),
    path("agenda/agenda-pro/", views.agenda_pro, name="agenda_pro"),
    path("agenda/semana/", views.agenda_week, name="agenda_week"),
    path("agenda/mensual/", views.agenda_month, name="agenda_month"),

    path(
        "agenda/dia/<int:day>/<int:month>/<int:year>/",
        views.agenda_day,
        name="agenda_day"
    ),
    
    # ✅ CALENDARIO GRILLA REAL

    path("agenda/calendario/", views.agenda_mensual_calendario, name="agenda_calendar"),

    path(
        "agenda/horarios/<int:year>/<int:month>/<int:day>/",
        views.agenda_horarios_dia,
        name="agenda_horarios_dia",
    ),


    # CRUD de citas
    path("agenda/nueva/", views.appointment_new, name="appointment_new"),
    path("agenda/editar/<int:id>/", views.appointment_edit, name="appointment_edit"),
    path("agenda/eliminar/<int:id>/", views.appointment_delete, name="appointment_delete"),
    path(
        "agenda/cobrar/<int:appointment_id>/",
        views.cobros_nuevo_desde_cita,
        name="cobros_nuevo_desde_cita"
    ),
    path(
        "pacientes/<int:patient_id>/cobrar/",
        views.cobros_nuevo_desde_paciente,
        name="cobros_nuevo_desde_paciente"
    ),

    path("agenda/mover/<int:id>/", views.appointment_move_time, name="appointment_move_time"),
    
    # =========================
    # HISTORIA CLÍNICA
    # =========================

    path("historia/", views.clinical_record_search, name="clinical_record_search"),

    path(
        "historia/registros/<int:patient_id>/",
        views.clinical_records_list,
        name="clinical_records_list",
    ),

    path(
        "historia/abrir/<int:patient_id>/",
        views.abrir_historia_desde_cita,
        name="abrir_historia_desde_cita",
    ),

    path(
        "historia/abrir-desde-cita/<int:patient_id>/<int:appointment_id>/",
        views.clinical_record_open_from_appointment,
        name="clinical_record_open_from_appointment",
    ),

    path(
        "historia/registro/nuevo/<int:patient_id>/",
        views.clinical_record_new,
        name="clinical_record_new",
    ),

    path(
        "historia/registro/<int:registro_id>/",
        views.clinical_record_detail,
        name="clinical_record_detail",
    ),

    path(
        "historia/registro/editar/<int:registro_id>/",
        views.clinical_record_edit,
        name="clinical_record_edit",
    ),

    path(
        "historia/registro/eliminar/<int:registro_id>/",
        views.clinical_record_delete,
        name="clinical_record_delete",
    ),

    path("dashboard-asistencia/", views.dashboard_asistencia, name="dashboard_asistencia"),



    # =====================
    # PRESUPUESTOS
    # =====================
    path("presupuestos/", views.budgets_list, name="budgets_list"),
    path("presupuestos/nuevo/<int:paciente_id>/", views.budget_new, name="budget_new"),
    path("presupuestos/editar/<int:id>/", views.budget_edit, name="budget_edit"),
    path("budgets/<int:id>/delete/", views.budget_delete, name="budget_delete"),
    path("presupuestos/pdf/<int:id>/", views.budget_print, name="budget_print"),
    path("budgets/<int:id>/", views.budget_detail, name="budget_detail"),
    path("budgets/<int:id>/add-payment/", views.budget_add_payment, name="budget_add_payment"),
    path("budgets/<int:id>/change-status/", views.budget_change_status, name="budget_change_status"),
    path("budget-payments/<int:payment_id>/receipt/", views.budget_payment_receipt, name="budget_payment_receipt"),
    path("budget-payments/<int:payment_id>/delete/", views.budget_payment_delete, name="budget_payment_delete"),


    # =====================
    # PAGOS
    # =====================
    path("pagos/", views.payments_list, name="payments_list"),
    path(
        "confirmar-pago-desde-cobros/",
        views.confirmar_pago_desde_cobros,
        name="confirmar_pago_desde_cobros",
    ),

    # =====================
    # WHATSAPP recordatorios
    # =====================
    path("whatsapp/", views.whatsapp_reminders, name="whatsapp_reminders"),
    path("whatsapp/iniciar/", views.iniciar_recordatorios_manana, name="iniciar_recordatorios_manana"),
    path("whatsapp/siguiente/", views.siguiente_recordatorio, name="siguiente_recordatorio"),
    path("whatsapp/confirmar/", views.confirmar_envio, name="confirmar_envio"),
    path("whatsapp/enviar/<int:id>/", views.cita_recordatorio, name="cita_recordatorio"),
    path("whatsapp/paciente/<int:id>/", views.whatsapp_paciente, name="whatsapp_paciente"),
    path("test-whatsapp/", views.test_whatsapp, name="test_whatsapp"),

    # =====================
    # RAYOS X
    # =====================
    path(
        "pacientes/<int:paciente_id>/rayos-x/",
        views.rayos_x_list,
        name="rayos_x_list",
    ),

    path(
        "pacientes/<int:paciente_id>/rayos-x/nuevo/",
        views.rayos_x_new,
        name="rayos_x_new",
    ),

    path(
        "rayos-x/<int:rx_id>/",
        views.rayos_x_detail,
        name="rayos_x_detail",
    ),

    path(
        "rayos-x/eliminar/<int:rx_id>/",
        views.rayos_x_delete,
        name="rayos_x_delete",
    ),


    # ======================
    # INVENTARIO
    # ======================
    path("inventario/", views.inventory_list, name="inventory_list"),
    path("inventario/nuevo/", views.inventory_new, name="inventory_new"),
    path("inventario/editar/<int:pk>/", views.inventory_edit, name="inventory_edit"),
    path("inventario/eliminar/<int:pk>/", views.inventory_delete, name="inventory_delete"),


    # =====================
    # PRÓTESIS
    # =====================

    path("protesis/", views.protesis_list, name="protesis_list"),
    path("protesis/nueva/", views.protesis_new, name="protesis_new"),
    path("protesis/editar/<int:id>/", views.protesis_edit, name="protesis_edit"),
    path("protesis/eliminar/<int:id>/", views.protesis_delete, name="protesis_delete"),
    path("protesis/ver/<int:id>/", views.protesis_detail, name="protesis_detail"),
    path("protesis/pdf/<int:id>/", views.protesis_print, name="protesis_print"),

    path("api/", include("core.api.urls")),

]

# =====================
# ARCHIVOS MEDIA
# =====================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
