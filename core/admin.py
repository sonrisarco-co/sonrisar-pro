"""Read-only inventory for reviewing patient links; this is not a backup."""
import hashlib
import json

from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone


def download_inventory(request, models, source):
    if not request.user.is_active or not request.user.is_superuser:
        raise PermissionDenied
    tables = {}
    with transaction.atomic():
        for model in models:
            fields = [field.attname for field in model._meta.concrete_fields]
            rows = []
            for record in model.objects.order_by(model._meta.pk.name).values(*fields).iterator():
                encoded = json.dumps(record, cls=DjangoJSONEncoder, sort_keys=True,
                                     ensure_ascii=False, separators=(",", ":"))
                # Keep clinical free text and fiscal XML out of the inventory.
                visible = {key: value for key, value in record.items()
                           if key == model._meta.pk.attname or key.endswith("_id")
                           or key in ("nombre", "apellido", "ci", "telefono", "paciente",
                                      "monto", "monto_total", "total", "fecha", "estado",
                                      "pieza", "cara", "numero", "tipo", "categoria")}
                visible["record_sha256"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
                rows.append(visible)
            tables[model._meta.label_lower] = {"count": len(rows), "records": rows}
    response = JsonResponse({
        "format": "sonrisar-patient-inventory-v1", "source": source,
        "generated_at": timezone.now(), "is_backup": False,
        "note": "Solo inventario. No contiene historias ni archivos completos. "
                "Puede reflejar cambios concurrentes; no usar como respaldo.",
        "tables": tables,
    }, json_dumps_params={"ensure_ascii": False, "indent": 2})
    response["Content-Disposition"] = f'attachment; filename="diagnostico-{source}.json"'
    response["Cache-Control"] = "no-store"
    return response


import csv
from django.apps import apps

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
    search_fields = ("nombre", "apellido", "ci", "telefono")
    search_help_text = "Buscar por nombre, apellido, cédula o teléfono."
    change_list_template = "admin/core/patient/change_list.html"

    def get_urls(self):
        return [
            path("diagnostico/", self.admin_site.admin_view(self.export_inventory),
                 name="core_patient_inventory"),
            path("exportar-csv/", self.admin_site.admin_view(self.export_csv),
                 name="core_patient_export_csv"),
        ] + super().get_urls()

    def export_inventory(self, request):
        return download_inventory(request, apps.get_app_config("core").get_models(), "pro")

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


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    search_fields = (
        "paciente__nombre", "paciente__apellido", "paciente__ci", "paciente__telefono",
    )
    search_help_text = "Buscar citas por nombre, apellido, cédula o teléfono del paciente."
    list_select_related = ("paciente",)


admin.site.register(Payment)
admin.site.register(Budget)
admin.site.register(BudgetItem)
admin.site.register(Prosthesis)
admin.site.register(Inventory)

admin.site.site_header = "SONRISAR ADMIN OK"
admin.site.index_title = "MODELOS CARGADOS"
