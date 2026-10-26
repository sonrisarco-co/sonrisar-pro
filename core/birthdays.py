"""Cumpleaños y confirmación manual de saludos; abrir WhatsApp no registra un envío."""
import re
from urllib.parse import urlencode, quote
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .models import Patient, BirthdayGreeting

MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def use_whatsapp_web(request):
    agent = request.META.get("HTTP_USER_AGENT", "").lower()
    return not any(device in agent for device in ("android", "iphone", "ipad", "ipod", "mobile", "macintosh"))


def birthday_rows(month, day=None, whatsapp_web=False):
    today = timezone.localdate()
    patients = Patient.objects.filter(fecha_nacimiento__month=month)
    if day is not None:
        patients = patients.filter(fecha_nacimiento__day=day)
    greetings = {g.paciente_id: g for g in BirthdayGreeting.objects.filter(year=today.year).select_related("marcado_por")}
    rows = []
    for patient in patients.order_by("fecha_nacimiento__day", "apellido", "nombre"):
        phone = re.sub(r"\D", "", patient.telefono or "")
        if phone.startswith("00"):
            phone = phone[2:]
        if len(phone) == 9 and phone.startswith("0"):
            phone = "598" + phone[1:]
        elif len(phone) == 8 and phone.startswith("9"):
            phone = "598" + phone
        valid_phone = 8 <= len(phone) <= 15 and not phone.startswith("0")
        message = (f"¡Muy feliz cumple! {patient.nombre} 🥳🎂\n\n"
                   "Hoy queremos saludarte desde Sonrisar y desearte que pases un día espectacular, lleno de alegría y lindos momentos.\n\n"
                   "¡Que tengas un hermoso día y lo disfrutes mucho!\n\n"
                   "Un abrazo de todo el equipo de Sonrisar. 💙")
        rows.append({"patient": patient, "age": today.year - patient.fecha_nacimiento.year,
                     "greeting": greetings.get(patient.pk),
                     "whatsapp_url": (("https://web.whatsapp.com/send?" + urlencode({"phone": phone, "text": message}, quote_via=quote))
                                      if whatsapp_web else ("https://wa.me/" + phone + "?" + urlencode({"text": message}, quote_via=quote))) if valid_phone else ""})
    return rows


@login_required
def birthdays(request):
    today = timezone.localdate()
    try:
        month = int(request.GET.get("mes", today.month))
        if not 1 <= month <= 12:
            raise ValueError
    except (ValueError, TypeError):
        month = today.month
    return render(request, "core/birthdays.html", {"rows": birthday_rows(month, whatsapp_web=use_whatsapp_web(request)), "month": month,
                  "months": list(enumerate(MONTHS, 1)), "year": today.year})


@login_required
@require_POST
def mark_greeting(request, id):
    patient = get_object_or_404(Patient, pk=id, fecha_nacimiento__isnull=False)
    today = timezone.localdate()
    # Only current/past birthdays in this year may be confirmed.
    if (patient.fecha_nacimiento.month, patient.fecha_nacimiento.day) > (today.month, today.day):
        messages.error(request, "Todavía no llegó el cumpleaños de este año.")
    else:
        _, created = BirthdayGreeting.objects.get_or_create(paciente=patient, year=today.year,
                                                           defaults={"marcado_por": request.user})
        messages.success(request, "Saludo marcado como enviado." if created else "Este saludo ya estaba registrado.")
    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()):
        target = reverse("birthdays")
    return redirect(target or reverse("birthdays"))
