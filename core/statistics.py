"""Estadísticas de citas: una cita asistida cuenta una vez por su motivo."""
from datetime import date
from django.db.models import Count, Min
from django.db.models.functions import ExtractMonth
from django.utils import timezone
from .models import Appointment, Patient, Prosthesis

MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
          "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
REASONS = ["Colocación nueva", "Ajuste (ortodoncia)", "Ajuste + limpieza", "Prótesis",
           "Extracción", "Resina", "Limpieza", "Valoración", "Endodoncia", "Blanqueamiento",
           "Segunda colocación + ajuste", "Segunda colocación", "Provisorio", "Contenciones",
           "Placa NMR", "Control", "Corona", "Puente fijo", "Despegados", "Retiro de brackets", "Urgencia"]


def statistics_context(params):
    today = timezone.localdate()
    warning = ""
    try:
        year = int(params.get("anio", today.year))
        month = int(params.get("mes", today.month))
        if not 1900 <= year <= 9998 or not 1 <= month <= 12:
            raise ValueError
    except (ValueError, TypeError):
        year, month = today.year, today.month
        warning = "El período ingresado no es válido. Se muestra el mes actual."
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    previous = date(year - (month == 1), 12 if month == 1 else month - 1, 1)
    appointments = Appointment.objects.filter(fecha__gte=start, fecha__lt=end)
    attended = appointments.filter(estado="asistio")
    counts = dict(attended.values("motivo").annotate(n=Count("pk")).values_list("motivo", "n"))
    reasons = [{"motivo": reason, "total": counts.get(reason, 0)}
               for reason in REASONS + sorted(set(counts) - set(REASONS))]
    first_dates = list(Appointment.objects.filter(estado="asistio").order_by()
                       .values("paciente_id").annotate(first=Min("fecha"))
                       .values_list("first", flat=True))
    annual_counts = {}
    for row in Appointment.objects.filter(fecha__year=year, estado="asistio").annotate(
            month=ExtractMonth("fecha")).values("month", "motivo").annotate(n=Count("pk")):
        annual_counts[(row["month"], row["motivo"])] = row["n"]
    extras = sorted({reason for _, reason in annual_counts} - {r["motivo"] for r in reasons})
    reasons.extend({"motivo": reason, "total": counts.get(reason, 0)} for reason in extras)
    annual = []
    for number, name in enumerate(MONTHS, 1):
        annual.append({"numero": number, "mes": name, "seleccionado": number == month,
                       "cantidades": [annual_counts.get((number, r["motivo"]), 0) for r in reasons],
                       "total": sum(n for (m, _), n in annual_counts.items() if m == number),
                       "nuevos": sum(d.year == year and d.month == number for d in first_dates)})
    prostheses = Prosthesis.objects.filter(fecha_inicio__gte=start, fecha_inicio__lt=end)
    prosthesis_states = dict(prostheses.values("estado").annotate(n=Count("pk")).values_list("estado", "n"))
    adjustments = counts.get("Ajuste (ortodoncia)", 0)
    adjustment_patients = attended.filter(motivo="Ajuste (ortodoncia)").values("paciente_id").distinct().count()
    summary = [
        ("Citas agendadas", appointments.count(), "Todos los estados"),
        ("Citas asistidas", attended.count(), "Estado: Asistió"),
        ("Pacientes atendidos", attended.values("paciente_id").distinct().count(), "Personas distintas en el mes"),
        ("Pacientes de primera vez", sum(start <= d < end for d in first_dates), "Primera cita asistida de su historial"),
        ("Ausencias", appointments.filter(estado="no_asistio").count(), "Estado: No asistió"),
        ("Cancelaciones", appointments.filter(estado="cancelado").count(), "Estado: Cancelado"),
    ]
    return {"anio": year, "mes": month, "periodo": f"{MONTHS[month-1]} de {year}",
            "meses": list(enumerate(MONTHS, 1)), "hoy": today, "anterior": previous, "siguiente": end,
            "aviso": warning, "resumen": summary, "motivos": reasons, "anual": annual,
            "total_pacientes": Patient.objects.count(), "total_protesis": prostheses.count(),
            "estados_protesis": [(label, prosthesis_states.get(value, 0)) for value, label in Prosthesis.ESTADOS_PROTESIS],
            "ajustes": adjustments, "pacientes_ajustes": adjustment_patients,
            "promedio_ajustes": round(adjustments / adjustment_patients, 2) if adjustment_patients else 0}
