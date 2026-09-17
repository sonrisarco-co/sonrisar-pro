import csv

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.urls import path
from .models import (
    Patient,
    Appointment,
    Payment,
    Budget,
    BudgetItem,
    Prosthesis,
    Inventory,
)

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    change_list_template = "admin/core/patient/change_list.html"

    def get_urls(self):
        return [
            path("exportar-csv/", self.admin_site.admin_view(self.export_csv),
                 name="core_patient_export_csv"),
        ] + super().get_urls()

    def export_csv(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="pacientes.csv"'
        response.write("\ufeff")
        writer = csv.writer(response, delimiter=";")
        writer.writerow(["ID", "Nombre", "Apellido", "Cedula", "Telefono"])
        patients = self.get_queryset(request).order_by("pk").values_list(
            "pk", "nombre", "apellido", "ci", "telefono"
        )
        for row in patients.iterator():
            # Prevent patient text from becoming a formula when opened in Excel.
            writer.writerow([
                "'" + value if isinstance(value, str) and
                (value.lstrip().startswith(("=", "+", "-", "@")) or
                 value.startswith(("\t", "\r", "\n"))) else value
                for value in row
            ])
        return response


admin.site.register(Appointment)
admin.site.register(Payment)
admin.site.register(Budget)
admin.site.register(BudgetItem)
admin.site.register(Prosthesis)
admin.site.register(Inventory)

admin.site.site_header = "SONRISAR ADMIN OK"
admin.site.index_title = "MODELOS CARGADOS"
