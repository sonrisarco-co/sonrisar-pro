from django.urls import path
from . import views

urlpatterns = [
    path('', views.agenda_day, name='agenda_day'),
    path('agenda-pro/', views.agenda_pro, name='agenda_pro'),
    path('semana/', views.agenda_week, name='agenda_week'),
    path('mensual/', views.agenda_month, name='agenda_month'),
    path('dia/<int:day>/<int:month>/<int:year>/', views.agenda_day, name='agenda_day'),
    path('calendario/', views.agenda_calendario, name='agenda_calendar'),
    path('horarios/<int:year>/<int:month>/<int:day>/', views.agenda_horarios_dia, name='agenda_horarios_dia'),
    path('nueva/', views.appointment_new, name='appointment_new'),
    path('editar/<int:id>/', views.appointment_edit, name='appointment_edit'),
    path('eliminar/<int:id>/', views.appointment_delete, name='appointment_delete'),
    path('mover/<int:id>/', views.appointment_move_time, name='appointment_move_time'),
]