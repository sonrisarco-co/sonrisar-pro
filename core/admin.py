from django.contrib import admin
from .models import Appointment, Patient

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("paciente", "fecha", "hora", "monto_total")

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("apellido", "nombre")