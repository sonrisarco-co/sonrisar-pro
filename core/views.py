from django.shortcuts import render, redirect, get_object_or_404
from datetime import date, time, timedelta, datetime
import requests
from django.utils.text import slugify

import calendar
#from core.models import Cita
from django.db.models import Q, Max
from django.contrib import messages

from django.conf import settings
from urllib.parse import urlencode, quote

from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from django.utils.http import urlencode

from django.contrib import messages

from django.core.paginator import Paginator

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
    Inventory,
    ClinicalRecord,
    RayosX,
    BudgetPayment,
    OdontogramTooth,
    DayBlock,
)

from .forms import (
    PatientForm,
    AppointmentForm,
    ClinicalRecordForm,
    BudgetForm,
    InventoryForm,
    ProsthesisForm,
    RayosXForm,
    BudgetPaymentForm,
)


# =============================
# 🌟 PANEL PRINCIPAL
# =============================
from django.db.models import Count

def home(request):
    today = date.today()

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

    ranking = (
        citas.filter(estado="no_asistio")
        .values("paciente__apellido", "paciente__nombre")
        .annotate(faltas=Count("id"))
        .order_by("-faltas")
    )

    # navegación entre meses
    prev_month = month - 1 if month > 1 else 12
    prev_year  = year - 1 if month == 1 else year

    next_month = month + 1 if month < 12 else 1
    next_year  = year + 1 if month == 12 else year

    context = {
        "total": total,
        "asistieron": asistieron,
        "no_asistieron": no_asistieron,
        "confirmados": confirmados,
        "cancelados": cancelados,
        "pendientes": pendientes,
        "porcentaje": porcentaje,
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
            "pacientes": pacientes,
            "query": query,
            "cantidad_inactivos": cantidad_inactivos,
        }
    )



def patient_detail(request, id):
    paciente = get_object_or_404(Patient, id=id)
    return render(request, "core/patient_detail.html", {"paciente": paciente})


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
        paciente = Patient.objects.create(
            nombre=request.POST.get("nombre", "").strip(),
            apellido=request.POST.get("apellido", "").strip(),
            ci=request.POST.get("ci", "").strip(),
            fecha_nacimiento=request.POST.get("fecha_nacimiento") or None,
            telefono=request.POST.get("telefono", "").strip(),
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
        paciente = Patient.objects.create(
            nombre=request.POST.get("nombre", "").strip(),
            apellido=request.POST.get("apellido", "").strip(),
            ci=request.POST.get("ci", "").strip(),
            fecha_nacimiento=request.POST.get("fecha_nacimiento") or None,
            telefono=request.POST.get("telefono", "").strip(),
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

    if request.method == "POST":
        paciente.nombre = request.POST.get("nombre", "").strip()
        paciente.apellido = request.POST.get("apellido", "").strip()
        paciente.ci = request.POST.get("ci", "").strip()
        paciente.fecha_nacimiento = request.POST.get("fecha_nacimiento") or None
        paciente.telefono = request.POST.get("telefono", "").strip()
        paciente.email = request.POST.get("email", "").strip()
        paciente.direccion = request.POST.get("direccion", "").strip()
        paciente.save()
        return redirect("patient_detail", id=paciente.id)

    # 🔥 AGREGADO IMPORTANTE:
    # Enviamos el paciente con todos sus datos para rellenar los campos del formulario
    context = {
        "paciente": paciente
    }

    return render(request, "core/patient_edit.html", context)



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

    # 🚫 VALIDAR HORARIOS BLOQUEADOS
    if hora in ["14:00", "14:30"]:
        messages.error(request, "Ese horario está bloqueado.")
        return redirect(next_url)

    # 🚫 VALIDAR DÍA BLOQUEADO
    if fecha:
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()

            if DayBlock.objects.filter(fecha=fecha_obj).exists():
                messages.error(request, "Ese día está bloqueado.")
                return redirect(next_url)

        except Exception:
            pass

    if request.method == "POST":
        form = AppointmentForm(request.POST)

        if form.is_valid():

            nueva_cita = form.save(commit=False)

            # 🚫 VALIDAR HORARIO EN POST
            hora_cita = nueva_cita.hora.strftime("%H:%M")

            if hora_cita in ["14:00", "14:30"]:
                messages.error(request, "Ese horario está bloqueado.")
                return redirect(next_url)

            # 🚫 VALIDAR DÍA BLOQUEADO
            if DayBlock.objects.filter(fecha=nueva_cita.fecha).exists():
                messages.error(request, "Ese día está bloqueado.")
                return redirect(next_url)

            nueva_cita.save()
            form.save_m2m()

            return redirect(next_url)

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

    es_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        form = AppointmentForm(request.POST, instance=cita)

        if form.is_valid():
            form.save()

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

    # 🚫 BLOQUEO DESCANSO
    if hora_str in {"14:00", "14:30"}:
        return JsonResponse({
            "success": False,
            "error": "Ese horario está bloqueado."
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

    # 🚫 DÍA BLOQUEADO
    if DayBlock.objects.filter(fecha=nueva_fecha).exists():
        return JsonResponse({
            "success": False,
            "error": "Ese día está bloqueado."
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
    paciente = get_object_or_404(Patient, id=patient_id)

    registros = ClinicalRecord.objects.filter(
        paciente_id=patient_id
    ).order_by("-fecha")

    pagos_cobros, pagos_error = obtener_pagos_cobros_paciente(request, paciente)

    return render(
        request,
        "core/clinical_records_list.html",
        {
            "paciente": paciente,
            "registros": registros,
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
    return [
        {
            "id": str(d.id),
            "estado": d.estado,
            "x": d.pos_x,
            "y": d.pos_y,
        }
        for d in OdontogramTooth.objects.filter(paciente=paciente)
    ]


def guardar_odontograma_desde_post(request, paciente):
    data = request.POST.get("odontograma_data", "")

    if not data:
        return

    try:
        marcas = json.loads(data)
    except Exception:
        return

    OdontogramTooth.objects.filter(paciente=paciente).delete()

    for marca in marcas:
        estado = marca.get("estado")
        x = marca.get("x")
        y = marca.get("y")

        if not estado or x is None or y is None:
            continue

        OdontogramTooth.objects.create(
            paciente=paciente,
            numero="marca",
            estado=estado,
            pos_x=float(x),
            pos_y=float(y),
        )


def clinical_record_new(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)

    cita_id = request.GET.get("appointment_id") or request.POST.get("appointment_id")
    cita = None

    if cita_id:
        cita = Appointment.objects.filter(
            id=cita_id,
            paciente=paciente
        ).prefetch_related("procedimientos").first()

    if request.method == "POST":
        form = ClinicalRecordForm(request.POST)

        if form.is_valid():
            registro = form.save(commit=False)
            registro.paciente = paciente
            registro.save()

            guardar_odontograma_desde_post(request, paciente)

            return redirect("clinical_record_detail", registro_id=registro.id)

    else:
        form = ClinicalRecordForm()

        if cita:
            procedimientos = [p.nombre for p in cita.procedimientos.all()]
            procedimientos_txt = ", ".join(procedimientos)

            form.initial["motivo"] = cita.motivo

            fecha_hoy = timezone.localdate().strftime("%d/%m/%Y")

            texto_evolucion = f"{fecha_hoy} – Motivo de cita: {cita.motivo}"
            if procedimientos_txt:
                texto_evolucion += f". Procedimientos: {procedimientos_txt}"
            texto_evolucion += "."

            form.initial["evolucion"] = texto_evolucion

    volver_url = request.GET.get("next") or request.POST.get("next")

    if not volver_url:
        volver_url = reverse("clinical_records_list", args=[paciente.id])

    return render(
        request,
        "core/clinical_record_form.html",
        {
            "form": form,
            "paciente": paciente,
            "fecha_hoy": timezone.localdate().strftime("%d/%m/%Y"),
            "volver_url": volver_url,
            "appointment_id": cita.id if cita else "",
            "odontograma_marcas": json.dumps(obtener_marcas_odontograma(paciente)),
        },
    )


def clinical_record_detail(request, registro_id):
    registro = get_object_or_404(ClinicalRecord, id=registro_id)
    paciente = registro.paciente

    historias = ClinicalRecord.objects.filter(
        paciente=paciente
    ).order_by("-fecha")

    rayos = paciente.rayos_x.all().order_by("-fecha")

    pagos_cobros, pagos_error = obtener_pagos_cobros_paciente(request, paciente)

    edad = calcular_edad(paciente.fecha_nacimiento)

    return render(
        request,
        "core/clinical_record_detail.html",
        {
            "registro": registro,
            "paciente": paciente,
            "edad": edad,
            "historias": historias,
            "rayos": rayos,
            "pagos_cobros": pagos_cobros,
            "pagos_error": pagos_error,
            "odontograma_marcas": json.dumps(obtener_marcas_odontograma(paciente)),
        }
    )


def clinical_record_edit(request, registro_id):
    registro = get_object_or_404(ClinicalRecord, id=registro_id)
    paciente = registro.paciente

    cita_id = request.GET.get("appointment_id") or request.POST.get("appointment_id")
    cita = None

    if cita_id:
        cita = Appointment.objects.filter(
            id=cita_id,
            paciente=paciente
        ).prefetch_related("procedimientos").first()

    if request.method == "POST":
        form = ClinicalRecordForm(request.POST, instance=registro)

        if form.is_valid():
            form.save()
            guardar_odontograma_desde_post(request, paciente)
            return redirect("clinical_record_detail", registro_id=registro.id)

    else:
        form = ClinicalRecordForm(instance=registro)

        hoy = timezone.localdate().strftime("%d/%m/%Y")
        texto_actual = (registro.evolucion or "").strip()

        if cita:
            procedimientos = [p.nombre for p in cita.procedimientos.all()]
            procedimientos_txt = ", ".join(procedimientos)

            nuevo_bloque = f"{hoy} – Motivo de cita: {cita.motivo}"
            if procedimientos_txt:
                nuevo_bloque += f". Procedimientos: {procedimientos_txt}"
            nuevo_bloque += "."

            if texto_actual:
                form.initial["evolucion"] = f"{texto_actual}\n\n{nuevo_bloque}"
            else:
                form.initial["evolucion"] = nuevo_bloque

            if not registro.motivo:
                form.initial["motivo"] = cita.motivo

        else:
            if texto_actual:
                form.initial["evolucion"] = f"{texto_actual}\n{hoy} "
            else:
                form.initial["evolucion"] = f"{hoy} "

    volver_url = request.GET.get("next") or request.POST.get("next")

    if not volver_url:
        volver_url = reverse("clinical_record_detail", args=[registro.id])

    return render(
        request,
        "core/clinical_record_form.html",
        {
            "form": form,
            "paciente": paciente,
            "registro": registro,
            "fecha_hoy": timezone.localdate().strftime("%d/%m/%Y"),
            "volver_url": volver_url,
            "appointment_id": cita.id if cita else "",
            "odontograma_marcas": json.dumps(obtener_marcas_odontograma(paciente)),
        },
    )


def abrir_historia_desde_cita(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)

    cita_id = request.GET.get("appointment_id")
    next_url = request.GET.get("next", "")

    ultimo_registro = (
        ClinicalRecord.objects
        .filter(paciente=paciente)
        .order_by("-fecha", "-id")
        .first()
    )

    if ultimo_registro:
        url = reverse("clinical_record_edit", args=[ultimo_registro.id])

        params = []
        if cita_id:
            params.append(f"appointment_id={cita_id}")
        if next_url:
            params.append(f"next={next_url}")

        if params:
            url += "?" + "&".join(params)

        return redirect(url)

    url = reverse("clinical_record_new", args=[paciente.id])

    params = []
    if cita_id:
        params.append(f"appointment_id={cita_id}")
    if next_url:
        params.append(f"next={next_url}")

    if params:
        url += "?" + "&".join(params)

    return redirect(url)


def clinical_record_open_from_appointment(request, patient_id, appointment_id):
    paciente = get_object_or_404(Patient, id=patient_id)

    cita = get_object_or_404(
        Appointment.objects.prefetch_related("procedimientos"),
        id=appointment_id,
        paciente=paciente
    )

    ultimo_registro = (
        ClinicalRecord.objects.filter(paciente=paciente)
        .order_by("-fecha", "-id")
        .first()
    )

    next_url = request.GET.get("next", "")

    if ultimo_registro:
        url = reverse("clinical_record_edit", args=[ultimo_registro.id])
        params = {
            "appointment_id": cita.id,
        }
        if next_url:
            params["next"] = next_url
        return redirect(f"{url}?{urlencode(params)}")

    url = reverse("clinical_record_new", args=[paciente.id])
    params = {
        "appointment_id": cita.id,
    }
    if next_url:
        params["next"] = next_url
    return redirect(f"{url}?{urlencode(params)}")


def clinical_record_delete(request, registro_id):
    registro = get_object_or_404(ClinicalRecord, id=registro_id)
    paciente_id = registro.paciente.id

    registro.delete()

    return redirect("clinical_records_list", patient_id=paciente_id)


def clinical_record_search(request):
    query = request.GET.get("q", "").strip()

    pacientes_qs = Patient.objects.all()

    if query:
        pacientes_qs = pacientes_qs.filter(
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query) |
            Q(ci__icontains=query) |
            Q(telefono__icontains=query)
        )

    pacientes_qs = pacientes_qs.order_by("apellido", "nombre")

    paginator = Paginator(pacientes_qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "core/clinical_record_search.html",
        {
            "page_obj": page_obj,
            "query": query,
        }
    )



# =========================
# 🔍 BUSCAR PACIENTE → HC
# =========================
def buscar_paciente_hc(request):
    query = request.GET.get("q", "").strip()

    if not query:
        return redirect("/pacientes/")

    patients = Patient.objects.filter(
        Q(nombre__icontains=query) |
        Q(apellido__icontains=query) |
        Q(ci__icontains=query)
    )

    if patients.count() == 1:
        patient = patients.first()
        record = ClinicalRecord.objects.filter(patient=patient).first()

        if record:
            return redirect("clinical_record_detail", id=record.id)
        else:
            return redirect("clinical_record_new", patient_id=patient.id)

    return redirect(f"/pacientes/?q={query}")


# 💰 PRESUPUESTOS

def budgets_list(request):
    presupuestos = Budget.objects.select_related("paciente").order_by("-fecha")

    return render(
        request,
        "core/budgets_list.html",
        {
            "presupuestos": presupuestos
        }
    )


def patient_budgets(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)

    presupuestos = Budget.objects.filter(
        paciente=paciente
    ).order_by("-fecha")

    return render(request, "core/patient_budgets.html", {
        "paciente": paciente,
        "presupuestos": presupuestos,
    })



def budget_new(request, paciente_id):
    """
    Crear un nuevo presupuesto para un paciente específico.
    """

    # 🔒 Paciente fijo (viene desde la URL)
    paciente = get_object_or_404(Patient, id=paciente_id)

    if request.method == "POST":
        diagnostico = request.POST.get("diagnostico")
        conceptos = request.POST.getlist("concepto[]")
        cantidades = request.POST.getlist("cantidad[]")
        valores = request.POST.getlist("valor[]")

        # Crear presupuesto principal
        presupuesto = Budget.objects.create(
            paciente=paciente,
            diagnostico=diagnostico,
            total=0
        )

        total_general = 0

        # Guardar ítems del presupuesto
        for concepto, cantidad, valor in zip(conceptos, cantidades, valores):
            if not concepto or concepto.strip() == "":
                continue

            cantidad = int(cantidad) if cantidad else 0
            valor = float(valor) if valor else 0
            total_item = cantidad * valor

            BudgetItem.objects.create(
                presupuesto=presupuesto,
                concepto=concepto,
                cantidad=cantidad,
                valor=valor,
                total_item=total_item
            )

            total_general += total_item

        # Actualizar total del presupuesto
        presupuesto.total = total_general
        presupuesto.save()

        messages.success(request, "Presupuesto creado correctamente.")
        return redirect("budgets_list")

    # GET → mostrar formulario
    form = BudgetForm()

    return render(
        request,
        "core/budget_form.html",
        {
            "form": form,
            "paciente": paciente  # 👈 para mostrar nombre en el form
        }
    )


# ==========================
# EDITAR PRESUPUESTO
# ==========================



def budget_edit(request, id):
    presupuesto = get_object_or_404(Budget, id=id)

    if request.method == "POST":
        paciente_id = request.POST.get("paciente")
        diagnostico = request.POST.get("diagnostico", "").strip()

        if paciente_id:
            try:
                presupuesto.paciente = Patient.objects.get(id=paciente_id)
            except Patient.DoesNotExist:
                pass

        presupuesto.diagnostico = diagnostico
        presupuesto.save()

        # Borrar items viejos
        presupuesto.items.all().delete()

        conceptos = request.POST.getlist("concepto[]")
        cantidades = request.POST.getlist("cantidad[]")
        valores = request.POST.getlist("valor[]")
        subtotales = request.POST.getlist("subtotal[]")

        total_general = 0

        for c, cant, v, sub in zip(conceptos, cantidades, valores, subtotales):
            c = (c or "").strip()
            if not c:
                continue

            try:
                cantidad = int(cant) if cant else 0
            except ValueError:
                cantidad = 0

            try:
                valor = float(str(v).replace(",", ".")) if v else 0
            except ValueError:
                valor = 0

            try:
                total_item = float(str(sub).replace(",", ".")) if sub else 0
            except ValueError:
                total_item = 0

            BudgetItem.objects.create(
                presupuesto=presupuesto,
                concepto=c,
                cantidad=cantidad,
                valor=valor,
                total_item=total_item
            )

            total_general += total_item

        presupuesto.total = total_general
        presupuesto.save()

        return redirect("budgets_list")

    return render(request, "core/budget_form.html", {
        "presupuesto": presupuesto,
        "items": presupuesto.items.all(),
        "modo": "editar"
    })


# ==========================
# ELIMINAR PRESUPUESTO
# ==========================



def budget_delete(request, id):
    presupuesto = get_object_or_404(Budget, id=id)

    if request.method == "POST":
        presupuesto.delete()
        messages.success(request, "Presupuesto eliminado.")

    return redirect("budgets_list")


def budget_detail(request, id):
    presupuesto = get_object_or_404(Budget, id=id)

    return render(request, "core/budget_detail.html", {
        "presupuesto": presupuesto,
        "items": presupuesto.items.all(),
        "pagos": presupuesto.pagos.all().order_by("-id"),
    })




# ==========================
# IMPRIMIR / PDF
# ==========================
def budget_pdf(request, id):
    presupuesto = get_object_or_404(Budget, id=id)
    items = presupuesto.items.all()

    return render(
        request,
        "core/budget_print.html",
        {
            "presupuesto": presupuesto,
            "items": items,
        }
    )


def budget_print(request, id):
    """
    Vista para imprimir / ver presupuesto en formato PDF (HTML por ahora)
    """
    presupuesto = get_object_or_404(Budget, id=id)
    items = presupuesto.items.all()

    return render(
        request,
        "core/budget_print.html",
        {
            "presupuesto": presupuesto,
            "items": items,
        }
    )

def budget_add_payment(request, id):
    presupuesto = get_object_or_404(Budget, id=id)

    if request.method == "POST":
        form = BudgetPaymentForm(request.POST)

        if form.is_valid():
            pago = form.save(commit=False)
            pago.presupuesto = presupuesto

            if pago.monto <= 0:
                messages.error(request, "El monto debe ser mayor a 0.")
            elif pago.monto > presupuesto.saldo_pendiente:
                messages.error(
                    request,
                    f"El monto no puede ser mayor al saldo pendiente (${presupuesto.saldo_pendiente})."
                )
            else:
                pago.save()

                if presupuesto.estado == "pendiente":
                    presupuesto.estado = "confirmado"
                    presupuesto.save()

                messages.success(request, "Pago registrado correctamente.")
                return redirect("budget_payment_receipt", payment_id=pago.id)

    else:
        form = BudgetPaymentForm()

    return render(request, "core/budget_payment_form.html", {
        "presupuesto": presupuesto,
        "form": form,
    })


def budget_change_status(request, id):
    presupuesto = get_object_or_404(Budget, id=id)

    if request.method == "POST":
        nuevo_estado = request.POST.get("estado")

        estados_validos = [
            "pendiente",
            "confirmado",
            "en_proceso",
            "entregado",
            "cancelado",
        ]

        if nuevo_estado in estados_validos:
            presupuesto.estado = nuevo_estado
            presupuesto.save()

    return redirect("budget_detail", id=presupuesto.id)


def budget_payment_receipt(request, payment_id):
    pago = get_object_or_404(BudgetPayment, id=payment_id)
    presupuesto = pago.presupuesto

    saldo_luego_del_pago = presupuesto.total - sum(
        p.monto for p in presupuesto.pagos.filter(id__lte=pago.id)
    )

    return render(request, "core/budget_payment_receipt.html", {
        "pago": pago,
        "presupuesto": presupuesto,
        "saldo_luego_del_pago": saldo_luego_del_pago,
    })



def budget_payment_delete(request, payment_id):
    pago = get_object_or_404(BudgetPayment, id=payment_id)
    presupuesto_id = pago.presupuesto.id

    if request.method == "POST":
        pago.delete()
        messages.success(request, "Pago eliminado correctamente.")

    return redirect("budget_detail", id=presupuesto_id)


# =============================
# 💵 PAGOS
# =============================
def payments_list(request):
    pagos = Payment.objects.all().order_by("-fecha")
    return render(request, "core/payments.html", {"pagos": pagos})


def payment_new(request):
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("payments_list")
    else:
        form = PaymentForm()
    return render(request, "core/payment_form.html", {"form": form, "titulo": "Nuevo Pago"})


def payment_edit(request, id):
    pago = get_object_or_404(Payment, id=id)
    if request.method == "POST":
        form = PaymentForm(request.POST, instance=pago)
        if form.is_valid():
            form.save()
            return redirect("payments_list")
    else:
        form = PaymentForm(instance=pago)
    return render(request, "core/payment_form.html", {"form": form, "titulo": "Editar Pago"})


def payment_delete(request, id):
    pago = get_object_or_404(Payment, id=id)
    pago.delete()
    return redirect("payments_list")

# =============================
# 🧾 INVENTARIO
# =============================

def inventory_list(request):
    productos = Inventory.objects.all().order_by("nombre")
    return render(request, "core/inventory_list.html", {"productos": productos})


def inventory_new(request):
    if request.method == "POST":
        form = InventoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("inventory_list")
    else:
        form = InventoryForm()

    return render(request, "core/inventory_new.html", {"form": form})


def inventory_edit(request, pk):
    producto = get_object_or_404(Inventory, pk=pk)
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = InventoryForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            if next_url:
                return redirect(next_url)
            return redirect("inventory_list")
    else:
        form = InventoryForm(instance=producto)

    return render(request, "core/inventory_edit.html", {
        "form": form,
        "producto": producto,
        "next": next_url,
    })


def inventory_delete(request, pk):
    producto = get_object_or_404(Inventory, pk=pk)

    if request.method == "POST":
        producto.delete()
        return redirect("inventory_list")

    return render(
        request, 
        "core/inventory_confirmar_eliminar.html", 
        {"producto": producto}
    )


# =============================
# 🦷 PRÓTESIS
# =============================

def protesis_list(request):
    protesis = Prosthesis.objects.all().order_by("-fecha_envio")
    return render(request, "core/protesis_list.html", {"protesis": protesis})


def protesis_new(request):
    if request.method == "POST":
        form = ProsthesisForm(request.POST)

        # 🔍 Imprimir los datos enviados y los errores del formulario
        print("POST DATA:", request.POST)
        print("FORM ERRORS:", form.errors)

        if form.is_valid():
            form.save()
            return redirect("protesis_list")
    else:
        form = ProsthesisForm()

    return render(
        request,
        "core/protesis_form.html",
        {"form": form, "titulo": "Nueva Prótesis"},
    )


def protesis_edit(request, id):
    protesis = get_object_or_404(Prosthesis, id=id)

    if request.method == "POST":
        form = ProsthesisForm(request.POST, instance=protesis)
        if form.is_valid():
            form.save()
            return redirect("protesis_list")
    else:
        form = ProsthesisForm(instance=protesis)

    return render(
        request,
        "core/protesis_form.html",
        {"form": form, "titulo": "Editar Prótesis"},
    )


def protesis_delete(request, id):
    protesis = get_object_or_404(Prosthesis, id=id)
    protesis.delete()
    return redirect("protesis_list")


def protesis_detail(request, id):
    return HttpResponse("Detalle de prótesis aún no implementado.")


def protesis_print(request, id):
    protesis = get_object_or_404(Prosthesis, id=id)

    return render(
        request,
        "core/protesis_print.html",
        {
            "protesis": protesis
        }
    )


# -----------------------------
# AGENDA: MES / SEMANA / DÍA
# -----------------------------

# ============================
# AGENDA DEL DÍA — COMPLETO
# ============================


def generar_horarios():
    """Genera horarios cada 30 minutos de 09:00 a 20:00"""
    hora = time(9, 0)
    lista = []
    for i in range(0, 22):  # 9:00 → 19:00
        lista.append(time(hora.hour, hora.minute))
        # avanzar 30 min
        total_min = hora.hour * 60 + hora.minute + 30
        hora = time(total_min // 60, total_min % 60)
    return lista

def floor_to_30_minutes(hora_obj):
    """
    Redondea hacia abajo una hora al bloque de 30 min.
    Ej:
    10:00 -> 10:00
    10:15 -> 10:00
    10:29 -> 10:00
    10:30 -> 10:30
    10:45 -> 10:30
    """
    total_min = hora_obj.hour * 60 + hora_obj.minute
    bloque_min = (total_min // 30) * 30
    return time(bloque_min // 60, bloque_min % 60)


def agrupar_citas_por_bloque(citas):
    """
    Devuelve un diccionario:
    {
        hora_bloque: [cita1, cita2, ...]
    }
    ordenadas por hora real.
    """
    citas_por_bloque = {}

    for cita in citas:
        bloque = floor_to_30_minutes(cita.hora)

        if bloque not in citas_por_bloque:
            citas_por_bloque[bloque] = []

        citas_por_bloque[bloque].append(cita)

    for bloque in citas_por_bloque:
        citas_por_bloque[bloque].sort(key=lambda c: c.hora)

    return citas_por_bloque



def _decimal_seguro(valor, defecto="0"):
    try:
        if valor is None or valor == "":
            return Decimal(str(defecto))
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(str(defecto))


def obtener_total_cobrable_paciente_desde_pro(paciente, fecha_hasta=None):
    """
    Total de cargos del paciente en Sonrisar Pro.
    Esto NO descuenta pagos. Los pagos se descuentan desde Sonrisar Cobros.
    """
    citas_qs = (
        Appointment.objects
        .filter(paciente=paciente)
        .exclude(estado="cancelado")
    )

    if fecha_hasta:
        citas_qs = citas_qs.filter(fecha__lte=fecha_hasta)

    total = Decimal("0")

    for monto in citas_qs.values_list("monto_total", flat=True):
        total += _decimal_seguro(monto)

    return total


def obtener_resumen_cobros_pacientes_bulk(patient_ids):
    """
    Consulta Sonrisar Cobros UNA sola vez para varios pacientes.
    Esto evita que Agenda del día quede lenta por hacer una consulta HTTP por cada cita.
    """
    patient_ids_limpios = []

    for patient_id in patient_ids:
        try:
            patient_id_int = int(patient_id)
        except (TypeError, ValueError):
            continue

        if patient_id_int not in patient_ids_limpios:
            patient_ids_limpios.append(patient_id_int)

    if not patient_ids_limpios:
        return {}

    cobros_base_url = "https://sonrisar-cobros-1.onrender.com"

    cobros_api_path = getattr(
        settings,
        "SONRISAR_COBROS_API_RESUMEN_PACIENTES_PATH",
        "/pagos/api/resumen-pacientes/"
    )

    api_url = (
        f"{cobros_base_url}"
        f"{cobros_api_path}"
        f"?{urlencode({'patient_ids': ','.join(str(x) for x in patient_ids_limpios)})}"
    )

    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        print("DEBUG COBROS patient_ids:", patient_ids_limpios)
        print("DEBUG COBROS api_url:", api_url)
        print("DEBUG COBROS status:", response.status_code)
        print("DEBUG COBROS data:", data)

        if not data.get("ok"):
            raise ValueError(data.get("error", "Respuesta inválida de Cobros"))

        resumenes = {}

        for item in data.get("pacientes", []):
            patient_id = item.get("patient_id")

            if patient_id is None:
                continue

            try:
                patient_id = int(patient_id)
            except (TypeError, ValueError):
                continue

            resumenes[patient_id] = {
                "ok": True,
                "total_pagado": _decimal_seguro(item.get("total_pagado", 0)),
                "tipo_pago": item.get("tipo_pago", "pagado"),
                "cantidad_pagos": item.get("cantidad_pagos", 0),
                "error": None,
            }

        return resumenes

    except Exception as e:
        print("ERROR CONECTANDO COBROS:", str(e))
        print("ERROR COBROS api_url:", api_url)

        return {
            patient_id: {
                "ok": False,
                "total_pagado": Decimal("0"),
                "tipo_pago": "pagado",
                "cantidad_pagos": 0,
                "error": f"No fue posible conectar con Sonrisar Cobros: {str(e)}",
            }
            for patient_id in patient_ids_limpios
        }


def obtener_resumen_cobros_paciente(paciente):
    """
    Compatibilidad para pantallas que consultan un solo paciente.
    Internamente usa la consulta rápida agrupada.
    """
    resumenes = obtener_resumen_cobros_pacientes_bulk([paciente.id])
    return resumenes.get(paciente.id, {
        "ok": False,
        "total_pagado": Decimal("0"),
        "tipo_pago": "pagado",
        "cantidad_pagos": 0,
        "error": "No fue posible obtener pagos de Cobros.",
    })


def obtener_deuda_total_paciente_desde_pro(paciente, fecha_hasta=None):
    """
    Deuda real del paciente:
    total cobrable en Sonrisar Pro - total pagado/señado en Sonrisar Cobros.
    """
    total_cobrable = obtener_total_cobrable_paciente_desde_pro(
        paciente,
        fecha_hasta=fecha_hasta,
    )

    resumen_cobros = obtener_resumen_cobros_paciente(paciente)
    total_pagado = resumen_cobros.get("total_pagado", Decimal("0"))

    saldo = total_cobrable - total_pagado

    if saldo < 0:
        saldo = Decimal("0")

    return saldo


def obtener_saldo_tratamiento(cita_actual):
    """
    Compatibilidad con código viejo.
    Ya no se heredan saldos por motivo/cita porque eso duplicaba deuda.
    """
    if not cita_actual or not cita_actual.paciente_id:
        return Decimal("0")

    return obtener_deuda_total_paciente_desde_pro(
        cita_actual.paciente,
        fecha_hasta=cita_actual.fecha,
    )


def _obtener_contexto_financiero_citas(citas_dia, fecha):
    """
    Calcula pagos, deuda y saldo a favor de forma cronológica por paciente.

    Regla correcta:
    - Cada cita muestra solo el pago registrado para ESA cita.
    - Si el paciente paga menos que el total acumulado, queda deuda.
    - Si paga de más, queda saldo a favor.
    - El saldo a favor se consume en próximas citas.
    - La deuda mostrada es la deuda real acumulada hasta esa cita.
    """
    contextos = {}

    pacientes_ids = []
    pacientes_por_id = {}

    for cita in citas_dia:
        if cita.paciente_id not in pacientes_ids:
            pacientes_ids.append(cita.paciente_id)
            pacientes_por_id[cita.paciente_id] = cita.paciente

    for patient_id in pacientes_ids:
        paciente = pacientes_por_id[patient_id]

        citas_paciente = list(
            Appointment.objects
            .filter(
                paciente=paciente,
                fecha__lte=fecha
            )
            .exclude(estado="cancelado")
            .select_related("paciente")
            .prefetch_related("procedimientos")
            .order_by("fecha", "hora", "id")
        )

        deuda_acumulada = Decimal("0")
        saldo_a_favor_disponible = Decimal("0")

        for cita in citas_paciente:
            monto_cita = _decimal_seguro(cita.monto_total)

            pago_info = obtener_pago_cobros_cita(
                appointment_id=cita.id,
                patient_id=patient_id
            )

            pago_cita = _decimal_seguro(
                pago_info.get("total_pagado", 0)
            )

            tiene_pago_cita = pago_cita > 0

            deuda_cita = Decimal("0")
            saldo_usado = Decimal("0")
            saldo_generado = Decimal("0")

            if monto_cita > 0:
                deuda_acumulada += monto_cita

            # Primero aplicamos saldo a favor anterior, si existe
            if deuda_acumulada > 0 and saldo_a_favor_disponible > 0:
                saldo_usado = min(
                    saldo_a_favor_disponible,
                    deuda_acumulada
                )
                deuda_acumulada -= saldo_usado
                saldo_a_favor_disponible -= saldo_usado

            # Después aplicamos pago de esta cita
            if pago_cita > 0:
                if deuda_acumulada > 0:
                    if pago_cita >= deuda_acumulada:
                        sobra = pago_cita - deuda_acumulada
                        deuda_acumulada = Decimal("0")

                        if sobra > 0:
                            saldo_generado = sobra
                            saldo_a_favor_disponible += sobra
                    else:
                        deuda_acumulada -= pago_cita
                else:
                    saldo_generado = pago_cita
                    saldo_a_favor_disponible += pago_cita

            deuda_cita = deuda_acumulada

            contextos[cita.id] = {
                "pago_cita": pago_cita,
                "tiene_pago_cita": tiene_pago_cita,
                "tipo_pago": pago_info.get("tipo_pago", "pagado"),
                "deuda_cita": deuda_cita,
                "saldo_usado": saldo_usado,
                "saldo_generado": saldo_generado,
                "saldo_a_favor_restante": saldo_a_favor_disponible,
                "tiene_saldo_generado": saldo_generado > 0,
                "usa_saldo_a_favor": saldo_usado > 0 and not tiene_pago_cita,
                "cobros_error": pago_info.get("error"),
            }

    return contextos


def _armar_cita_agenda_rapida(cita, contextos_financieros):
    contexto_financiero = contextos_financieros.get(cita.id, {})

    edad = calcular_edad(cita.paciente.fecha_nacimiento)

    monto_total = _decimal_seguro(cita.monto_total)
    pago_cita = _decimal_seguro(contexto_financiero.get("pago_cita", 0))
    deuda_cita = _decimal_seguro(contexto_financiero.get("deuda_cita", 0))
    saldo_generado = _decimal_seguro(contexto_financiero.get("saldo_generado", 0))
    saldo_usado = _decimal_seguro(contexto_financiero.get("saldo_usado", 0))
    saldo_a_favor_restante = _decimal_seguro(
        contexto_financiero.get("saldo_a_favor_restante", 0)
    )

    tiene_pago_cita = pago_cita > 0
    tiene_monto = monto_total > 0
    cita_atendida = cita.estado == "asistio"

    tiene_entrega_parcial = tiene_pago_cita and deuda_cita > 0
    cita_pagada_visual = tiene_monto and deuda_cita <= 0

    tiene_saldo_generado = saldo_generado > 0
    usa_saldo_a_favor = saldo_usado > 0 and not tiene_pago_cita

    mostrar_pago_cobros = (
        tiene_pago_cita
        or tiene_saldo_generado
        or usa_saldo_a_favor
        or (cita_atendida and cita_pagada_visual)
    )

    if tiene_saldo_generado:
        tipo_pago_visual = "saldo_a_favor"
    elif usa_saldo_a_favor:
        tipo_pago_visual = "saldo_usado"
    elif tiene_entrega_parcial:
        tipo_pago_visual = "sena"
    elif cita_pagada_visual:
        tipo_pago_visual = "pagado"
    else:
        tipo_pago_visual = "pendiente"

    return {
        "id": cita.id,
        "patient_id": cita.paciente.id,
        "hora_real": cita.hora,
        "paciente": f"{cita.paciente.apellido}, {cita.paciente.nombre}",
        "edad": edad,
        "motivo": cita.motivo,
        "motivo_slug": slugify(cita.motivo or ""),
        "procedimientos": [p.nombre for p in cita.procedimientos.all()],
        "estado": cita.get_estado_display(),
        "estado_slug": cita.estado,
        "pagado": cita_pagada_visual,
        "tiene_pago_cobros": mostrar_pago_cobros,
        "total_pagado": str(pago_cita),
        "total_pagado_paciente": str(pago_cita),
        "tipo_pago": tipo_pago_visual,
        "monto_total": monto_total,
        "total_cobrable_paciente": monto_total,
        "debe": deuda_cita,
        "deuda_total_paciente": deuda_cita,
        "saldo_a_favor": saldo_generado,
        "saldo_a_favor_restante": saldo_a_favor_restante,
        "saldo_usado": saldo_usado,
        "tiene_saldo_a_favor": tiene_saldo_generado,
        "usa_saldo_a_favor": usa_saldo_a_favor,
        "cobros_error": contexto_financiero.get("cobros_error"),
    }


def agenda_day(request, day, month, year):
    fecha = date(year, month, day)
    print("DEBUG AGENDA_DAY EJECUTADA", fecha)

    dia_bloqueado = DayBlock.objects.filter(
        fecha=fecha
    ).first()

    citas = list(
        Appointment.objects.filter(fecha=fecha)
        .select_related("paciente")
        .prefetch_related("procedimientos")
        .order_by("hora", "id")
    )

    HORARIOS_BLOQUEADOS = {"14:00", "14:30"}

    contextos_financieros = _obtener_contexto_financiero_citas(
        citas,
        fecha
    )

    citas_por_bloque = agrupar_citas_por_bloque(citas)

    horarios = []

    for h in generar_horarios():
        hora_txt = h.strftime("%H:%M")

        if dia_bloqueado:
            horarios.append({
                "hora": h,
                "bloqueado": True,
                "motivo": dia_bloqueado.motivo or "Día bloqueado",
                "ocupado_exacto": False,
                "citas_exactas": [],
                "citas_extra": [],
            })
            continue

        if hora_txt in HORARIOS_BLOQUEADOS:
            horarios.append({
                "hora": h,
                "bloqueado": True,
                "motivo": "Descanso",
                "ocupado_exacto": False,
                "citas_exactas": [],
                "citas_extra": [],
            })
            continue

        citas_en_bloque = citas_por_bloque.get(h, [])

        citas_exactas = [
            c for c in citas_en_bloque
            if c.hora == h
        ]

        citas_extra = [
            c for c in citas_en_bloque
            if c.hora != h
        ]

        citas_exactas_data = [
            _armar_cita_agenda_rapida(
                cita,
                contextos_financieros
            )
            for cita in citas_exactas
        ]

        citas_extra_data = [
            _armar_cita_agenda_rapida(
                cita,
                contextos_financieros
            )
            for cita in citas_extra
        ]

        horarios.append({
            "hora": h,
            "bloqueado": False,
            "motivo": "",
            "ocupado_exacto": len(citas_exactas) > 0,
            "citas_exactas": citas_exactas_data,
            "citas_extra": citas_extra_data,
        })

    deudores = []
    pacientes_ya_agregados = set()

    if not dia_bloqueado:
        for h in horarios:
            if h.get("bloqueado"):
                continue

            for cita in h.get("citas_exactas", []) + h.get("citas_extra", []):
                debe = _decimal_seguro(cita.get("debe", 0))
                patient_id = cita.get("patient_id")

                if debe > 0 and patient_id not in pacientes_ya_agregados:
                    deudores.append(cita)
                    pacientes_ya_agregados.add(patient_id)

    total_deuda_dia = sum(
        (_decimal_seguro(d.get("debe", 0)) for d in deudores),
        Decimal("0")
    )

    return render(
        request,
        "core/agenda_day.html",
        {
            "fecha": fecha,
            "horarios": horarios,
            "deudores": deudores,
            "total_deuda_dia": total_deuda_dia,
            "dia_bloqueado": dia_bloqueado,
        }
    )


def _absolute_url(request, path_or_url):
    """
    Convierte una ruta relativa (/agenda/...) en URL absoluta.
    Si ya viene absoluta, la devuelve tal cual.
    """
    if not path_or_url:
        return ""

    path_or_url = path_or_url.strip()

    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url

    return request.build_absolute_uri(path_or_url)


def cobros_nuevo_desde_cita(request, appointment_id):
    cita = get_object_or_404(
        Appointment.objects.select_related("paciente"),
        id=appointment_id
    )

    cobros_base_url = getattr(
        settings,
        "SONRISAR_COBROS_BASE_URL",
        "https://sonrisar-cobros-1.onrender.com"
    ).rstrip("/")

    cobros_path = getattr(
        settings,
        "SONRISAR_COBROS_NUEVO_PATH",
        "/pagos/nuevo/"
    )

    paciente_nombre = f"{cita.paciente.apellido}, {cita.paciente.nombre}".strip(", ")

    # Puede venir relativo o absoluto
    next_param = request.GET.get("next", "").strip()
    next_url = _absolute_url(request, next_param) if next_param else ""

    # URL intermedia en Sonrisar Pro:
    # Cobros guarda -> vuelve aquí -> aquí marcamos Asistió -> redirigimos al destino final
    confirmar_pago_url = request.build_absolute_uri(
        reverse("confirmar_pago_desde_cobros")
    )

    confirmar_params = {
        "appointment_id": cita.id,
    }

    if next_url:
        confirmar_params["next"] = next_url

    confirmar_pago_url = f"{confirmar_pago_url}?{urlencode(confirmar_params)}"

    params = {
        "paciente": paciente_nombre,
        "concepto": cita.motivo or "Consulta odontológica",
        "appointment_id": cita.id,
        "patient_id": cita.paciente.id,
        "fecha_cita": cita.fecha.strftime("%Y-%m-%d"),
        "next": confirmar_pago_url,
    }

    ci = getattr(cita.paciente, "ci", "")
    if ci:
        params["ci"] = ci

    cobros_url = f"{cobros_base_url}{cobros_path}?{urlencode(params)}"
    return redirect(cobros_url)


def confirmar_pago_desde_cobros(request):
    appointment_id = request.GET.get("appointment_id")
    next_url = request.GET.get("next", "").strip()

    if not appointment_id:
        messages.warning(request, "No se recibió la cita a actualizar.")
        return redirect(next_url or reverse("agenda_pro"))

    cita = get_object_or_404(Appointment, id=appointment_id)

    if cita.estado != "cancelado":
        cita.estado = "asistio"

    cita.save()

    cita.refresh_from_db()

    messages.success(
        request,
        f"Pago registrado. Estado: {cita.estado} | Pagado: {cita.pagado}"
    )
    return redirect(next_url or reverse("agenda_pro"))



def cobros_nuevo_desde_paciente(request, patient_id):
    paciente = get_object_or_404(Patient, id=patient_id)

    cobros_base_url = getattr(
        settings,
        "SONRISAR_COBROS_BASE_URL",
        "https://sonrisar-cobros-1.onrender.com"
    ).rstrip("/")

    cobros_path = getattr(
        settings,
        "SONRISAR_COBROS_NUEVO_PATH",
        "/pagos/nuevo/"
    )

    paciente_nombre = f"{paciente.apellido}, {paciente.nombre}".strip(", ")

    next_param = request.GET.get("next", "").strip()
    next_url = _absolute_url(request, next_param) if next_param else ""

    params = {
        "paciente": paciente_nombre,
        "concepto": "Pago odontológico",
        "patient_id": paciente.id,
    }

    ci = getattr(paciente, "ci", "")
    if ci:
        params["ci"] = ci

    if next_url:
        params["next"] = next_url

    cobros_url = f"{cobros_base_url}{cobros_path}?{urlencode(params)}"
    return redirect(cobros_url)


def obtener_pagos_cobros_paciente(request, paciente):
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

    paciente_nombre = f"{paciente.apellido}, {paciente.nombre}".strip(", ")

    api_url = f"{cobros_base_url}{cobros_api_path}?{urlencode({'paciente': paciente_nombre})}"

    try:
        with urlopen(api_url, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("ok"):
            return data.get("pagos", []), None

        return [], data.get("error", "No se pudieron obtener los pagos.")

    except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        return [], "No fue posible conectar con Sonrisar Cobros."
        

def obtener_pago_cobros_cita(
    appointment_id,
    patient_id=None
):

    cobros_base_url = getattr(
        settings,
        "SONRISAR_COBROS_BASE_URL",
        "https://sonrisar-cobros-1.onrender.com"
    ).rstrip("/")

    cobros_api_path = getattr(
        settings,
        "SONRISAR_COBROS_API_CITA_PATH",
        "/pagos/api/por-cita/"
    )

    params = {
        "appointment_id": appointment_id,
    }

    # =====================================
    # NUEVO
    # =====================================
    if patient_id:
        params["patient_id"] = patient_id

    api_url = (
        f"{cobros_base_url}"
        f"{cobros_api_path}"
        f"?{urlencode(params)}"
    )

    try:

        with urlopen(api_url, timeout=6) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        total_pagado = Decimal(
            str(data.get("total_pagado", 0))
        )

        if data.get("ok"):

            return {
                "tiene_pago": total_pagado > 0,
                "total_pagado": str(total_pagado),
                "tipo_pago": data.get(
                    "tipo_pago",
                    "pagado"
                ),
                "pagos": data.get(
                    "pagos",
                    []
                ),
                "error": None,
            }

        return {
            "tiene_pago": False,
            "total_pagado": "0",
            "tipo_pago": "pagado",
            "pagos": [],
            "error": data.get(
                "error",
                "No se pudo obtener el pago."
            ),
        }

    except (
        URLError,
        HTTPError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError
    ):

        return {
            "tiene_pago": False,
            "total_pagado": "0",
            "tipo_pago": "pagado",
            "pagos": [],
            "error": (
                "No fue posible conectar "
                "con Sonrisar Cobros."
            ),
        }

def obtener_pacientes_con_pago(request, pacientes):
    """
    Devuelve un set con ids de pacientes que tienen al menos un pago
    registrado en Sonrisar Cobros.
    """
    pacientes_pagados = set()

    for paciente in pacientes:
        pagos, error = obtener_pagos_cobros_paciente(request, paciente)
        if pagos and not error:
            pacientes_pagados.add(paciente.id)

    return pacientes_pagados



def agenda_week(request):
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # lunes
    fin_semana = inicio_semana + timedelta(days=6)

    selected_day = request.GET.get("day")  # 1=lunes ... 7=domingo

    # Citas de la semana (optimizado)
    citas_qs = (
        Appointment.objects.filter(fecha__range=[inicio_semana, fin_semana])
        .select_related("paciente")
        .order_by("fecha", "hora")
    )

    if selected_day:
        citas_qs = citas_qs.filter(fecha__iso_week_day=int(selected_day))

    # Lista de días a mostrar (si filtra, mostramos solo ese día)
    if selected_day:
        dias = [inicio_semana + timedelta(days=int(selected_day) - 1)]
    else:
        dias = [inicio_semana + timedelta(days=i) for i in range(7)]

    # Armamos la grilla: por cada día, todos los horarios + ocupado/libre
    week_grid = []
    horarios_base = generar_horarios()  # 09:00 a 19:30 cada 30 min

    for dia in dias:
        citas_del_dia = [c for c in citas_qs if c.fecha == dia]
        citas_por_hora = {c.hora: c for c in citas_del_dia}

        slots = []
        for h in horarios_base:
            cita = citas_por_hora.get(h)
            if cita:
                slots.append({
                    "hora": h,
                    "ocupado": True,
                    "id": cita.id,
                    "paciente": f"{cita.paciente.apellido}, {cita.paciente.nombre}",
                    "motivo": cita.motivo,
                    "estado": cita.estado,
                })
            else:
                slots.append({
                    "hora": h,
                    "ocupado": False,
                })

        week_grid.append({
            "fecha": dia,
            "slots": slots
        })

    contexto = {
        "week_grid": week_grid,
        "inicio": inicio_semana,
        "fin": fin_semana,
        "selected_day": selected_day,
    }

    return render(request, "core/agenda_week.html", contexto)


def agenda_month(request):
    hoy = date.today()
    primer_dia = hoy.replace(day=1)

    if hoy.month == 12:
        ultimo_dia = date(hoy.year, 12, 31)
    else:
        ultimo_dia = date(hoy.year, hoy.month + 1, 1) - timedelta(days=1)

    citas = Appointment.objects.filter(
        fecha__range=[primer_dia, ultimo_dia]
    ).order_by("fecha", "hora")

    # 🔥 FORMATO LISTO, SIMPLE, SIN FILTROS DJANGO
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "setiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }

    primer_texto = f"{primer_dia.day} de {meses[primer_dia.month]} de {primer_dia.year}"
    ultimo_texto = f"{ultimo_dia.day} de {meses[ultimo_dia.month]} de {ultimo_dia.year}"

    contexto = {
        "primer_texto": primer_texto,
        "ultimo_texto": ultimo_texto,
        "citas": citas,
    }

    return render(request, "core/agenda_month.html", contexto)


def cita_recordatorio(request, id):
    cita = get_object_or_404(Appointment, id=id)

    paciente = cita.paciente
    telefono = paciente.telefono  # CONFIRMAR si se llama "telefono" en tu modelo
    nombre = paciente.nombre

    fecha = cita.fecha.strftime("%d/%m/%Y")
    hora = cita.hora.strftime("%H:%M")

    mensaje = (
        f"Hola {nombre}, te recordamos tu cita odontológica para el día {fecha} "
        f"a las {hora} en Sonrisar - Centro Odontológico. "
        f"Dirección: Román Guerra 752. "
        f"Ubicación en Google Maps: https://maps.app.goo.gl/6X9d13YqcqVb8sGw8 "
        f"Si necesitás reprogramar o cancelar, escribinos al 092706293. "
        f"¡Te esperamos!"
    )

    params = urlencode({"text": mensaje})
    url = f"https://wa.me/598{telefono}?{params}"

    return redirect(url)

def recordatorios_manana(request):
    manana = date.today() + timedelta(days=1)
    citas = Appointment.objects.filter(fecha=manana)

    if not citas.exists():
        messages.warning(request, "No hay citas para mañana.")
        return redirect("agenda_day")

    # Obtener la primera cita de mañana
    cita = citas.first()
    paciente = cita.paciente

    telefono = paciente.telefono
    nombre = paciente.nombre
    fecha = cita.fecha.strftime("%d/%m/%Y")
    hora = cita.hora.strftime("%H:%M")

    mensaje = (
        f"Hola {nombre}, te recordamos tu cita odontológica para el día {fecha} "
        f"a las {hora} en Sonrisar - Centro Odontológico. "
        f"Dirección: Román Guerra 752. "
        f"Ubicación en Google Maps: https://maps.app.goo.gl/6X9d13YqcqVb8sGw8 "
        f"Si necesitás reprogramar o cancelar, escribinos al 092706293. "
        f"¡Te esperamos!"
    )

    params = urlencode({"text": mensaje})
    url = f"https://wa.me/598{telefono}?{params}"

    return redirect(url)


def iniciar_recordatorios_manana(request):
    manana = date.today() + timedelta(days=1)
    citas = Appointment.objects.filter(fecha=manana).order_by("hora")

    if not citas.exists():
        messages.warning(request, "No hay citas para mañana.")
        return redirect("whatsapp_reminders")

    request.session["recordatorios_lista"] = [c.id for c in citas]

    return redirect("siguiente_recordatorio")


def siguiente_recordatorio(request):
    lista = request.session.get("recordatorios_lista", [])

    # Si ya no quedan
    if not lista:
        messages.success(request, "Todos los recordatorios fueron enviados correctamente.")
        return redirect("agenda_day")

    cita_id = lista.pop(0)
    request.session["recordatorios_lista"] = lista

    cita = get_object_or_404(Appointment, id=cita_id)
    paciente = cita.paciente

    telefono = paciente.telefono
    nombre = paciente.nombre
    fecha = cita.fecha.strftime("%d/%m/%Y")
    hora = cita.hora.strftime("%H:%M")

    # 🔹 MENSAJE PROLIJO SIN 'text=' Y SIN LINK LARGO
    mensaje = (
        f"Hola {nombre} 😊\n"
        f"Te recordamos tu cita odontológica para el *{fecha}* a las *{hora}* en Sonrisar - Centro Odontológico.\n\n"
        f"📍 Dirección: Román Guerra 752\n"
        f"🗺️ Ubicación: https://maps.google.com/?q=Roman+Guerra+752+Maldonado+Uruguay\n\n"
        f"Si necesitás reprogramar o cancelar, escribinos al 092 706 293.\n"
        f"¡Te esperamos! ✨"
    )


    params = urlencode({"text": mensaje})
    url_whatsapp = f"https://web.whatsapp.com/send?phone=598{telefono}&{params}"

    return render(request, "core/esperando.html", {"url_whatsapp": url_whatsapp})


def cita_recordatorio(request, id):
    cita = get_object_or_404(Appointment, id=id)

    paciente = cita.paciente
    telefono = paciente.telefono
    nombre = paciente.nombre

    fecha = cita.fecha.strftime("%d/%m/%Y")
    hora = cita.hora.strftime("%H:%M")

    mensaje = (
        f"Hola {nombre} 😊\n\n"
        f"Te recordamos tu cita odontológica para el *{fecha}* "
        f"a las *{hora}* en *Sonrisar – Centro Odontológico*.\n\n"
        f"📍 Dirección: Román Guerra 752\n"
        f"🗺️ Ubicación: https://maps.google.com/?q=Roman+Guerra+752+Maldonado+Uruguay\n\n"
        f"Si necesitás reprogramar o cancelar, escribinos al 092 706 293.\n\n"
        f"¡Te esperamos! 🦷✨"
    )

    params = urlencode({"text": mensaje})
    url = f"https://wa.me/598{telefono}?{params}"

    return redirect(url)

def confirmar_envio(request):
    lista = request.session.get("recordatorios_lista", [])

    if lista:
        lista.pop(0)  # ahora sí sacamos el anterior
        request.session["recordatorios_lista"] = lista

    if not lista:
        messages.success(request, "Todos los recordatorios fueron enviados.")
        return redirect("whatsapp_reminders")

    return redirect("siguiente_recordatorio")


# VISTA DEL CALENDARIO MENSUAL
def agenda_mensual_calendario(request):
    hoy = date.today()
    year = int(request.GET.get("year", hoy.year))
    month = int(request.GET.get("month", hoy.month))

    q = request.GET.get("q", "").strip()
    resultados = None

    if q:
        resultados = Appointment.objects.filter(
            Q(paciente__nombre__icontains=q) |
            Q(paciente__apellido__icontains=q) |
            Q(paciente__ci__icontains=q) |
            Q(motivo__icontains=q)
        ).select_related("paciente").order_by("fecha", "hora")

    cal = calendar.Calendar(firstweekday=0)
    semanas = cal.monthdayscalendar(year, month)

    citas = (
        Appointment.objects.filter(
            fecha__year=year,
            fecha__month=month
        )
        .select_related("paciente")
        .order_by("fecha", "hora")
    )

    citas_por_dia = {}
    for cita in citas:
        dia = cita.fecha.day
        citas_por_dia.setdefault(dia, []).append(cita)

    bloqueos_mes = DayBlock.objects.filter(
        fecha__year=year,
        fecha__month=month
    )

    bloqueos_por_dia = {
        bloqueo.fecha.day: bloqueo
        for bloqueo in bloqueos_mes
    }

    horarios_base = generar_horarios()
    slots_por_dia = {}
    HORARIOS_BLOQUEADOS = {"14:00", "14:30"}

    dias_en_grilla = set()
    for semana in semanas:
        for d in semana:
            if d != 0:
                dias_en_grilla.add(d)

    for d in dias_en_grilla:
        dia_bloqueado = bloqueos_por_dia.get(d)
        citas_del_dia = citas_por_dia.get(d, [])
        citas_por_bloque = agrupar_citas_por_bloque(citas_del_dia)

        slots = []

        for h in horarios_base:
            hora_txt = h.strftime("%H:%M")

            if dia_bloqueado:
                slots.append({
                    "hora": h,
                    "ocupado": False,
                    "bloqueado": True,
                    "motivo_bloqueo": dia_bloqueado.motivo or "Día bloqueado",
                    "citas": [],
                })
                continue

            if hora_txt in HORARIOS_BLOQUEADOS:
                slots.append({
                    "hora": h,
                    "ocupado": False,
                    "bloqueado": True,
                    "motivo_bloqueo": "Descanso",
                    "citas": [],
                })
                continue

            citas_en_bloque = citas_por_bloque.get(h, [])

            if citas_en_bloque:
                slots.append({
                    "hora": h,
                    "ocupado": True,
                    "bloqueado": False,
                    "citas": [
                        {
                            "id": c.id,
                            "patient_id": c.paciente.id,
                            "hora_real": c.hora,
                            "paciente": f"{c.paciente.apellido}, {c.paciente.nombre}",
                            "motivo": c.motivo,
                            "estado": c.estado,
                        }
                        for c in citas_en_bloque
                    ],
                })
            else:
                slots.append({
                    "hora": h,
                    "ocupado": False,
                    "bloqueado": False,
                    "citas": [],
                })

        slots_por_dia[d] = slots

    slots_por_dia_str = {str(k): v for k, v in slots_por_dia.items()}

    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1

    MESES = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    return render(
        request,
        "core/agenda_mensual_calendario.html",
        {
            "hoy": hoy,
            "year": year,
            "month": month,
            "nombre_mes": MESES[month],
            "semanas": semanas,
            "citas_por_dia": citas_por_dia,
            "slots_por_dia": slots_por_dia,
            "slots_por_dia_str": slots_por_dia_str,
            "bloqueos_por_dia": bloqueos_por_dia,
            "prev_month": prev_month,
            "prev_year": prev_year,
            "next_month": next_month,
            "next_year": next_year,
            "q": q,
            "resultados": resultados,
        }
    )

# ENDPOINT JSON PARA FULLCALENDAR

def agenda_citas_json(request):
    citas = Appointment.objects.select_related("paciente")

    eventos = []
    for cita in citas:
        eventos.append({
            "id": cita.id,
            "title": f"{cita.paciente}",   # nombre del paciente
            "start": f"{cita.fecha}T{cita.hora}",
            "url": reverse("appointment_edit", args=[cita.id]),
            "extendedProps": {
                "estado": cita.estado,
                "motivo": cita.motivo,    # ← AGREGADO
            }
        })

    return JsonResponse(eventos, safe=False)


# 📅 AGENDA SEMANAL (CALENDARIO)
def agenda_semanal_calendario(request):
    return render(request, "core/agenda_semanal_calendario.html")


def patient_delete(request, id):
    paciente = get_object_or_404(Patient, id=id)

    if request.method == "POST":
        paciente.delete()
        return redirect("patient_list")

    return render(request, "core/patient_confirm_delete.html", {
        "paciente": paciente
    })


# =============================
# 📅 AGENDA (alias seguro)
# =============================
def agenda(request):
    return redirect("citas_list")


# =============================
# 📲 WHATSAPP (recordatorios)
# =============================

def iniciar_recordatorios_manana(request):
    manana = date.today() + timedelta(days=1)
    citas = Appointment.objects.filter(fecha=manana).order_by("hora")

    if not citas.exists():
        messages.warning(request, "No hay citas para mañana.")
        return redirect("agenda_day")

    request.session["recordatorios_lista"] = [c.id for c in citas]
    return redirect("siguiente_recordatorio")


def siguiente_recordatorio(request):
    lista = request.session.get("recordatorios_lista", [])

    if not lista:
        messages.success(request, "Todos los recordatorios fueron enviados correctamente.")
        return redirect("whatsapp_reminders")

    cita_id = lista[0]  # NO sacamos aún hasta confirmar
    cita = get_object_or_404(Appointment, id=cita_id)

    paciente = cita.paciente
    telefono = (paciente.telefono or "").strip()

    if not telefono:
        messages.warning(request, f"El paciente {paciente} no tiene teléfono cargado. Se salta.")
        lista.pop(0)
        request.session["recordatorios_lista"] = lista
        return redirect("siguiente_recordatorio")

    # Armamos mensaje
    fecha_txt = cita.fecha.strftime("%d/%m/%Y")
    hora_txt = cita.hora.strftime("%H:%M")

    mensaje = (
        f"Hola {paciente.nombre} 😊\n"
        f"Te recordamos tu cita odontológica para el *{fecha_txt}* a las *{hora_txt}* "
        f"en Sonrisar - Centro Odontológico.\n\n"
        f"📍 Dirección: Román Guerra 752\n"
        f"🗺️ Ubicación: https://maps.google.com/?q=Roman+Guerra+752+Maldonado+Uruguay\n\n"
        f"Si necesitás reprogramar o cancelar, escribinos al 092 706 293.\n"
        f"¡Te esperamos! ✨"
    )

    params = urlencode({"text": mensaje})

    # Normalizamos teléfono: dejamos solo números
    telefono_num = "".join([c for c in telefono if c.isdigit()])

    # Si el usuario guarda teléfonos sin el 598, lo agregamos
    if telefono_num.startswith("0"):
        telefono_num = telefono_num[1:]  # 092xxxxxx -> 92xxxxxx
    if not telefono_num.startswith("598"):
        telefono_num = "598" + telefono_num

    url_whatsapp = f"https://web.whatsapp.com/send?phone={telefono_num}&{params}"

    return render(request, "core/esperando.html", {"url_whatsapp": url_whatsapp, "cita": cita})


def confirmar_envio(request):
    lista = request.session.get("recordatorios_lista", [])

    if lista:
        lista.pop(0)  # ahora sí sacamos el anterior
        request.session["recordatorios_lista"] = lista

    if not lista:
        messages.success(request, "Todos los recordatorios fueron enviados.")
        return redirect("whatsapp_reminders")

    return redirect("siguiente_recordatorio")


def cita_recordatorio(request, id):
    cita = get_object_or_404(Appointment, id=id)

    paciente = cita.paciente
    telefono = (paciente.telefono or "").strip()

    if not telefono:
        messages.warning(request, "Este paciente no tiene teléfono cargado.")
        return redirect("whatsapp_reminders")

    fecha_txt = cita.fecha.strftime("%d/%m/%Y")
    hora_txt = cita.hora.strftime("%H:%M")

    mensaje = (
        f"Hola {paciente.nombre} 😊\n"
        f"Te recordamos tu cita odontológica para el *{fecha_txt}* a las *{hora_txt}* "
        f"en Sonrisar - Centro Odontológico.\n\n"
        f"📍 Dirección: Román Guerra 752\n"
        f"🗺️ Ubicación: https://maps.google.com/?q=Roman+Guerra+752+Maldonado+Uruguay\n\n"
        f"Si necesitás reprogramar o cancelar, escribinos al 092 706 293.\n"
        f"¡Te esperamos! ✨"
    )

    params = urlencode({"text": mensaje})

    telefono_num = "".join([c for c in telefono if c.isdigit()])
    if telefono_num.startswith("0"):
        telefono_num = telefono_num[1:]
    if not telefono_num.startswith("598"):
        telefono_num = "598" + telefono_num

    url_whatsapp = f"https://web.whatsapp.com/send?phone={telefono_num}&{params}"
    return redirect(url_whatsapp)

def whatsapp_reminders(request):
    manana = date.today() + timedelta(days=1)
    citas = Appointment.objects.filter(
        fecha=manana
    ).select_related("paciente").order_by("hora")

    if request.method == "POST":
        if not citas.exists():
            messages.warning(request, "No hay citas para mañana.")
            return redirect("agenda_day")

        primera_cita = citas.first()
        return redirect("whatsapp_paciente", primera_cita.id)

    return render(
        request,
        "core/whatsapp_reminders.html",
        {
            "citas": citas,
            "manana": manana
        }
    )



def whatsapp_paciente(request, id):
    cita = get_object_or_404(Appointment, id=id)
    paciente = cita.paciente

    # ---------- DÍA EN ESPAÑOL ----------
    DIAS_ES = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
    }

    dia_en = cita.fecha.strftime("%A")
    dia = DIAS_ES.get(dia_en, dia_en)

    fecha = cita.fecha.strftime("%d/%m/%Y")
    hora = cita.hora.strftime("%H:%M")

    # ---------- TELÉFONO ----------
    telefono = (paciente.telefono or "").strip().replace(" ", "").replace("-", "")
    if not telefono.startswith("598"):
        telefono = "598" + telefono

    # ---------- MENSAJE WHATSAPP ----------
    mensaje = (
        "⚠️ ATENCIÓN: NOS ENCONTRAMOS EN NUEVA DIRECCIÓN ⚠️\n\n"
        f"Hola {paciente.nombre} 👋 Sonrisar Centro Odontológico te recuerda tu turno para "
        f"{dia} {fecha} a las {hora}.\n\n"
        "📍 Dirección: Román Guerra 752\Local 101\n"
        "🗺️ Ubicación: https://maps.google.com/?q=Roman+Guerra+752+Maldonado+Uruguay\n\n"
        "Para dejar tu turno asegurado, respondé “Confirmo”, por favor. ✅\n"
        "Si no recibimos confirmación, el turno podría cancelarse y liberarse para otro paciente.\n\n"
        "¡Gracias por tu comprensión!"
    )

    mensaje_url = quote(mensaje)

    # ---------- ABRIR WHATSAPP WEB ----------
    url_whatsapp = f"https://web.whatsapp.com/send?phone={telefono}&text={mensaje_url}"

    return redirect(url_whatsapp)


# =========================
# RAYOS X
# =========================

def rayos_x_list(request, paciente_id):
    paciente = get_object_or_404(Patient, id=paciente_id)
    rayos = RayosX.objects.filter(paciente=paciente).order_by("-fecha")

    return render(
        request,
        "core/rayos_x_list.html",
        {
            "paciente": paciente,
            "rayos": rayos,
        }
    )


def rayos_x_new(request, paciente_id):
    paciente = get_object_or_404(Patient, id=paciente_id)

    if request.method == "POST":
        form = RayosXForm(request.POST, request.FILES)
        if form.is_valid():
            rx = form.save(commit=False)
            rx.paciente = paciente
            rx.save()
            return redirect("rayos_x_list", paciente_id=paciente.id)
    else:
        form = RayosXForm()

    return render(
        request,
        "core/rayos_x_form.html",
        {
            "form": form,
            "paciente": paciente,
        }
    )


def rayos_x_detail(request, rx_id):
    rx = get_object_or_404(RayosX, id=rx_id)

    return render(
        request,
        "core/rayos_x_detail.html",
        {
            "rx": rx,
        }
    )


def rayos_x_delete(request, rx_id):
    rx = get_object_or_404(RayosX, id=rx_id)
    paciente_id = rx.paciente.id

    if request.method == "POST":
        rx.delete()
        return redirect("rayos_x_list", paciente_id=paciente_id)

    return render(
        request,
        "core/rayos_x_confirm_delete.html",
        {
            "rx": rx,
        }
    )

# ============================
# LISTA DE TODAS LAS CITAS
# ============================
def lista_de_citas(request):
    citas = Appointment.objects.select_related("paciente").order_by("fecha", "hora")
    return render(request, "core/appointments_list.html", {"citas": citas})


# =============================
# INVENTARIO
# =============================

def inventory_list(request):
    query = request.GET.get("q", "")

    productos = Inventory.objects.all().order_by("nombre")

    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) |
            Q(codigo__icontains=query) |
            Q(categoria__icontains=query) |
            Q(proveedor__icontains=query)
        )

    paginator = Paginator(productos, 20)  # 👈 20 productos por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "core/inventory_list.html",
        {
            "productos": page_obj,
            "query": query,
            "page_obj": page_obj,
        }
    )



def inventory_new(request):
    if request.method == "POST":
        form = InventoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("inventory_list")
    else:
        form = InventoryForm()

    return render(request, "core/inventory_form.html", {
        "form": form,
        "modo": "nuevo",
        "producto": None
    })


def inventory_edit(request, pk):
    producto = get_object_or_404(Inventory, pk=pk)
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = InventoryForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            if next_url:
                return redirect(next_url)
            return redirect("inventory_list")
    else:
        form = InventoryForm(instance=producto)

    return render(request, "core/inventory_edit.html", {
        "form": form,
        "producto": producto,
        "next": next_url,
    })


def inventory_delete(request, pk):
    producto = get_object_or_404(Inventory, pk=pk)

    # Si querés confirmación, podés hacer un template confirm.
    # Para hacerlo simple: borra directo por GET (funciona)
    producto.delete()
    return redirect("inventory_list")
    


def agenda_calendar_month(request):
    hoy = date.today()
    year = hoy.year
    month = hoy.month

    primer_dia = date(year, month, 1)
    ultimo_dia = date(year, month, monthrange(year, month)[1])

    turnos = (
        Appointment.objects
        .filter(fecha__range=(primer_dia, ultimo_dia))
        .select_related()  # 🔒 SIN nombre → no rompe nada
        .order_by("fecha", "hora")
    )

    context = {
        "year": year,
        "month": month,
        "turnos": turnos,
    }

    return render(request, "core/agenda_month.html", context)



def agenda_calendario(request):
    today = date.today()

    month = int(request.GET.get("month", today.month))
    year = int(request.GET.get("year", today.year))

    # ============================
    # 🔍 BUSCADOR DE CITAS
    # ============================
    q = request.GET.get("q", "").strip()
    resultados = None

    if q:
        resultados = Appointment.objects.filter(
            Q(paciente__nombre__icontains=q) |
            Q(paciente__apellido__icontains=q) |
            Q(paciente__ci__icontains=q) |
            Q(motivo__icontains=q)
        ).select_related("paciente").order_by("fecha", "hora")

    # ============================
    # 📅 GENERAR CALENDARIO
    # ============================
    cal = calendar.Calendar(firstweekday=0)
    semanas = cal.monthdayscalendar(year, month)

    # Cargar citas del mes
    citas = Appointment.objects.filter(
        fecha__year=year,
        fecha__month=month
    ).select_related("paciente")

    citas_por_dia = {}
    for c in citas:
        d = c.fecha.day
        citas_por_dia.setdefault(d, []).append(c)

    # Meses en español
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "setiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }

    # Navegación entre meses
    prev_month = month - 1 if month > 1 else 12
    prev_year  = year - 1 if month == 1 else year

    next_month = month + 1 if month < 12 else 1
    next_year  = year + 1 if month == 12 else year

    return render(
        request,
        "core/agenda_mensual_calendario.html",
        {
            "month": month,
            "year": year,
            "semanas": semanas,
            "citas_por_dia": citas_por_dia,
            "nombre_mes": meses[month],

            # Navegación
            "prev_month": prev_month,
            "prev_year": prev_year,
            "next_month": next_month,
            "next_year": next_year,

            # 🔥 VARIABLES DEL BUSCADOR (esto antes NO estaba)
            "q": q,
            "resultados": resultados,
        }
    )


def agenda_horarios_dia(request, year, month, day):
    fecha = date(year, month, day)

    # Horario del consultorio: 09:00 a 19:00 cada 30 minutos
    inicio = datetime.combine(fecha, time(9, 0))
    fin = datetime.combine(fecha, time(19, 0))

    horarios = []
    actual = inicio
    while actual < fin:
        horarios.append(actual.time())
        actual += timedelta(minutes=30)

    ocupados = Appointment.objects.filter(
        fecha=fecha
    ).values_list("hora", flat=True)

    return render(request, "core/agenda_horarios_dia.html", {
        "fecha": fecha,
        "horarios": horarios,
        "ocupados": ocupados,
    })


def agenda_hoy(request):
    hoy = date.today()
    return redirect(
        "agenda_day",
        day=hoy.day,
        month=hoy.month,
        year=hoy.year
    )

from django.http import HttpResponse
from core.utils.wati import enviar_whatsapp

def test_whatsapp(request):
    numero = "59892706293"   # sin signo +
    mensaje = "Hola! Este es un mensaje de prueba desde SonrisAR Pro ✔️"
    
    status, result = enviar_whatsapp(numero, mensaje)
    return HttpResponse(f"STATUS: {status}<br>RESPUESTA: {result}")


from django.db.models import Count
from datetime import date

def dashboard_asistencia(request):
    today = date.today()
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

    # 🔥 RANKING PACIENTES QUE MÁS FALTAN
    ranking = (
        citas.filter(estado="no_asistio")
        .values("paciente__apellido", "paciente__nombre")
        .annotate(faltas=Count("id"))
        .order_by("-faltas")
    )

    context = {
        "month": month,
        "year": year,
        "total": total,
        "asistieron": asistieron,
        "no_asistieron": no_asistieron,
        "confirmados": confirmados,
        "cancelados": cancelados,
        "pendientes": pendientes,
        "porcentaje": porcentaje,
        "ranking": ranking,
    }

    return render(request, "core/dashboard_asistencia.html", context)


from django.http import HttpResponse

def service_worker(request):
    js = """
const CACHE_NAME = "sonrisar-cache-v2";

const urlsToCache = [
  "/",
  "/static/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
"""
    return HttpResponse(js, content_type="application/javascript")


# ===================================
# CALENDARIO PRO SONRISAR
# ===================================
def color_cita_por_motivo(motivo):
    if not motivo:
        return "#6b7280"  # gris

    m = motivo.lower()

    if "consulta" in m or "diagnóstico" in m or "diagnostico" in m:
        return "#6b7280"  # gris

    if "limpieza" in m:
        return "#1f9bd1"  # celeste

    if "resina" in m:
        return "#ffd400"  # amarillo

    if "ajuste" in m and "ortodoncia" in m:
        return "#1aa7a1"  # turquesa

    if "segunda colocación" in m or "segunda colocacion" in m:
        return "#2e7d32"  # verde fuerte

    if "colocación nueva" in m or "colocacion nueva" in m:
        return "#2563eb"  # azul

    if "retiro" in m and "bracket" in m:
        return "#795548"  # marrón

    if "ajuste" in m and "limpieza" in m:
        return "#00bfa5"  # verde agua

    if "endodoncia" in m:
        return "#8e24aa"  # lila

    if "extracción" in m or "extraccion" in m:
        return "#d32f2f"  # rojo

    if "prótesis" in m or "protesis" in m:
        return "#e91e63"  # rosado

    if "urgencia" in m:
        return "#ff8c00"  # naranja

    if "despegados" in m:
        return "#ff6b6b"  # rojo suave

    if "blanqueamiento" in m:
        return "#c8b6e2"  # lila pastel medio

    return "#26ABA5"


def agenda_pro(request):
    import calendar

    hoy = date.today()

    fecha_str = request.GET.get("fecha")
    q = request.GET.get("q", "").strip()

    if fecha_str:
        try:
            fecha_base = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha_base = hoy
    else:
        fecha_base = hoy

    inicio_semana = fecha_base - timedelta(days=fecha_base.weekday())
    fin_semana = inicio_semana + timedelta(days=5)

    dias = [inicio_semana + timedelta(days=i) for i in range(6)]
    horarios = generar_horarios()

    bloqueos_semana = DayBlock.objects.filter(fecha__range=[inicio_semana, fin_semana])

    bloqueos_por_dia = {bloqueo.fecha: bloqueo for bloqueo in bloqueos_semana}
    bloqueos_por_dia_str = {bloqueo.fecha.strftime("%Y-%m-%d"): bloqueo for bloqueo in bloqueos_semana}

    citas_semana = (
        Appointment.objects
        .filter(fecha__range=[inicio_semana, fin_semana])
        .select_related("paciente")
        .prefetch_related("procedimientos")
        .order_by("fecha", "hora")
    )

    if q:
        filtro = Q()
        for palabra in q.split():
            filtro &= (
                Q(paciente__nombre__icontains=palabra) |
                Q(paciente__apellido__icontains=palabra) |
                Q(paciente__ci__icontains=palabra)
            )
        citas_semana = citas_semana.filter(filtro)

    citas_por_dia = {dia: {} for dia in dias}

    for cita in citas_semana:
        bloque = floor_to_30_minutes(cita.hora)
        citas_por_dia.setdefault(cita.fecha, {}).setdefault(bloque, []).append(cita)

    for dia in citas_por_dia:
        for bloque in citas_por_dia[dia]:
            citas_por_dia[dia][bloque].sort(key=lambda c: c.hora)

    filas = []

    for hora in horarios:
        celdas = []

        for dia in dias:
            dia_bloqueado = bloqueos_por_dia.get(dia)
            citas_en_bloque = citas_por_dia.get(dia, {}).get(hora, [])

            if dia_bloqueado:
                celdas.append({
                    "ocupado": False,
                    "bloqueado": True,
                    "motivo_bloqueo": dia_bloqueado.motivo or "Día bloqueado",
                    "citas": [],
                    "fecha": dia,
                    "hora": hora,
                })
                continue

            if citas_en_bloque:
                citas_preparadas = []

                for cita in citas_en_bloque:
                    estado_texto = cita.get_estado_display()

                    if estado_texto == "En espera":
                        estado_color = "#c8b6e2"
                    elif cita.estado == "pendiente":
                        estado_color = "#ffc107"
                    elif cita.estado == "confirmado":
                        estado_color = "#0d6efd"
                    elif cita.estado == "asistio":
                        estado_color = "#198754"
                    elif cita.estado == "no_asistio":
                        estado_color = "#dc3545"
                    elif cita.estado == "cancelado":
                        estado_color = "#6c757d"
                    else:
                        estado_color = "#6c757d"

                    citas_preparadas.append({
                        "id": cita.id,
                        "paciente": cita.paciente,
                        "motivo": cita.motivo,
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
                    "motivo_bloqueo": "",
                    "citas": citas_preparadas,
                    "fecha": dia,
                    "hora": hora,
                })
            else:
                celdas.append({
                    "ocupado": False,
                    "bloqueado": False,
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
        }
    )



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

    citas = list(
        Appointment.objects
        .exclude(estado="cancelado")
        .filter(monto_total__gt=0)
        .select_related("paciente")
        .order_by("fecha", "hora")[:300]
    )

    pacientes_por_id = {}
    primera_cita_pendiente_por_id = {}
    ultima_fecha_por_id = {}

    for cita in citas:
        paciente = cita.paciente
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
    presupuestos_confirmados = list(
        Budget.objects
        .filter(estado="confirmado")
        .select_related("paciente")
    )

    deuda_presupuestos_por_id = {}

    for presupuesto in presupuestos_confirmados:
        paciente = presupuesto.paciente
        patient_id = paciente.id
        nombre = f"{paciente.apellido}, {paciente.nombre}".lower()

        if query and query not in nombre:
            continue

        try:
            saldo = presupuesto.saldo_pendiente or Decimal("0")
        except Exception:
            saldo = Decimal("0")

        if saldo <= 0:
            continue

        pacientes_por_id[patient_id] = paciente
        deuda_presupuestos_por_id[patient_id] = deuda_presupuestos_por_id.get(patient_id, Decimal("0")) + saldo

        if patient_id not in ultima_fecha_por_id:
            ultima_fecha_por_id[patient_id] = presupuesto.fecha

    patient_ids = list(pacientes_por_id.keys())
    resumenes_cobros = obtener_resumen_cobros_pacientes_bulk(patient_ids)

    deudores = []

    for patient_id, paciente in pacientes_por_id.items():
        total_cobrable = obtener_total_cobrable_paciente_desde_pro(paciente)
        total_pagado = _decimal_seguro(
            resumenes_cobros.get(patient_id, {}).get("total_pagado", 0)
        )

        deuda_citas = total_cobrable - total_pagado
        if deuda_citas < 0:
            deuda_citas = Decimal("0")

        deuda_presupuestos = deuda_presupuestos_por_id.get(patient_id, Decimal("0"))
        deuda_total = deuda_citas + deuda_presupuestos

        if deuda_total <= 0:
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

    total_general = sum(
        (d["deuda_total"] for d in deudores),
        Decimal("0")
    )

    return render(
        request,
        "core/deudores_general.html",
        {
            "deudores": deudores,
            "total_general": total_general,
            "query": query,
        }
    )

def patient_finances(request, id):
    """
    Ficha financiera del paciente.

    Pantalla liviana:
    - Usa datos locales de Sonrisar Pro para citas/presupuestos.
    - Consulta Sonrisar Cobros una sola vez para total pagado por patient_id.
    - No llama a Cobros por cada cita ni por cada pago.
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

    resumen_cobros = obtener_resumen_cobros_paciente(paciente)
    total_pagado_cobros = _decimal_seguro(resumen_cobros.get("total_pagado", 0))

    saldo_actual = total_citas - total_pagado_cobros
    if saldo_actual < 0:
        saldo_actual = Decimal("0")

    presupuestos = list(
        Budget.objects
        .filter(paciente=paciente)
        .prefetch_related("items", "pagos")
        .order_by("-fecha", "-id")
    )

    estados_aceptados = {"confirmado", "en_proceso", "entregado"}

    total_presupuestos_aceptados = Decimal("0")
    total_pagado_presupuestos = Decimal("0")
    saldo_presupuestos = Decimal("0")
    presupuestos_data = []
    movimientos_presupuesto = []

    for presupuesto in presupuestos:
        total_presupuesto = _decimal_seguro(presupuesto.total)
        total_pagado = _decimal_seguro(presupuesto.total_pagado)
        saldo = total_presupuesto - total_pagado

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
            "total_pagado": total_pagado,
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
            })

    movimientos_presupuesto.sort(
        key=lambda m: (m["fecha"], m["presupuesto_id"]),
        reverse=True,
    )

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
            "saldo_actual": saldo_actual,
            "cobros_error": resumen_cobros.get("error"),
            "cobros_ok": resumen_cobros.get("ok", False),
            "cantidad_pagos_cobros": resumen_cobros.get("cantidad_pagos", 0),
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
