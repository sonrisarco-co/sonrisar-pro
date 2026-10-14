Warning: truncated output (original token count: 50511)
Total output lines: 6471

from django.shortcuts import render, redirect, get_object_or_404
from datetime import date, time, timedelta, datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.utils.text import slugify

import calendar
#from core.models import Cita
from django.db.models import Q, F, Max, Min, Sum, OuterRef, Subquery
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib import messages

from django.conf import settings
from urllib.parse import urlencode, quote, urlsplit, parse_qsl

from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from django.utils.http import urlencode, url_has_allowed_host_and_scheme

from django.contrib import messages

from django.core.paginator import Paginator
from django.core.cache import cache

from django.http import HttpResponse
from django.template.loader import get_template
import pdfkit

from django.utils.timezone import localdate, now
from django.utils import timezone
from django.utils.timezone import localtime

from calendar import monthrange

from django.views.decorators.http import require_POST

from decimal import Decimal, InvalidOperation

import json
from urllib.request import urlopen
from urllib.error import URLError, HTTPError




from .models import (
    Patient,
    Appointment,
    Procedure,
    ClinicalRecord,
    Budget,
    BudgetItem,
    Payment,
    Prosthesis,
    OrdenLaboratorio,
    Inventory,
    InventoryMovement,
    ClinicalRecord,
    RayosX,
    BudgetPayment,
    BudgetAdjustment,
    BudgetCreditTransfer,
    OdontogramTooth,
    OdontogramaCara,
    DayBlock,
    TimeBlock,
    AgendaReminder,
    ClinicalAlert,
)

from .forms import (
    PatientForm,
    AppointmentForm,
    ClinicalRecordForm,
    BudgetForm,
    InventoryForm,
    InventoryMovementForm,
    ProsthesisForm,
    OrdenLaboratorioForm,
    RayosXForm,
    BudgetPaymentForm,
)


# =============================
# 🌟 PANEL PRINCIPAL
# =============================
from django.db.models import Count

def home(request):
    today = date.today()

    primera_cita_paciente = (
        Appointment.objects
        .filter(paciente_id=OuterRef("paciente_id"))
        .order_by("fecha", "hora", "id")
        .values("id")[:1]
    )

    citas_hoy = list(
        Appointment.objects
        .filter(fecha=today)
        .annotate(primera_cita_id=Subquery(primera_cita_paciente))
        .select_related("paciente")
        .prefetch_related("procedimientos")
        .order_by("hora", "id")
    )

    pacientes_primera_vez_hoy = sum(
        1 for cita in citas_hoy if cita.id == cita.primera_cita_id
    )
    citas_hoy_pendientes = sum(cita.estado == "pendiente" for cita in citas_hoy)
    citas_hoy_confirmadas = sum(cita.estado == "confirmado" for cita in citas_hoy)
    citas_hoy_atendidas = sum(cita.estado == "asistio" for cita in citas_hoy)

    contextos_financieros_hoy = _obtener_contexto_financiero_citas(
        citas_hoy,
        today,
    ) if citas_hoy else {}

    total_cobrado_hoy = sum(
        (
            _decimal_seguro(contextos_financieros_hoy.get(cita.id, {}).get("pago_cita", 0))
            for cita in citas_hoy
        ),
        Decimal("0"),
    )
    deuda_por_paciente = {}
    for cita in citas_hoy:
        deuda_por_paciente[cita.paciente_id] = _decimal_seguro(
            contextos_financieros_hoy.get(cita.id, {}).get("deuda_cita", 0)
        )
    deuda_pendiente_hoy = sum(
        (max(deuda, Decimal("0")) for deuda in deuda_por_paciente.values()),
        Decimal("0"),
    )

    citas_futuras = (
        Appointment.objects
        .filter(fecha__gt=today)
        .exclude(estado="cancelado")
    )
    proxima_fecha = citas_futuras.order_by("fecha").values_list("fecha", flat=True).first()
    proximas_citas = list(
        citas_futuras
        .filter(fecha=proxima_fecha)
        .select_related("paciente")
        .prefetch_related("procedimientos")
        .order_by("hora", "id")
    )

    alertas_clinicas = list(
        ClinicalAlert.objects
        .filter(realizado=False)
        .select_related("paciente")
        .order_by("fecha_revision", "-creado")[:6]
    )
    alertas_administrativas = list(
        AgendaReminder.objects
        .filter(realizado=False)
        .select_related("paciente")
        .order_by("fecha", "-id")[:6]
    )

    month = int(request.GET.get("month", today.month))
    year = int(request.GET.get("year", today.year))

    citas = Appointment.objects.filter(
        fecha__year=year,
        fecha__month=month
    )

    total = citas.count()
    asistieron = citas.filter(estado="asistio").count()
    no_asistieron = citas.filter(estado="no_asistio").count()
    confirmados = citas.filter(estado="confirmado").count()
    cancelados = citas.filter(estado="cancelado").count()
    pendientes = citas.filter(estado="pendiente").count()

    porcentaje = 0
    if total > 0:
        porcentaje = round((asistieron / total) * 100, 1)

    ausentismo_real = 0
    total_con_resultado = asistieron + no_asistieron

    if total_con_resultado > 0:
        ausentismo_real = round(
            (no_asistieron / total_con_resultado) * 100,
            1
        )

    ranking = (
        citas.filter(estado="no_asistio")
        .values("paciente__apellido", "paciente__nombre")
        .annotate(faltas=Count("id"))
        .order_by("-faltas")
    )

    prev_month = month - 1 if month > 1 else 12
    prev_year = year - 1 if month == 1 else year

    next_month = month + 1 if month < 12 else 1
    next_year = year + 1 if month == 12 else year

    context = {
        "today": today,
        "citas_hoy": citas_hoy,
        "total_citas_hoy": len(citas_hoy),
        "pacientes_primera_vez_hoy": pacientes_primera_vez_hoy,
        "citas_hoy_pendientes": citas_hoy_pendientes,
        "citas_hoy_confirmadas": citas_hoy_confirmadas,
        "citas_hoy_atendidas": citas_hoy_atendidas,
        "total_cobrado_hoy": total_cobrado_hoy,
        "deuda_pendiente_hoy": deuda_pendiente_hoy,
        "proximas_citas": proximas_citas,
        "proxima_fecha": proxima_fecha,
        "alertas_clinicas": alertas_clinicas,
        "alertas_administrativas": alertas_administrativas,
        "total": total,
        "asistieron": asistieron,
        "no_asistieron": no_asistieron,
        "confirmados": confirmados,
        "cancelados": cancelados,
        "pendientes": pendientes,
        "porcentaje": porcentaje,
        "ausentismo_real": ausentismo_real,
        "month": month,
        "year": year,
        "ranking": ranking,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
    }

    return render(request, "core/home.html", context)




# =========================
# PACIENTES (COMPLETO)
# =========================


def patient_list(request):
    from activity.live import patients_revision
    live_revision = patients_revision()

    # 🔍 Buscar por nombre, apellido, CI o teléfono
    query = request.GET.get("q", "")

    pacientes_queryset = Patient.objects.all().order_by("nombre")

    if query:
        pacientes_queryset = pacientes_queryset.filter(
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query) |
            Q(ci__icontains=query) |
            Q(telefono__icontains=query)
        )

    # 📄 Paginación (20 por página)
    paginator = Paginator(pacientes_queryset, 20)
    page_number = request.GET.get("page")
    pacientes = paginator.get_page(page_number)

    # 🕒 Contador de pacientes inactivos
    fecha_limite = timezone.now().date() - timedelta(days=90)

    cantidad_inactivos = Patient.objects.annotate(
        ultima_cita=Max("appointment__fecha")
    ).filter(
        ultima_cita__isnull=False,
        ultima_cita__lt=fecha_limite
    ).count()

    return render(
        request,
        "core/patients_list.html",
        {
            "patients_live_revision": live_revision,
            "pacientes": pacientes,
            "query": query,
            "cantidad_inactivos": cantidad_inactivos,
        }
    )



def _obtener_resumen_financiero_ficha(paciente):
    """
    Resumen financiero liviano para la Ficha del paciente.

    Usa exactamente la misma fuente rápida por patient_id que Agenda del día
    y Pacientes deudores, evitando inconsistencias entre pantallas.

    Rendimiento:
    - Una sola consulta HTTP a Sonrisar Cobros.
    - No consulta cita por cita.
    - No hace búsquedas repetidas por nombre.
    """
    resumen_cobros = obtener_resumen_cobros_paciente(paciente)

    disponible = bool(resumen_cobros.get("ok"))
    total_pagado = _decimal_seguro(
        resumen_cobros.get("total_pagado", 0)
    )

    total_cobrable = obtener_total_cobrable_paciente_desde_pro(paciente)
    deuda = total_cobrable - total_pagado

    if deuda < 0:
        deuda = Decimal("0")

    return {
        "disponible": disponible,
        "error": resumen_cobros.get("error"),
        "deuda": deuda,
        "sin_deuda": deuda <= 0,
        "total_pagado": total_pagado,

        # El endpoint rápido devuelve el total consolidado, no el detalle
        # del último movimiento. Dejamos estos campos vacíos para que el
        # template muestre el total pagado registrado sin inventar datos.
        "ultimo_pago": None,
        "recibo_url": "",
    }


def _patients_return_url(value):
    """Accept only the local patient list, retaining search and pagination."""
    try:
        target = urlsplit(value or "")
    except ValueError:
        return ""
    if target.scheme or target.netloc or target.path != reverse("patient_list"):
        return ""
    return target.path + ("?" + target.query if target.query else "")


def patient_detail(request, id):
    from django.urls import resolve, Resolver404
    from django.utils.http import url_has_allowed_host_and_scheme

    return_url = request.GET.get("next", "")
    return_label = "Volver"
    if not url_has_allowed_host_and_scheme(return_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return_url = ""
    if return_url:
        try:
            origin_view = resolve(urlsplit(return_url).path).url_name
            if origin_view == "agenda_day":
                return_label = "Volver a la agenda"
            elif origin_view == "agenda_pro":
                return_label = "Volver al calendario"
        except (Resolver404, ValueError):
            pass
    paciente = get_object_or_404(Patient, id=id)

    hoy = timezone.localdate()
    hora_actual = timezone.localtime().time()
    edad = calcular_edad(paciente.fecha_nacimiento)

    citas_paciente = (
        Appointment.objects
        .filter(paciente=paciente)
        .exclude(estado="cancelado")
        .prefetch_related("procedimientos")
    )

    ultima_cita = (
        citas_paciente
        .filter(
            Q(fecha__lt=hoy) |
            Q(fecha=hoy, hora__lte=hora_actual)
        )
        .order_by("-fecha", "-hora")
        .first()
    )

    proxima_cita = (
        citas_paciente
        .filter(
            Q(fecha__gt=hoy) |
            Q(fecha=hoy, hora__gt=hora_actual)
        )
        .order_by("fecha", "hora")
        .first()
    )

    resumen_financiero = _obtener_resumen_financiero_ficha(paciente)

    return render(
        request,
        "core/patient_detail.html",
        {
            "paciente": paciente,
            "edad": edad,
            "ultima_cita": ultima_cita,
            "proxima_cita": proxima_cita,
            "resumen_financiero": resumen_financiero,
            "patients_return_url": _patients_return_url(request.GET.get("next")) or reverse("patient_list"),
            "detail_return_url": return_url,
            "detail_return_label": return_label,
        },
    )


def patient_appointments(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)

    citas = Appointment.objects.filter(
        paciente=paciente
    ).order_by("fecha", "hora")

    return render(request, "core/patient_appointments.html", {
        "paciente": paciente,
        "citas": citas,
    })



def patient_new(request):

    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.method == "POST":
        ci = request.POST.get("ci", "").strip()
        telefono = request.POST.get("telefono", "").strip()

        if not ci or not telefono:
            messages.error(request, "La cédula y el teléfono son obligatorios.")
            return render(request, "core/patient_new.html", {
                "next": next_url,
                "form_data": request.POST,
            })

        paciente = Patient.objects.create(
            nombre=request.POST.get("nombre", "").strip(),
            apellido=request.POST.get("apellido", "").strip(),
            ci=ci,
            fecha_nacimiento=request.POST.get("fecha_nacimiento") or None,
            telefono=telefono,
            email=request.POST.get("email", "").strip(),
            direccion=request.POST.get("direccion", "").strip(),
        )

        # 🔁 volver a donde estaba (agenda)
        if next_url:
            sep = "&" if "?" in next_url else "?"
            return redirect(f"{next_url}{sep}paciente_id={paciente.id}")

        return redirect("patient_list")

    return render(request, "core/patient_new.html", {
        "next": next_url
    })

from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string

@require_http_methods(["GET", "POST"])
def patient_quick_new(request):
    """
    Crear paciente desde un modal (AJAX).
    GET  -> devuelve HTML del formulario
    POST -> crea paciente y devuelve JSON con id + texto
    """
    if request.method == "POST":
        ci = request.POST.get("ci", "").strip()
        telefono = request.POST.get("telefono", "").strip()

        if not ci or not telefono:
            return JsonResponse({
                "success": False,
                "error": "La cédula y el teléfono son obligatorios.",
            }, status=400)

        paciente = Patient.objects.create(
            nombre=request.POST.get("nombre", "").strip(),
            apellido=request.POST.get("apellido", "").strip(),
            ci=ci,
            fecha_nacimiento=request.POST.get("fecha_nacimiento") or None,
            telefono=telefono,
            email=request.POST.get("email", "").strip(),
            direccion=request.POST.get("direccion", "").strip(),
        )

        return JsonResponse({
            "success": True,
            "id": paciente.id,
            "text": f"{paciente.apellido}, {paciente.nombre}"
        })

    # GET: devolvemos el formulario HTML para el modal
    html = render_to_string("core/patient_quick_form.html", {}, request=request)
    return JsonResponse({"success": True, "html": html})



def patient_edit(request, id):
    paciente = get_object_or_404(Patient, id=id)

    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        ci = request.POST.get("ci", "").strip()
        telefono = request.POST.get("telefono", "").strip()

        if not ci or not telefono:
            messages.error(request, "La cédula y el teléfono son obligatorios.")
            return render(request, "core/patient_edit.html", {
                "paciente": paciente,
                "next": next_url,
                "form_data": request.POST,
            })

        paciente.nombre = request.POST.get("nombre", "").strip()
        paciente.apellido = request.POST.get("apellido", "").strip()
        paciente.ci = ci
        paciente.fecha_nacimiento = request.POST.get("fecha_nacimiento") or None
        paciente.telefono = telefono
        paciente.email = request.POST.get("email", "").strip()
        paciente.direccion = request.POST.get("direccion", "").strip()
        paciente.save()

        if next_url:
            return redirect(
                f"{reverse('patient_detail', args=[paciente.id])}?next={quote(next_url)}"
            )

        return redirect("patient_detail", id=paciente.id)

    return render(
        request,
        "core/patient_edit.html",
        {
            "paciente": paciente,
            "next": next_url,
        }
    )



def patient_delete(request, id):
    paciente = get_object_or_404(Patient, id=id)

    if request.method == "POST":
        paciente.delete()
        return redirect("patient_list")

    return render(request, "core/patient_delete.html", {"paciente": paciente})



# =============================
# 📅 CITAS / AGENDA
# =============================
def citas_list(request):
    citas = Appointment.objects.all().order_by("fecha", "hora")
    return render(request, "core/citas.html", {"citas": citas})


from django.urls import reverse


def _calendar_saved_appointment_url(next_url, cita):
    """Return to the saved appointment, including when its date/time changed."""
    target = urlsplit(next_url)
    if target.scheme or target.netloc or target.path != reverse("agenda_pro"):
        return next_url
    params = dict(parse_qsl(target.query, keep_blank_values=True))
    params["fecha"] = cita.fecha.isoformat()
    params["mini_fecha"] = cita.fecha.isoformat()
    # A previous patient search may hide the saved appointment.
    params.pop("q", None)
    return f"{target.path}?{urlencode(params)}#cita-{cita.pk}"


def appointment_new(request):
    fecha = request.GET.get("fecha")
    hora = request.GET.get("hora")
    paciente_id = request.GET.get("paciente_id")

    next_url = request.GET.get("next") or request.POST.get("next")

    if not next_url:
        next_url = reverse("agenda_calendar")

    initial_data = {}

    if fecha:
        initial_data["fecha"] = fecha

    if hora:
        initial_data["hora"] = hora

    if paciente_id:
        initial_data["paciente"] = paciente_id

    # 🚫 VALIDAR HORARIOS BLOQUEADOS (14:00 y 14:30 solo de lunes a viernes)
    fecha_obj = None
    if fecha:
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
        except Exception:
            fecha_obj = None

    if hora in ["14:00", "14:15", "14:30", "14:45"] and fecha_obj and fecha_obj.weekday() != 5:
        messages.error(request, "Ese horario está bloqueado.")
        return redirect(next_url)

    # 🚫 VALIDAR DÍA BLOQUEADO
    if fecha_obj:
        try:
            if DayBlock.objects.filter(fecha=fecha_obj).exists():
                messages.error(request, "Ese día está bloqueado.")
                return redirect(next_url)

            # 🚫 VALIDAR HORARIO BLOQUEADO MANUALMENTE
            if hora:
                try:
                    hora_obj = datetime.strptime(hora, "%H:%M").time()
                    if TimeBlock.objects.filter(fecha=fecha_obj, hora=hora_obj).exists():
                        messages.error(request, "Ese horario está bloqueado.")
                        return redirect(next_url)
                except ValueError:
                    pass

        except Exception:
            pass

    if request.method == "POST":
        form = AppointmentForm(request.POST)

        if form.is_valid():

            nueva_cita = form.save(commit=False)

            # 🚫 VALIDAR HORARIO EN POST
            hora_cita = nueva_cita.hora.strftime("%H:%M")

            if hora_cita in ["14:00", "14:15", "14:30", "14:45"] and nueva_cita.fecha.weekday() != 5:
                messages.error(request, "Ese horario está bloqueado.")
                return redirect(next_url)

            # 🚫 VALIDAR DÍA BLOQUEADO
            if DayBlock.objects.filter(fecha=nueva_cita.fecha).exists():
                messages.error(request, "Ese día está bloqueado.")
                return redirect(next_url)

            # 🚫 VALIDAR HORARIO BLOQUEADO MANUALMENTE
            if TimeBlock.objects.filter(
                fecha=nueva_cita.fecha,
                hora=nueva_cita.hora
            ).exists():
                messages.error(request, "Ese horario está bloqueado.")
                return redirect(next_url)

            # Avisar antes de crear otra cita del paciente en el mismo mes.
            from django.core import signing

            citas_mes = list(
                Appointment.objects.filter(
                    paciente_id=nueva_cita.paciente_id,
                    fecha__year=nueva_cita.fecha.year,
                    fecha__month=nueva_cita.fecha.month,
                ).exclude(estado="cancelado").order_by("fecha", "hora", "id")
            )
            if citas_mes:
                referencia = (
                    str(nueva_cita.paciente_id) + ":" +
                    nueva_cita.fecha.isoformat() + ":" +
                    ",".join(str(c.pk) for c in citas_mes)
                )
                confirmado = False
                try:
                    confirmado = (
                        signing.Signer(salt="citas-mismo-mes").unsign(
                            request.POST.get("confirmacion_citas_mes", "")
                        ) == referencia
                    )
                except signing.BadSignature:
                    pass

                if not confirmado:
                    datos = [
                        (nombre, valor)
                        for nombre, valores in request.POST.lists()
                        if nombre not in {
                            "csrfmiddlewaretoken", "confirmacion_citas_mes"
                        }
                        for valor in valores
                    ]
                    return render(
                        request,
                        "core/appointment_month_confirm.html",
                        {
                            "paciente": nueva_cita.paciente,
                            "fecha": nueva_cita.fecha,
                            "citas_mes": citas_mes,
                            "datos": datos,
                            "confirmacion_citas_mes": signing.Signer(
                                salt="citas-mismo-mes"
                            ).sign(referencia),
                            "next": next_url,
                        },
                    )

            nueva_cita.save()
            form.save_m2m()

            return redirect(_calendar_saved_appointment_url(next_url, nueva_cita))

    else:
        form = AppointmentForm(initial=initial_data)

    return render(
        request,
        "core/appointment_form.html",
        {
            "form": form,
            "next": next_url,
            "titulo": "Nueva cita",
        }
    )


def appointment_edit(request, id):
    cita = get_object_or_404(Appointment, id=id)

    next_url = request.GET.get("next") or request.POST.get("next")
    if not next_url:
        next_url = reverse("agenda_pro")

    # Al editar desde el calendario, vuelve a la misma fila horaria.
    volver_hora = request.GET.get("volver_hora")
    if volver_hora and "#hora-" not in next_url:
        try:
            hora_ancla = datetime.strptime(volver_hora, "%H:%M").strftime("%H%M")
            next_url = f"{next_url}#hora-{hora_ancla}"
        except ValueError:
            pass

    es_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        form = AppointmentForm(request.POST, instance=cita)

        if form.is_valid():
            cita = form.save()
            next_url = _calendar_saved_appointment_url(next_url, cita)

            if es_ajax:
                return JsonResponse({
                    "success": True,
                    "redirect_url": next_url
                })

            return redirect(next_url)

    else:
        form = AppointmentForm(instance=cita)

    template_name = "core/appointment_form_partial.html" if es_ajax else "core/appointment_form.html"

    return render(
        request,
        template_name,
        {
            "form": form,
            "titulo": "Editar Cita",
            "next": next_url,
        }
    )


@require_POST
def appointment_confirm(request, id):
    cita = get_object_or_404(Appointment, id=id)
    nuevo_estado = request.POST.get("estado", "confirmado")
    if nuevo_estado not in {"confirmado", "sin_respuesta"}:
        return JsonResponse({"success": False, "error": "Estado no válido."}, status=400)
    permitidos = {"pendiente", "En espera", "sin_respuesta"}
    if nuevo_estado == "sin_respuesta":
        permitidos.add("confirmado")
    if cita.estado not in permitidos:
        return JsonResponse({
            "success": False,
            "error": "Esta cita ya no está pendiente de confirmación.",
        }, status=409)
    cita.estado = nuevo_estado
    cita.save(update_fields=["estado"])
    return JsonResponse({"success": True, "estado": cita.get_estado_display()})


@require_POST
def appointment_attended(request, id):
    cita = get_object_or_404(Appointment, id=id)
    if cita.estado == "cancelado":
        return JsonResponse({"success": False, "error": "La cita está cancelada."}, status=409)
    cita.estado = "asistio"
    cita.save(update_fields=["estado"])
    return JsonResponse({"success": True, "estado": cita.get_estado_display()})


@require_POST
def appointment_no_show(request, id):
    cita = get_object_or_404(Appointment, id=id)
    if cita.estado == "cancelado":
        return JsonResponse({"success": False, "error": "La cita está cancelada."}, status=409)
    cita.estado = "no_asistio"
    cita.save(update_fields=["estado"])
    return JsonResponse({"success": True, "estado": cita.get_estado_display()})


@require_POST
def appointment_update_amount(request, id):
    cita = get_object_or_404(Appointment, id=id)
    monto_texto = (request.POST.get("monto_total") or "").strip()
    monto_texto = monto_texto.replace("$", "").replace(" ", "")

    if "," in monto_texto and "." in monto_texto:
        if monto_texto.rfind(",") > monto_texto.rfind("."):
            monto_texto = monto_texto.replace(".", "").replace(",", ".")
        else:
            monto_texto = monto_texto.replace(",", "")
    else:
        monto_texto = monto_texto.replace(",", ".")

    try:
        monto = Decimal(monto_texto).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return JsonResponse({
            "success": False,
            "error": "Ingresá un monto válido.",
        }, status=400)

    if monto < 0 or monto > Decimal("99999999.99"):
        return JsonResponse({
            "success": False,
            "error": "El monto debe estar entre $0 y $99.999.999,99.",
        }, status=400)

    cita.monto_total = monto
    cita.save(update_fields=["monto_total"])

    return JsonResponse({
        "success": True,
        "monto_total": str(monto),
    })


def appointment_delete(request, id):
    cita = get_object_or_404(Appointment, id=id)
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    fecha = cita.fecha

    if request.method == "POST":
        cita.delete()

        if next_url:
            return redirect(next_url)

        return redirect(
            "agenda_day",
            day=fecha.day,
            month=fecha.month,
            year=fecha.year
        )

    return render(request, "core/appointment_confirm_delete.html", {
        "cita": cita,
        "next": next_url,
    })



@require_POST
def appointment_move_time(request, id):

    cita = get_object_or_404(Appointment, id=id)

    hora_str = request.POST.get("hora", "").strip()
    fecha_str = request.POST.get("fecha", "").strip()

    if not hora_str:
        return JsonResponse({
            "success": False,
            "error": "Hora no recibida."
        }, status=400)

    if not fecha_str:
        return JsonResponse({
            "success": False,
            "error": "Fecha no recibida."
        }, status=400)

    try:
        nueva_hora = datetime.strptime(hora_str, "%H:%M").time()
    except ValueError:
        return JsonResponse({
            "success": False,
            "error": "Formato de hora inválido."
        }, status=400)

    try:
        nueva_fecha = datetime.strptime(
            fecha_str,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        return JsonResponse({
            "success": False,
            "error": "Formato de fecha inválido."
        }, status=400)

    # 🚫 BLOQUEO DESCANSO (sábado queda libre)
    if hora_str in {"14:00", "14:15", "14:30", "14:45"} and nueva_fecha.weekday() != 5:
        return JsonResponse({
            "success": False,
            "error": "Ese horario está bloqueado."
        }, status=400)

    # 🚫 DÍA BLOQUEADO
    if DayBlock.objects.filter(fecha=nueva_fecha).exists():
        return JsonResponse({
            "success": False,
            "error": "Ese día está bloqueado."
        }, status=400)

    # 🚫 HORARIO BLOQUEADO MANUALMENTE
    if TimeBlock.objects.filter(fecha=nueva_fecha, hora=nueva_hora).exists():
        return JsonResponse({
            "success": False,
            "error": "Ese horario está bloqueado."
        }, status=400)

    cita.hora = nueva_hora
    cita.fecha = nueva_fecha

    cita.save(update_fields=["hora", "fecha"])

    return JsonResponse({"success": True})

# =========================
# 📋 LISTA DE HISTORIAS
# =========================

import json

def clinical_records_list(request, patient_id):
    search_return_url = ""
    try:
        target = urlsplit(request.GET.get("next", ""))
        if not target.scheme and not target.netloc and target.path == reverse("clinical_record_search"):
            search_return_url = target.path + ("?" + target.query if target.query else "")
    except ValueError:
        pass
    paciente = get_object_or_404(Patient, id=patient_id)

    registros = ClinicalRecord.objects.filter(
        paciente_id=patient_id
    ).order_by("-fecha", "-id")

    pagos_cobros, pagos_error = obtener_pagos_cobros_paciente(request, paciente)

    return render(
        request,
        "core/clinical_records_list.html",
        {
            "paciente": paciente,
            "registros": registros,
            "search_return_url": search_return_url,
            "pagos_cobros": pagos_cobros,
            "pagos_error": pagos_error,
        }
    )


def calcular_edad(fecha_nacimiento):
    if not fecha_nacimiento:
        return None

    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year

    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1

    return edad


def obtener_marcas_odontograma(paciente):
    """
    Odontograma simplificado Opción A:
    una sola marca por pieza dental.

    Devuelve un diccionario así:
    {
        "18": "caries",
        "17": "obturado"
    }

    Se siguen usando los campos existentes de OdontogramTooth:
    - numero = pieza dental
    - estado = tratamiento
    - pos_x / pos_y quedan en 0 para compatibilidad con registros viejos
    """
    return {
        str(d.numero): d.estado
        for d in OdontogramTooth.objects.filter(paciente=paciente).exclude(estado="sano")
        if str(d.numero).strip() and str(d.numero) != "marca"
    }


def guardar_odontograma_desde_post(request, paciente):
    data = request.POST.get("odontograma_data", "")

    if not data:
        return

    try:
        marcas = json.loads(data)
    except Exception:
        return

    estados_validos = {
        "caries",
        "obturado",
        "corona",
        "endodoncia",
        "implante",
        "extraccion",
        "ausente",
        "sano",
    }

    # Nuevo formato recomendado: {"18": "caries", "17": "obturado"}
    if isinstance(marcas, dict):
        OdontogramTooth.objects.filter(paciente=paciente).delete()

        for pieza, estado in marcas.items():
            pieza = str(pieza).strip()
            estado = str(estado).strip()

            if not pieza or estado not in estados_validos or estado == "sano":
                continue

            OdontogramTooth.objects.create(
                paciente=paciente,
                numero=pieza,
                estado=estado,
                pos_x=0,
                pos_y=0,
            )
        return

    # Compatibilidad con el odontograma viejo por coordenadas.
    if isinstance(marcas, list):
        OdontogramTooth.objects.filter(paciente=paciente).delete()

        for marca in marcas:
            estado = marca.get("estado")
            pieza = marca.get("pieza") or marca.get("numero") or "marca"
            x = marca.get("x", 0)
            y = marca.get("y", 0)

            if not estado or estado not in estados_validos:
                continue

            OdontogramTooth.objects.create(
                paciente=paciente,
                numero=str(pieza),
                estado=estado,
                pos_x=float(x or 0),
                pos_y=float(y or 0),
            )


def odontograma_paciente(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        guardar_odontograma_desde_post(request, paciente)
        messages.success(request, "Odontograma guardado correctamente.")
        return redirect("odontograma_paciente", patient_id=paciente.id)

    return render(
        request,
        "core/odontograma_paciente.html",
        {
            "paciente": paciente,
            "odontograma_marcas": json.dumps(obtener_marcas_odontograma(paciente)),
            "avisos_clinicos": ClinicalAlert.objects.filter(
                paciente=paciente,
                realizado=False
            ).order_by("fecha_revision", "-creado"),
        }
    )


def odontograma_profesional(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        # Guardado normal desde el formulario del odontograma nuevo.
        if request.POST.get("odontograma_data"):
            guardar_odontograma_desde_post(request, paciente)
            messages.success(request, "Odontograma guardado correctamente.")

            next_url = request.GET.get("next") or request.POST.get("next")

            if next_url:
                return redirect(next_url)

            return redirect(
                "odontograma_profesional",
                patient_id=paciente.id
            )

        # Guardado AJAX opcional: pieza + estado.
        pieza = request.POST.get("pieza")
        estado = request.POST.get("estado")

        estados_validos = {
            "caries",
            "obturado",
            "corona",
            "endodoncia",
            "implante",
            "extraccion",
            "ausente",
            "sano",
        }

        if pieza and estado in estados_validos:
            if estado == "sano":
                OdontogramTooth.objects.filter(paciente=paciente, numero=pieza).delete()
            else:
                OdontogramTooth.objects.update_or_create(
                    paciente=paciente,
                    numero=pieza,
                    defaults={
                        "estado": estado,
                        "pos_x": 0,
                        "pos_y": 0,
                    }
                )
            return JsonResponse({"success": True})

        return JsonResponse({"success": False}, status=400)

    marcas = obtener_marcas_odontograma(paciente)

    return render(
        request,
        "core/odontograma_profesional.html",
        {
            "paciente": paciente,
            "marcas": json.dumps(marcas),
        }
    )


@require_POST
def clinical_alert_create(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)
    titulo = request.POST.get("titulo", "").strip()
    detalle = request.POST.get("detalle", "").strip()
    mes_revision = request.POST.get("mes_revision", "").strip()
    fecha_revision = None

    if mes_revision:
        try:
            # Se guarda el primer día del mes para mantener el DateField actual
            # sin necesidad de migraciones. En pantalla se muestra solo mes/año.
            fecha_revision = datetime.strptime(mes_revision, "%Y-%m").date()
        except ValueError:
            messages.error(request, "El mes de revisión no es válido.")
            next_url = request.POST.get("next") or reverse("clinical_records_list", args=[paciente.id])
            return redirect(next_url)

    next_url = request.POST.get("next") or reverse("clinical_records_list", args=[paciente.id])

    if not titulo:
        messages.error(request, "Escribí un título para el aviso clínico.")
        return redirect(next_url)

    ClinicalAlert.objects.create(
        paciente=paciente,
        titulo=titulo,
        detalle=detalle,
        fecha_revision=fecha_revision,
    )
    messages.success(request, "Aviso clínico agregado.")
    return redirect(next_url)


@require_POST
def clinical_alert_done(request, alert_id):
    aviso = get_object_or_404(ClinicalAlert, id=alert_id)
    next_url = request.POST.get("next") or reverse("clinical_records_list", args=[aviso.paciente_id])
    aviso.realizado = True
    aviso.save(update_fields=["realizado", "actualizado"])
    messages.success(request, "Aviso clínico marcado como realizado.")
    return redirect(next_url)


@require_POST
def clinical_alert_delete(request, alert_id):
    aviso = get_object_or_404(ClinicalAlert, id=alert_id)
    paciente_id = aviso.paciente_id
    next_url = request.POST.get("next") or reverse("clinical_records_list", args=[paciente_id])
    aviso.delete()
    messages.success(request, "Aviso clínico eliminado.")
    return redirect(next_url)


def clinical_record_new(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)

    volver_url = request.GET.get("next") or request.POST.get("next")

    cita_id = request.GET.get("appointment_id") or request.POST.get("appointment_id")
    cita = None
    fecha_seleccionada = None

    fecha_param = request.GET.get("fecha")
    if fecha_param:
        try:
            fecha_candidata = date.fromisoformat(fecha_param)
            if fecha_candidata <= timezone.localdate():
                fecha_seleccionada = fecha_candidata
        except ValueError:
            pass

    if cita_id:
        cita = Appointment.objects.filter(
            id=cita_id,
            paciente=paciente
        ).prefetch_related("procedimientos").first()

    if not cita and request.method == "GET" and fecha_seleccionada:
        cita = (
            Appointment.objects
            .filter(paciente=paciente, fecha=fecha_seleccionada)
            .exclude(estado="cancelado")
            .prefetch_related("procedimientos")
            .order_by("hora", "id")
            .first()
        )

    if request.method == "POST":
        form = ClinicalRecordForm(request.POST)

        if form.is_valid():
            registro = form.save(commit=False)
            registro.paciente = paciente
            registro.save()

            guardar_odontograma_desde_post(request, paciente)

            # Si la Historia Clínica se abrió desde una cita de Agenda,
            # marcamos únicamente que la HC fue actualizada.
            # NO modificamos el estado de asistencia.
            if cita and not cita.historia_actualizada:
                cita.historia_actualizada = True
                cita.save(update_fields=["historia_actualizada"])

            if volver_url:
                return redirect(volver_url)

            return redirect("clinical_record_detail", registro_id=registro.id)

    else:
        fecha_registro = cita.fecha if cita else (fecha_seleccionada or timezone.localdate())
        form = ClinicalRecordForm(initial={"fecha": fecha_registro})

        if cita:
            tratamientos = list(dict.fromkeys(
                p.nombre for p in cita.procedimientos.all()
            ))
            if not tratamientos and cita.motivo:
                tratamientos =…30511 tokens truncated…o,
                        "procedimientos": [p.nombre for p in cita.procedimientos.all()],
                        "hora": cita.hora,
                        "color": color_cita_por_motivo(cita.motivo),
                        "estado": cita.estado,
                        "estado_texto": estado_texto,
                        "estado_color": estado_color,
                    })

                celdas.append({
                    "ocupado": True,
                    "bloqueado": False,
                    "tipo_bloqueo": "",
                    "motivo_bloqueo": "",
                    "citas": citas_preparadas,
                    "fecha": dia,
                    "hora": hora,
                })
            else:
                celdas.append({
                    "ocupado": False,
                    "bloqueado": False,
                    "tipo_bloqueo": "",
                    "motivo_bloqueo": "",
                    "citas": [],
                    "fecha": dia,
                    "hora": hora,
                })

        filas.append({"hora": hora, "celdas": celdas})

    resultados_paciente = []

    if q:
        filtro = Q()
        for palabra in q.split():
            filtro &= (
                Q(paciente__nombre__icontains=palabra) |
                Q(paciente__apellido__icontains=palabra) |
                Q(paciente__ci__icontains=palabra) |
                Q(paciente__telefono__icontains=palabra)
            )

        resultados_paciente = (
            Appointment.objects
            .filter(filtro)
            .select_related("paciente")
            .prefetch_related("procedimientos")
            .order_by("-fecha", "-hora")[:80]
        )

    semana_anterior = inicio_semana - timedelta(days=7)
    semana_siguiente = inicio_semana + timedelta(days=7)

    mini_fecha_str = request.GET.get("mini_fecha")

    if mini_fecha_str:
        try:
            mini_fecha_base = datetime.strptime(mini_fecha_str, "%Y-%m-%d").date()
        except ValueError:
            mini_fecha_base = fecha_base
    else:
        mini_fecha_base = fecha_base

    mini_prev_date = (mini_fecha_base.replace(day=1) - timedelta(days=1)).replace(day=1)

    if mini_fecha_base.month == 12:
        mini_next_date = mini_fecha_base.replace(year=mini_fecha_base.year + 1, month=1, day=1)
    else:
        mini_next_date = mini_fecha_base.replace(month=mini_fecha_base.month + 1, day=1)

    mini_cal = calendar.Calendar(firstweekday=0)
    mini_weeks_raw = mini_cal.monthdatescalendar(mini_fecha_base.year, mini_fecha_base.month)

    mini_inicio = mini_weeks_raw[0][0]
    mini_fin = mini_weeks_raw[-1][-1]

    fechas_con_citas = set(
        Appointment.objects
        .filter(fecha__range=[mini_inicio, mini_fin])
        .values_list("fecha", flat=True)
    )

    mini_weeks = []

    for semana in mini_weeks_raw:
        fila_semana = []

        for dia in semana:
            if dia.month != mini_fecha_base.month:
                fila_semana.append(None)
                continue

            fila_semana.append({
                "date": dia,
                "day": dia.day,
                "is_today": dia == hoy,
                "is_selected": dia == fecha_base,
                "has_appointments": dia in fechas_con_citas,
            })

        mini_weeks.append(fila_semana)

    MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    mini_mes_actual = {
        "label": f"{MESES[mini_fecha_base.month]} {mini_fecha_base.year}",
        "weeks": mini_weeks,
    }

    # 📝 Recordatorios: mostrar TODOS para no tener que ir día por día.
    # Se ordenan primero los pendientes, luego por fecha.
    recordatorios = (
        AgendaReminder.objects
        .all()
        .select_related("paciente")
        .order_by("realizado", "fecha", "-id")
    )

    pacientes_recordatorios = Patient.objects.all().order_by("apellido", "nombre")

    return render(
        request,
        "core/agenda_pro.html",
        {
            "fecha_base": fecha_base,
            "inicio_semana": inicio_semana,
            "fin_semana": fin_semana,
            "dias": dias,
            "filas": filas,
            "semana_anterior": semana_anterior,
            "semana_siguiente": semana_siguiente,
            "q": q,
            "resultados_paciente": resultados_paciente,
            "mini_fecha_base": mini_fecha_base,
            "mini_prev_date": mini_prev_date,
            "mini_next_date": mini_next_date,
            "mini_mes_actual": mini_mes_actual,
            "bloqueos_por_dia": bloqueos_por_dia,
            "bloqueos_por_dia_str": bloqueos_por_dia_str,
            "recordatorios": recordatorios,
            "pacientes_recordatorios": pacientes_recordatorios,
        }
    )



# =============================
# 📝 RECORDATORIOS DE AGENDA
# =============================

def _agenda_reminder_redirect(request, fecha=None):
    next_url = request.POST.get("next") or request.GET.get("next")

    if next_url:
        return redirect(next_url)

    if fecha:
        return redirect(f"{reverse('agenda_pro')}?fecha={fecha.strftime('%Y-%m-%d')}")

    return redirect("agenda_pro")


def _agenda_reminder_fecha(fecha_str):
    if fecha_str:
        try:
            return datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    return timezone.localdate()


@require_POST
def agenda_reminder_create(request):
    titulo = request.POST.get("titulo", "").strip()
    descripcion = request.POST.get("descripcion", "").strip()
    prioridad = request.POST.get("prioridad", "normal").strip()
    fecha = _agenda_reminder_fecha(request.POST.get("fecha"))
    paciente_id = request.POST.get("paciente") or None

    prioridades_validas = {"normal", "importante", "urgente"}
    if prioridad not in prioridades_validas:
        prioridad = "normal"

    if not titulo:
        messages.error(request, "El recordatorio necesita un título.")
        return _agenda_reminder_redirect(request, fecha)

    paciente = None
    if paciente_id:
        paciente = Patient.objects.filter(id=paciente_id).first()

    AgendaReminder.objects.create(
        fecha=fecha,
        titulo=titulo,
        descripcion=descripcion,
        prioridad=prioridad,
        paciente=paciente,
    )

    messages.success(request, "Recordatorio creado correctamente.")
    return _agenda_reminder_redirect(request, fecha)


@require_POST
def agenda_reminder_edit(request, id):
    recordatorio = get_object_or_404(AgendaReminder, id=id)

    titulo = request.POST.get("titulo", "").strip()
    descripcion = request.POST.get("descripcion", "").strip()
    prioridad = request.POST.get("prioridad", "normal").strip()
    fecha = _agenda_reminder_fecha(request.POST.get("fecha"))
    paciente_id = request.POST.get("paciente") or None

    prioridades_validas = {"normal", "importante", "urgente"}
    if prioridad not in prioridades_validas:
        prioridad = "normal"

    if not titulo:
        messages.error(request, "El recordatorio necesita un título.")
        return _agenda_reminder_redirect(request, fecha)

    recordatorio.titulo = titulo
    recordatorio.descripcion = descripcion
    recordatorio.prioridad = prioridad
    recordatorio.fecha = fecha
    recordatorio.paciente = Patient.objects.filter(id=paciente_id).first() if paciente_id else None
    recordatorio.save()

    messages.success(request, "Recordatorio actualizado.")
    return _agenda_reminder_redirect(request, fecha)


@require_POST
def agenda_reminder_toggle(request, id):
    recordatorio = get_object_or_404(AgendaReminder, id=id)
    recordatorio.realizado = not recordatorio.realizado
    recordatorio.save(update_fields=["realizado", "actualizado"])

    return _agenda_reminder_redirect(request, recordatorio.fecha)


@require_POST
def agenda_reminder_delete(request, id):
    recordatorio = get_object_or_404(AgendaReminder, id=id)
    fecha = recordatorio.fecha
    recordatorio.delete()

    messages.success(request, "Recordatorio eliminado.")
    return _agenda_reminder_redirect(request, fecha)



def pacientes_inactivos(request):
    dias = int(request.GET.get("dias", 90))
    fecha_limite = timezone.now().date() - timedelta(days=dias)

    pacientes = Patient.objects.annotate(
        ultima_cita=Max("appointment__fecha")
    ).filter(
        ultima_cita__isnull=False,
        ultima_cita__lt=fecha_limite
    ).order_by("ultima_cita", "apellido", "nombre")

    pacientes_con_dias = []
    hoy = timezone.now().date()

    for paciente in pacientes:
        dias_sin_venir = (hoy - paciente.ultima_cita).days
        pacientes_con_dias.append({
            "id": paciente.id,
            "apellido": paciente.apellido,
            "nombre": paciente.nombre,
            "telefono": getattr(paciente, "telefono", ""),
            "ultima_cita": paciente.ultima_cita,
            "dias_sin_venir": dias_sin_venir,
        })

    context = {
        "pacientes": pacientes_con_dias,
        "dias": dias,
        "titulo": "Pacientes inactivos",
    }
    return render(request, "core/pacientes_inactivos.html", context)


from django.http import FileResponse
import os

def descargar_backup(request):
    ruta = "/opt/render/project/src/db_respaldo_cierre.sqlite3"
    return FileResponse(open(ruta, 'rb'), as_attachment=True, filename='backup.sqlite3')



def obtener_deuda_presupuestos_paciente(paciente):
    presupuestos = Budget.objects.filter(
        paciente=paciente,
        estado="confirmado"
    )

    total = Decimal("0")

    for p in presupuestos:
        try:
            saldo = p.saldo_pendiente or Decimal("0")
        except:
            saldo = Decimal("0")

        if saldo > 0:
            total += saldo

    return total


def deudores_general(request):
    """
    Pacientes deudores optimizado.
    Antes esta pantalla consultaba Cobros una vez por cada cita (/pagos/api/por-cita/),
    por eso la consola de Cobros no dejaba de cargar.

    Ahora:
    - Junta pacientes.
    - Consulta Cobros una sola vez por patient_id.
    - Calcula deuda real por paciente: total citas cobrables - total pagado.
    """
    query = request.GET.get("q", "").strip().lower()
    mostrar_archivados = request.GET.get("estado") == "archivados"

    citas = (
        Appointment.objects
        .exclude(estado="cancelado")
        .filter(monto_total__gt=0)
        .select_related("paciente")
        .only(
            "id",
            "paciente_id",
            "fecha",
            "hora",
            "paciente__nombre",
            "paciente__apellido",
            "paciente__archivado_deudores",
        )
        .order_by("fecha", "hora", "id")
    )

    pacientes_por_id = {}
    primera_cita_pendiente_por_id = {}
    ultima_fecha_por_id = {}

    for cita in citas.iterator(chunk_size=500):
        paciente = cita.paciente
        if paciente.archivado_deudores != mostrar_archivados:
            continue
        patient_id = paciente.id
        nombre = f"{paciente.apellido}, {paciente.nombre}".lower()


        if query and query not in nombre:
            continue

        pacientes_por_id[patient_id] = paciente

        if patient_id not in primera_cita_pendiente_por_id:
            primera_cita_pendiente_por_id[patient_id] = cita

        if patient_id not in ultima_fecha_por_id or cita.fecha > ultima_fecha_por_id[patient_id]:
            ultima_fecha_por_id[patient_id] = cita.fecha

    # Presupuestos confirmados también pueden generar deuda aunque no haya cita reciente.
    # Guardamos el TOTAL del presupuesto; los pagos se descontarán desde Cobros
    # una sola vez por paciente para no duplicar deuda.
    presupuestos_confirmados = list(
        Budget.objects
        .filter(estado="confirmado")
        .select_related("paciente")
        .prefetch_related("pagos", "ajustes", "transferencias_enviadas", "transferencias_recibidas")
    )

    total_presupuestos_por_id = {}
    total_pagado_presupuesto_local_por_id = {}

    for presupuesto in presupuestos_confirmados:
        paciente = presupuesto.paciente
        if paciente.archivado_deudores != mostrar_archivados:
            continue
        patient_id = paciente.id
        nombre = f"{paciente.apellido}, {paciente.nombre}".lower()


        if query and query not in nombre:
            continue

        total_presupuesto = _decimal_seguro(presupuesto.total_efectivo)
        if total_presupuesto <= 0:
            continue

        pacientes_por_id[patient_id] = paciente
        total_presupuestos_por_id[patient_id] = (
            total_presupuestos_por_id.get(patient_id, Decimal("0"))
            + total_presupuesto
        )
        total_pagado_presupuesto_local_por_id[patient_id] = (
            total_pagado_presupuesto_local_por_id.get(patient_id, Decimal("0"))
            + _decimal_seguro(presupuesto.total_pagado)
        )

        if patient_id not in ultima_fecha_por_id:
            ultima_fecha_por_id[patient_id] = presupuesto.fecha

    # El archivo también muestra pacientes archivados que ya no tengan citas
    # cobrables o presupuestos confirmados, para poder restaurarlos si hace falta.
    if mostrar_archivados:
        archivados = Patient.objects.filter(archivado_deudores=True).annotate(
            ultima_cita=Max("appointment__fecha")
        ).only("id", "nombre", "apellido", "archivado_deudores")
        for paciente in archivados:
            nombre = f"{paciente.apellido}, {paciente.nombre}".lower()
            if query and query not in nombre:
                continue
            pacientes_por_id.setdefault(paciente.id, paciente)
            if paciente.ultima_cita:
                ultima_fecha_por_id[paciente.id] = paciente.ultima_cita

    patient_ids = list(pacientes_por_id.keys())
    resumenes_cobros = obtener_resumen_cobros_pacientes_bulk(patient_ids)

    # Calcula los cargos de todos los pacientes en bloques. Evita hacer una
    # consulta SQL por paciente al entrar a Deudores.
    totales_cobrables_por_id = {}
    for inicio in range(0, len(patient_ids), 500):
        ids_bloque = patient_ids[inicio:inicio + 500]
        filas_totales = (
            Appointment.objects
            .filter(paciente_id__in=ids_bloque)
            .exclude(estado="cancelado")
            .values("paciente_id")
            .annotate(total=Sum("monto_total"))
        )
        totales_cobrables_por_id.update({
            fila["paciente_id"]: _decimal_seguro(fila["total"])
            for fila in filas_totales
        })

    deudores = []

    for patient_id, paciente in pacientes_por_id.items():
        total_cobrable = totales_cobrables_por_id.get(
            patient_id,
            Decimal("0"),
        )
        total_pagado = _decimal_seguro(
            resumenes_cobros.get(patient_id, {}).get("total_pagado", 0)
        )

        deuda_citas = total_cobrable - total_pagado
        if deuda_citas < 0:
            deuda_citas = Decimal("0")

        total_presupuestos = total_presupuestos_por_id.get(
            patient_id,
            Decimal("0"),
        )
        total_pagado_local = total_pagado_presupuesto_local_por_id.get(
            patient_id,
            Decimal("0"),
        )
        total_pagado_reconocido = max(total_pagado, total_pagado_local)

        deuda_presupuestos = total_presupuestos - total_pagado_reconocido
        if deuda_presupuestos < 0:
            deuda_presupuestos = Decimal("0")

        # Citas y presupuesto pueden corresponder al mismo tratamiento.
        # Tomamos el saldo mayor en vez de sumarlos para no duplicar deuda.
        deuda_total = max(deuda_citas, deuda_presupuestos)

        if deuda_total <= 0 and not mostrar_archivados:
            continue

        cita_pendiente = primera_cita_pendiente_por_id.get(patient_id)

        deudores.append({
            "patient_id": patient_id,
            "paciente": f"{paciente.apellido}, {paciente.nombre}",
            "deuda_citas": deuda_citas,
            "deuda_presupuestos": deuda_presupuestos,
            "deuda_total": deuda_total,
            "ultima_fecha": ultima_fecha_por_id.get(patient_id),
            "cita_pendiente_id": cita_pendiente.id if cita_pendiente else None,
        })

    deudores.sort(key=lambda x: x["deuda_total"], reverse=True)

    total_general = (
        sum((d["deuda_total"] for d in deudores), Decimal("0"))
        if not mostrar_archivados
        else Decimal("0")
    )

    return render(
        request,
        "core/deudores_general.html",
        {
            "deudores": deudores,
            "total_general": total_general,
            "query": query,
            "mostrar_archivados": mostrar_archivados,
        }
    )


def _redirigir_deudores(request, url_predeterminada):
    """Vuelve a una URL local indicada por el formulario, si es segura."""
    from django.utils.http import url_has_allowed_host_and_scheme

    destino = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(destino)
    return redirect(url_predeterminada)


@require_POST
def deudor_archivar(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)
    if not paciente.archivado_deudores:
        paciente.archivado_deudores = True
        paciente.save(update_fields=["archivado_deudores"])
        messages.success(
            request,
            "Paciente archivado. Su deuda se conserva y deja de sumarse al total activo.",
        )
    return _redirigir_deudores(request, "deudores_general")


@require_POST
def deudor_restaurar(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)
    if paciente.archivado_deudores:
        paciente.archivado_deudores = False
        paciente.save(update_fields=["archivado_deudores"])
        messages.success(
            request,
            "Paciente restaurado. Su deuda vuelve a incluirse en el total activo.",
        )
    return _redirigir_deudores(request, "deudores_general")

def obtener_detalle_cobros_paciente(paciente):
    """
    Obtiene el resumen financiero del paciente usando como fuente principal
    el endpoint rápido por patient_id, el mismo que utiliza Agenda/Deudores.

    Si existen movimientos modernos con patient_id, hace como máximo una
    consulta adicional al endpoint de detalle para recuperar devoluciones.
    Si no existen movimientos por patient_id, conserva la compatibilidad con
    pagos históricos buscando por los formatos de nombre antiguos.
    """
    cobros_base_url = getattr(
        settings,
        "SONRISAR_COBROS_BASE_URL",
        "https://sonrisar-cobros-1.onrender.com"
    ).rstrip("/")

    cobros_api_path = getattr(
        settings,
        "SONRISAR_COBROS_API_PACIENTE_PATH",
        "/pagos/api/por-paciente/"
    )

    # Fuente principal y rápida: exactamente el mismo resumen por patient_id
    # que ya usan Agenda del día y Pacientes deudores.
    resumen_rapido = obtener_resumen_cobros_paciente(paciente)
    resumen_ok = bool(resumen_rapido.get("ok"))
    total_pagado_resumen = _decimal_seguro(
        resumen_rapido.get("total_pagado", 0)
    )
    cantidad_pagos_resumen = int(
        resumen_rapido.get("cantidad_pagos", 0) or 0
    )

    # Si el resumen rápido reconoce pagos del paciente, NO hacemos las tres
    # búsquedas históricas. Consultamos detalle solo una vez por patient_id
    # para conservar información de devoluciones cuando esté disponible.
    if resumen_ok and (total_pagado_resumen > 0 or cantidad_pagos_resumen > 0):
        try:
            response = requests.get(
                f"{cobros_base_url}{cobros_api_path}",
                params={"patient_id": paciente.id},
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                cantidad_devoluciones = int(
                    data.get("cantidad_devoluciones", 0) or 0
                )
                total_devuelto = _decimal_seguro(
                    data.get("total_devuelto", 0)
                )
                total_pagado_bruto = _decimal_seguro(
                    data.get(
                        "total_pagado_bruto",
                        total_pagado_resumen + total_devuelto,
                    )
                )

                return {
                    "ok": True,
                    # El total rápido es la fuente autoritativa para el saldo.
                    "total_pagado": total_pagado_resumen,
                    "total_pagado_bruto": total_pagado_bruto,
                    "total_devuelto": total_devuelto,
                    "cantidad_pagos": max(
                        cantidad_pagos_resumen,
                        int(data.get("total", data.get("cantidad_pagos", 0)) or 0),
                    ),
                    "cantidad_devoluciones": cantidad_devoluciones,
                    "devoluciones": data.get("devoluciones", []) or [],
                    "error": None,
                }
        except Exception:
            # Si falla solamente el detalle, el saldo sigue siendo válido
            # gracias al resumen rápido. No bloqueamos Finanzas del paciente.
            pass

        return {
            "ok": True,
            "total_pagado": total_pagado_resumen,
            "total_pagado_bruto": total_pagado_resumen,
            "total_devuelto": Decimal("0"),
            "cantidad_pagos": cantidad_pagos_resumen,
            "cantidad_devoluciones": 0,
            "devoluciones": [],
            "error": None,
        }

    # Compatibilidad con pagos históricos que todavía no tengan patient_id.
    consultas_historicas = [
        {"paciente": f"{paciente.apellido}, {paciente.nombre}".strip(", ")},
        {"paciente": f"{paciente.nombre} {paciente.apellido}".strip()},
    ]

    ultimo_error = resumen_rapido.get("error") if not resumen_ok else None

    for params in consultas_historicas:
        try:
            response = requests.get(
                f"{cobros_base_url}{cobros_api_path}",
                params=params,
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                ultimo_error = data.get("error", "Respuesta inválida de Cobros")
                continue

            ultimo_error = None

            cantidad_pagos = int(
                data.get("total", data.get("cantidad_pagos", 0)) or 0
            )
            cantidad_devoluciones = int(
                data.get("cantidad_devoluciones", 0) or 0
            )

            if cantidad_pagos == 0 and cantidad_devoluciones == 0:
                continue

            return {
                "ok": True,
                "total_pagado": _decimal_seguro(data.get("total_pagado", 0)),
                "total_pagado_bruto": _decimal_seguro(
                    data.get("total_pagado_bruto", data.get("total_pagado", 0))
                ),
                "total_devuelto": _decimal_seguro(data.get("total_devuelto", 0)),
                "cantidad_pagos": cantidad_pagos,
                "cantidad_devoluciones": cantidad_devoluciones,
                "devoluciones": data.get("devoluciones", []) or [],
                "error": None,
            }

        except Exception as e:
            ultimo_error = str(e)

    if resumen_ok or ultimo_error is None:
        return {
            "ok": True,
            "total_pagado": Decimal("0"),
            "total_pagado_bruto": Decimal("0"),
            "total_devuelto": Decimal("0"),
            "cantidad_pagos": 0,
            "cantidad_devoluciones": 0,
            "devoluciones": [],
            "error": None,
        }

    return {
        "ok": False,
        "total_pagado": Decimal("0"),
        "total_pagado_bruto": Decimal("0"),
        "total_devuelto": Decimal("0"),
        "cantidad_pagos": 0,
        "cantidad_devoluciones": 0,
        "devoluciones": [],
        "error": f"No fue posible conectar con Sonrisar Cobros: {ultimo_error}",
    }

def patient_finances(request, id):
    """
    Ficha financiera del paciente.

    Pantalla liviana:
    - Usa datos locales de Sonrisar Pro para citas/presupuestos.
    - Consulta Sonrisar Cobros una sola vez por patient_id.
    - Usa el total pagado neto (pagos - devoluciones).
    - Muestra el historial de devoluciones sin borrar el pago original.
    """
    paciente = get_object_or_404(Patient, id=id)

    citas_cobrables = list(
        Appointment.objects
        .filter(paciente=paciente, monto_total__gt=0)
        .exclude(estado="cancelado")
        .prefetch_related("procedimientos")
        .order_by("-fecha", "-hora")
    )

    total_citas = Decimal("0")
    for cita in citas_cobrables:
        total_citas += _decimal_seguro(cita.monto_total)

    resumen_cobros = obtener_detalle_cobros_paciente(paciente)
    total_pagado_cobros = _decimal_seguro(resumen_cobros.get("total_pagado", 0))
    total_pagado_bruto_cobros = _decimal_seguro(resumen_cobros.get("total_pagado_bruto", 0))
    total_devuelto_cobros = _decimal_seguro(resumen_cobros.get("total_devuelto", 0))
    devoluciones_cobros = resumen_cobros.get("devoluciones", []) or []

    # Saldo financiero real del paciente.
    # total_pagado_cobros ya viene neto desde Cobros: pagos - devoluciones.
    diferencia_saldo = total_citas - total_pagado_cobros

    saldo_pendiente = max(diferencia_saldo, Decimal("0"))
    saldo_a_favor = max(-diferencia_saldo, Decimal("0"))

    # Se conserva saldo_actual por compatibilidad con cualquier uso existente.
    saldo_actual = saldo_pendiente

    presupuestos = list(
        Budget.objects
        .filter(paciente=paciente)
        .prefetch_related("items", "pagos", "ajustes", "transferencias_enviadas", "transferencias_recibidas")
        .order_by("-fecha", "-id")
    )

    estados_aceptados = {"confirmado", "en_proceso", "entregado"}

    total_presupuestos_aceptados = Decimal("0")
    total_pagado_presupuestos = Decimal("0")
    saldo_presupuestos = Decimal("0")
    presupuestos_data = []
    movimientos_presupuesto = []

    for presupuesto in presupuestos:
        total_original = _decimal_seguro(presupuesto.total)
        total_ajustes = _decimal_seguro(presupuesto.total_ajustes)
        total_presupuesto = _decimal_seguro(presupuesto.total_efectivo)
        total_pagado = _decimal_seguro(presupuesto.total_pagado)
        credito_recibido = _decimal_seguro(presupuesto.credito_recibido)
        credito_transferido = _decimal_seguro(presupuesto.credito_transferido)
        credito_disponible = _decimal_seguro(presupuesto.credito_disponible)
        saldo = _decimal_seguro(presupuesto.saldo_pendiente)

        if saldo < 0:
            saldo = Decimal("0")

        if presupuesto.estado in estados_aceptados:
            total_presupuestos_aceptados += total_presupuesto
            total_pagado_presupuestos += total_pagado
            saldo_presupuestos += saldo

        presupuestos_data.append({
            "id": presupuesto.id,
            "fecha": presupuesto.fecha,
            "diagnostico": presupuesto.diagnostico,
            "estado": presupuesto.estado,
            "estado_display": presupuesto.get_estado_display(),
            "total": total_presupuesto,
            "total_original": total_original,
            "total_ajustes": total_ajustes,
            "total_pagado": total_pagado,
            "credito_recibido": credito_recibido,
            "credito_transferido": credito_transferido,
            "credito_disponible": credito_disponible,
            "saldo": saldo,
            "aceptado": presupuesto.estado in estados_aceptados,
        })

        for pago in presupuesto.pagos.all():
            movimientos_presupuesto.append({
                "fecha": pago.fecha,
                "tipo": pago.get_tipo_display(),
                "concepto": pago.observacion or f"Pago presupuesto #{presupuesto.id}",
                "metodo": pago.get_metodo_pago_display() if pago.metodo_pago else "—",
                "monto": _decimal_seguro(pago.monto),
                "presupuesto_id": presupuesto.id,
                "clase": "pago",
            })

        for ajuste in presupuesto.ajustes.all():
            movimientos_presupuesto.append({
                "fecha": ajuste.fecha,
                "tipo": "Ajuste de presupuesto",
                "concepto": ajuste.motivo,
                "metodo": "Administrativo",
                "monto": _decimal_seguro(ajuste.monto),
                "presupuesto_id": presupuesto.id,
                "clase": "ajuste",
            })

        for transferencia in presupuesto.transferencias_enviadas.all():
            movimientos_presupuesto.append({
                "fecha": transferencia.fecha,
                "tipo": "Crédito transferido",
                "concepto": transferencia.motivo or f"Al presupuesto #{transferencia.presupuesto_destino_id}",
                "metodo": f"#{presupuesto.id} → #{transferencia.presupuesto_destino_id}",
                "monto": -_decimal_seguro(transferencia.monto),
                "presupuesto_id": presupuesto.id,
                "clase": "transferencia",
            })

        for transferencia in presupuesto.transferencias_recibidas.all():
            movimientos_presupuesto.append({
                "fecha": transferencia.fecha,
                "tipo": "Crédito recibido",
                "concepto": transferencia.motivo or f"Desde presupuesto #{transferencia.presupuesto_origen_id}",
                "metodo": f"#{transferencia.presupuesto_origen_id} → #{presupuesto.id}",
                "monto": _decimal_seguro(transferencia.monto),
                "presupuesto_id": presupuesto.id,
                "clase": "transferencia",
            })

    movimientos_presupuesto.sort(
        key=lambda m: (m["fecha"], m["presupuesto_id"]),
        reverse=True,
    )

    # El saldo de citas conserva el cálculo de cobros netos menos cargos.
    # El presupuesto incluye prestaciones todavía no realizadas; su saldo se
    # muestra por separado y no reemplaza el saldo disponible de las citas.
    # Sus pagos tampoco se agregan: pueden reflejar los mismos cobros.

    citas_data = []
    for cita in citas_cobrables[:60]:
        procedimientos = ", ".join([p.nombre for p in cita.procedimientos.all()])
        citas_data.append({
            "id": cita.id,
            "fecha": cita.fecha,
            "hora": cita.hora,
            "motivo": cita.motivo,
            "procedimientos": procedimientos,
            "estado": cita.estado,
            "estado_display": cita.get_estado_display(),
            "monto_total": _decimal_seguro(cita.monto_total),
        })

    return render(
        request,
        "core/patient_finances.html",
        {
            "paciente": paciente,
            "total_citas": total_citas,
            "total_pagado_cobros": total_pagado_cobros,
            "total_pagado_bruto_cobros": total_pagado_bruto_cobros,
            "total_devuelto_cobros": total_devuelto_cobros,
            "devoluciones_cobros": devoluciones_cobros,
            "saldo_actual": saldo_actual,
            "saldo_pendiente": saldo_pendiente,
            "saldo_a_favor": saldo_a_favor,
            "cobros_error": resumen_cobros.get("error"),
            "cobros_ok": resumen_cobros.get("ok", False),
            "cantidad_pagos_cobros": resumen_cobros.get("cantidad_pagos", 0),
            "cantidad_devoluciones_cobros": resumen_cobros.get("cantidad_devoluciones", 0),
            "total_presupuestos_aceptados": total_presupuestos_aceptados,
            "total_pagado_presupuestos": total_pagado_presupuestos,
            "saldo_presupuestos": saldo_presupuestos,
            "presupuestos": presupuestos_data,
            "movimientos_presupuesto": movimientos_presupuesto,
            "citas": citas_data,
        }
    )


# FINANZAS_2026_05_23 


# ============================
# BLOQUEAR / DESBLOQUEAR DÍA
# ============================

@require_POST
def bloquear_dia(request):

    fecha = request.POST.get("fecha")
    motivo = request.POST.get("motivo", "Día bloqueado")

    if not fecha:
        messages.error(request, "Fecha inválida.")
        return redirect("agenda_pro")

    try:
        fecha_obj = datetime.strptime(
            fecha,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        messages.error(request, "Fecha inválida.")
        return redirect("agenda_pro")

    DayBlock.objects.get_or_create(
        fecha=fecha_obj,
        defaults={
            "motivo": motivo
        }
    )

    messages.success(
        request,
        "Día bloqueado correctamente."
    )

    return redirect(
        f"{reverse('agenda_pro')}?fecha={fecha_obj.strftime('%Y-%m-%d')}"
    )


@require_POST
def desbloquear_dia(request):

    fecha = request.POST.get("fecha")

    if not fecha:
        return redirect("agenda_pro")

    try:
        fecha_obj = datetime.strptime(
            fecha,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        return redirect("agenda_pro")

    DayBlock.objects.filter(
        fecha=fecha_obj
    ).delete()

    messages.success(
        request,
        "Día desbloqueado."
    )

    return redirect(
        f"{reverse('agenda_pro')}?fecha={fecha_obj.strftime('%Y-%m-%d')}"
    )

# ============================
# BLOQUEAR / DESBLOQUEAR HORARIO
# ============================

@require_POST
def bloquear_horario(request):
    fecha_str = request.POST.get("fecha", "").strip()
    hora_str = request.POST.get("hora", "").strip()
    motivo = request.POST.get("motivo", "").strip() or "Horario bloqueado"

    try:
        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        hora_obj = datetime.strptime(hora_str, "%H:%M").time()
    except ValueError:
        messages.error(request, "Fecha u hora inválida.")
        return redirect("agenda_pro")

    if DayBlock.objects.filter(fecha=fecha_obj).exists():
        messages.error(request, "Ese día ya está bloqueado completamente.")
        return redirect(f"{reverse('agenda_pro')}?fecha={fecha_obj.strftime('%Y-%m-%d')}")

    if hora_str in {"14:00", "14:15", "14:30", "14:45"} and fecha_obj.weekday() != 5:
        messages.error(request, "Ese horario ya corresponde al descanso.")
        return redirect(f"{reverse('agenda_pro')}?fecha={fecha_obj.strftime('%Y-%m-%d')}")

    # No permitir ocultar accidentalmente una cita existente dentro del bloque de 30 min.
    inicio_dt = datetime.combine(fecha_obj, hora_obj)
    siguiente = next((h for h in horarios_para_fecha(fecha_obj) if h > hora_obj), time(20))
    fin_dt = datetime.combine(fecha_obj, siguiente)
    if Appointment.objects.filter(
        fecha=fecha_obj,
        hora__gte=inicio_dt.time(),
        hora__lt=fin_dt.time()
    ).exists():
        messages.error(request, "No se puede bloquear: ya existe una cita en ese horario.")
        return redirect(f"{reverse('agenda_pro')}?fecha={fecha_obj.strftime('%Y-%m-%d')}")

    bloqueo, creado = TimeBlock.objects.get_or_create(
        fecha=fecha_obj,
        hora=hora_obj,
        defaults={"motivo": motivo}
    )

    if not creado and bloqueo.motivo != motivo:
        bloqueo.motivo = motivo
        bloqueo.save(update_fields=["motivo"])

    messages.success(request, f"Horario {hora_str} bloqueado.")
    return redirect(f"{reverse('agenda_pro')}?fecha={fecha_obj.strftime('%Y-%m-%d')}")


@require_POST
def desbloquear_horario(request):
    fecha_str = request.POST.get("fecha", "").strip()
    hora_str = request.POST.get("hora", "").strip()

    try:
        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        hora_obj = datetime.strptime(hora_str, "%H:%M").time()
    except ValueError:
        messages.error(request, "Fecha u hora inválida.")
        return redirect("agenda_pro")

    TimeBlock.objects.filter(fecha=fecha_obj, hora=hora_obj).delete()
    messages.success(request, f"Horario {hora_str} desbloqueado.")
    return redirect(f"{reverse('agenda_pro')}?fecha={fecha_obj.strftime('%Y-%m-%d')}")


# =============================
# 📊 ESTADÍSTICAS SONRISAR PRO
# =============================

def estadisticas(request):
    hoy = timezone.now().date()

    total_pacientes = Patient.objects.count()

    citas_mes = Appointment.objects.filter(
        fecha__year=hoy.year,
        fecha__month=hoy.month
    ).count()

    colocaciones_mes = Appointment.objects.filter(
        fecha__year=hoy.year,
        fecha__month=hoy.month,
        motivo="Colocación nueva",
        estado="asistio"
    ).values("paciente").distinct().count()

    primeras_fechas = list(
        Appointment.objects
        .values("paciente_id")
        .annotate(fecha_primera=Min("fecha"))
        .values_list("fecha_primera", flat=True)
    )

    pacientes_primera_vez_anio = sum(
        1 for fecha_primera in primeras_fechas
        if fecha_primera and fecha_primera.year == hoy.year
    )

    pacientes_primera_vez_mes = sum(
        1 for fecha_primera in primeras_fechas
        if (
            fecha_primera
            and fecha_primera.year == hoy.year
            and fecha_primera.month == hoy.month
        )
    )

    ajustes_ortodoncia_mes = Appointment.objects.filter(
        fecha__year=hoy.year,
        fecha__month=hoy.month,
        motivo="Ajuste (ortodoncia)",
        estado="asistio"
    ).count()

    pacientes_ortodoncia_activos = Appointment.objects.filter(
        fecha__year=hoy.year,
        fecha__month=hoy.month,
        motivo="Ajuste (ortodoncia)",
        estado="asistio"
    ).values("paciente").distinct().count()

    promedio_ajustes_ortodoncia = 0
    if pacientes_ortodoncia_activos > 0:
        promedio_ajustes_ortodoncia = round(
            ajustes_ortodoncia_mes / pacientes_ortodoncia_activos,
            2
        )

    motivos = (
        Appointment.objects
        .filter(estado="asistio")
        .values("motivo")
        .annotate(total=Count("id"))
        .order_by("-total", "motivo")
    )

    nombres_meses = [
        "",
        "Enero", "Febrero", "Marzo", "Abril",
        "Mayo", "Junio", "Julio", "Agosto",
        "Setiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    primeras_veces_por_mes = []

    for mes in range(1, 13):
        cantidad = sum(
            1 for fecha_primera in primeras_fechas
            if (
                fecha_primera
                and fecha_primera.year == hoy.year
                and fecha_primera.month == mes
            )
        )

        primeras_veces_por_mes.append({
            "mes": nombres_meses[mes],
            "cantidad": cantidad,
        })

    return render(
        request,
        "core/estadisticas.html",
        {
            "total_pacientes": total_pacientes,
            "citas_mes": citas_mes,
            "colocaciones_mes": colocaciones_mes,
            "pacientes_primera_vez_mes": pacientes_primera_vez_mes,
            "pacientes_primera_vez_anio": pacientes_primera_vez_anio,
            "motivos": motivos,
            "primeras_veces_por_mes": primeras_veces_por_mes,
            "anio_actual": hoy.year,

            "ajustes_ortodoncia_mes": ajustes_ortodoncia_mes,
            "pacientes_ortodoncia_activos": pacientes_ortodoncia_activos,
            "promedio_ajustes_ortodoncia": promedio_ajustes_ortodoncia,
        }
    )


def csrf_failure(request, reason=""):
    print(
        f"CSRF_FAILURE path={request.path} reason={reason} "
        f"origin={request.headers.get('Origin', '')} "
        f"referer={request.headers.get('Referer', '')} "
        f"cookie_present={bool(request.COOKIES.get(settings.CSRF_COOKIE_NAME))}",
        flush=True,
    )
    from django.views.csrf import csrf_failure as default_csrf_failure
    return default_csrf_failure(request, reason=reason)
