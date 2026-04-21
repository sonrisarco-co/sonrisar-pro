from django.shortcuts import render, redirect, get_object_or_404
from datetime import date, time, timedelta, datetime

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

    if request.method == "POST":
        form = AppointmentForm(request.POST)

        if form.is_valid():
            form.save()
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
        return JsonResponse({"success": False, "error": "Hora no recibida."}, status=400)

    if not fecha_str:
        return JsonResponse({"success": False, "error": "Fecha no recibida."}, status=400)

    if hora_str in {"14:00", "14:30"}:
        return JsonResponse({"success": False, "error": "Ese horario está bloqueado."}, status=400)

    try:
        nueva_hora = datetime.strptime(hora_str, "%H:%M").time()
    except ValueError:
        return JsonResponse({"success": False, "error": "Formato de hora inválido."}, status=400)

    try:
        nueva_fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"success": False, "error": "Formato de fecha inválido."}, status=400)

    cita.hora = nueva_hora
    cita.fecha = nueva_fecha
    cita.save(update_fields=["hora", "fecha"])

    return JsonResponse({"success": True})

# =========================
# 📋 LISTA DE HISTORIAS
# =========================

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

  
# =========================
# ➕ NUEVA HISTORIA
# =========================

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
            return redirect("clinical_record_detail", registro_id=registro.id)
    else:
        form = ClinicalRecordForm()

        if cita:
            procedimientos = [p.nombre for p in cita.procedimientos.all()]
            procedimientos_txt = ", ".join(procedimientos)

            form.initial["motivo"] = cita.motivo

            fecha_hoy = timezone.localdate().strftime("%d/%m/%Y")

            texto_tratamiento = f"{fecha_hoy} – Motivo de cita: {cita.motivo}"
            if procedimientos_txt:
                texto_tratamiento += f". Procedimientos: {procedimientos_txt}"
            texto_tratamiento += "."

            form.initial["tratamiento"] = texto_tratamiento

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
        },
    )
    


# =========================
# 👁️ DETALLE
# =========================
def clinical_record_detail(request, registro_id):
    registro = get_object_or_404(ClinicalRecord, id=registro_id)

    paciente = registro.paciente

    historias = ClinicalRecord.objects.filter(
        paciente=paciente
    ).order_by("-fecha")

    rayos = paciente.rayos_x.all().order_by("-fecha")

    pagos_cobros, pagos_error = obtener_pagos_cobros_paciente(request, paciente)

    return render(
        request,
        "core/clinical_record_detail.html",
        {
            "registro": registro,
            "paciente": paciente,
            "historias": historias,
            "rayos": rayos,
            "pagos_cobros": pagos_cobros,
            "pagos_error": pagos_error,
        }
    )
    


# =========================
# ✏️ EDITAR
# =========================

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
            return redirect("clinical_record_detail", registro_id=registro.id)
    else:
        form = ClinicalRecordForm(instance=registro)

        hoy = timezone.localdate().strftime("%d/%m/%Y")
        texto_actual = (registro.tratamiento or "").strip()

        if cita:
            procedimientos = [p.nombre for p in cita.procedimientos.all()]
            procedimientos_txt = ", ".join(procedimientos)

            nuevo_bloque = f"{hoy} – Motivo de cita: {cita.motivo}"
            if procedimientos_txt:
                nuevo_bloque += f". Procedimientos: {procedimientos_txt}"
            nuevo_bloque += "."

            if texto_actual:
                form.initial["tratamiento"] = f"{texto_actual}\n\n{nuevo_bloque}"
            else:
                form.initial["tratamiento"] = nuevo_bloque

            if not registro.motivo:
                form.initial["motivo"] = cita.motivo

        else:
            if texto_actual:
                form.initial["tratamiento"] = f"{texto_actual}\n{hoy} "
            else:
                form.initial["tratamiento"] = f"{hoy} "

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



# =========================
# 🗑️ BORRAR
# =========================

def clinical_record_delete(request, registro_id):
    registro = get_object_or_404(ClinicalRecord, id=registro_id)
    paciente_id = registro.paciente.id

    registro.delete()

    return redirect("clinical_records_list", patient_id=paciente_id)



from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from .models import Patient

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

    # 🔹 ORDEN ALFABÉTICO SIEMPRE
    pacientes_qs = pacientes_qs.order_by("apellido", "nombre")

    # ✅ PAGINACIÓN (ACÁ ES DONDE VA)
    paginator = Paginator(pacientes_qs, 20)  # 20 por página
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


def obtener_deuda_total_paciente_desde_pro(paciente, fecha_hasta=None):
    """
    Calcula la deuda acumulada del paciente tomando las citas registradas
    en Sonrisar Pro y restando lo pagado en Sonrisar Cobros por cada cita.

    Reglas:
    - Si hay pago en Cobros, la deuda real es monto_total - total_pagado.
    - Si NO hay pago en Cobros y la cita está marcada como pagada, la deuda es 0.
    - Si NO hay pago en Cobros y la cita NO está marcada como pagada, la deuda es monto_total.
    - No cuenta citas canceladas.
    """
    citas_qs = (
        Appointment.objects
        .filter(paciente=paciente)
        .exclude(estado="cancelado")
        .order_by("fecha", "hora")
    )

    if fecha_hasta:
        citas_qs = citas_qs.filter(fecha__lte=fecha_hasta)

    deuda_total = Decimal("0")

    for cita in citas_qs:
        info_pago = obtener_pago_cobros_cita(cita.id)

        try:
            total_pagado_decimal = Decimal(str(info_pago["total_pagado"]))
        except (InvalidOperation, TypeError, ValueError):
            total_pagado_decimal = Decimal("0")

        monto_total = cita.monto_total or Decimal("0")
        tiene_pago_cobros = bool(info_pago.get("tiene_pago"))

        if tiene_pago_cobros:
            debe = monto_total - total_pagado_decimal
            if debe < 0:
                debe = Decimal("0")
        elif cita.pagado:
            debe = Decimal("0")
        else:
            debe = monto_total

        deuda_total += debe

    return deuda_total

def agenda_day(request, day, month, year):
    fecha = date(year, month, day)

    citas = (
        Appointment.objects.filter(fecha=fecha)
        .select_related("paciente")
        .prefetch_related("procedimientos")
        .order_by("hora")
    )

    HORARIOS_BLOQUEADOS = {"14:00", "14:30"}

    citas_por_bloque = agrupar_citas_por_bloque(citas)

    deudas_totales_cache = {}

    horarios = []
    for h in generar_horarios():

        if h.strftime("%H:%M") in HORARIOS_BLOQUEADOS:
            horarios.append({
                "hora": h,
                "bloqueado": True,
                "motivo": "Descanso",
            })
            continue

        citas_en_bloque = citas_por_bloque.get(h, [])

        citas_exactas = [c for c in citas_en_bloque if c.hora == h]
        citas_extra = [c for c in citas_en_bloque if c.hora != h]

        citas_exactas_data = []

        for cita in citas_exactas:
            info_pago = obtener_pago_cobros_cita(cita.id)

            try:
                total_pagado_decimal = Decimal(str(info_pago["total_pagado"]))
            except (InvalidOperation, TypeError, ValueError):
                total_pagado_decimal = Decimal("0")

            monto_total = cita.monto_total or Decimal("0")
            tiene_pago_cobros = bool(info_pago.get("tiene_pago"))

            if tiene_pago_cobros:
                debe = monto_total - total_pagado_decimal
                if debe < 0:
                    debe = Decimal("0")
            elif cita.pagado:
                debe = Decimal("0")
            else:
                debe = monto_total

            patient_id = cita.paciente.id

            if patient_id not in deudas_totales_cache:
                deudas_totales_cache[patient_id] = obtener_deuda_total_paciente_desde_pro(
                    cita.paciente,
                    fecha_hasta=fecha
                )

            citas_exactas_data.append({
                "id": cita.id,
                "patient_id": patient_id,
                "hora_real": cita.hora,
                "paciente": f"{cita.paciente.apellido}, {cita.paciente.nombre}",
                "motivo": cita.motivo,
                "motivo_slug": slugify(cita.motivo or ""),
                "procedimientos": [p.nombre for p in cita.procedimientos.all()],
                "estado": cita.get_estado_display(),
                "estado_slug": cita.estado,
                "pagado": cita.pagado,
                "tiene_pago_cobros": info_pago["tiene_pago"],
                "total_pagado": info_pago["total_pagado"],
                "tipo_pago": info_pago["tipo_pago"],
                "monto_total": monto_total,
                "debe": debe,
                "deuda_total_paciente": deudas_totales_cache[patient_id],
            })

        citas_extra_data = []

        for cita in citas_extra:
            info_pago = obtener_pago_cobros_cita(cita.id)

            try:
                total_pagado_decimal = Decimal(str(info_pago["total_pagado"]))
            except (InvalidOperation, TypeError, ValueError):
                total_pagado_decimal = Decimal("0")

            monto_total = cita.monto_total or Decimal("0")
            tiene_pago_cobros = bool(info_pago.get("tiene_pago"))

            if tiene_pago_cobros:
                debe = monto_total - total_pagado_decimal
                if debe < 0:
                    debe = Decimal("0")
            elif cita.pagado:
                debe = Decimal("0")
            else:
                debe = monto_total

            patient_id = cita.paciente.id

            if patient_id not in deudas_totales_cache:
                deudas_totales_cache[patient_id] = obtener_deuda_total_paciente_desde_pro(
                    cita.paciente,
                    fecha_hasta=fecha
                )

            citas_extra_data.append({
                "id": cita.id,
                "patient_id": patient_id,
                "hora_real": cita.hora,
                "paciente": f"{cita.paciente.apellido}, {cita.paciente.nombre}",
                "motivo": cita.motivo,
                "motivo_slug": slugify(cita.motivo or ""),
                "procedimientos": [p.nombre for p in cita.procedimientos.all()],
                "estado": cita.get_estado_display(),
                "estado_slug": cita.estado,
                "pagado": cita.pagado,
                "tiene_pago_cobros": info_pago["tiene_pago"],
                "total_pagado": info_pago["total_pagado"],
                "tipo_pago": info_pago["tipo_pago"],
                "monto_total": monto_total,
                "debe": debe,
                "deuda_total_paciente": deudas_totales_cache[patient_id],
            })

        horarios.append({
            "hora": h,
            "ocupado_exacto": len(citas_exactas) > 0,
            "citas_exactas": citas_exactas_data,
            "citas_extra": citas_extra_data,
        })

    deudores = []

    for h in horarios:
        if h.get("bloqueado"):
            continue

        for cita in h.get("citas_exactas", []) + h.get("citas_extra", []):
            try:
                debe = Decimal(str(cita.get("debe", 0)))
            except (InvalidOperation, TypeError, ValueError):
                debe = Decimal("0")

            if debe > 0:
                deudores.append(cita)

    total_deuda_dia = sum(
        (Decimal(str(d.get("debe", 0))) for d in deudores),
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
        "https://sonrisar-cobros.onrender.com"
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

    cita.pagado = True
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
        "https://sonrisar-cobros.onrender.com"
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
        "https://sonrisar-cobros.onrender.com"
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
        

def obtener_pago_cobros_cita(appointment_id):
    cobros_base_url = getattr(
        settings,
        "SONRISAR_COBROS_BASE_URL",
        "https://sonrisar-cobros.onrender.com"
    ).rstrip("/")

    cobros_api_path = getattr(
        settings,
        "SONRISAR_COBROS_API_CITA_PATH",
        "/pagos/api/por-cita/"
    )

    api_url = f"{cobros_base_url}{cobros_api_path}?{urlencode({'appointment_id': appointment_id})}"

    try:
        with urlopen(api_url, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))

        total_pagado = Decimal(str(data.get("total_pagado", 0)))

        if data.get("ok"):
            return {
                "tiene_pago": total_pagado > 0,
                "total_pagado": str(total_pagado),
                "tipo_pago": data.get("tipo_pago", "pagado"),
                "pagos": data.get("pagos", []),
                "error": None,
            }

        return {
            "tiene_pago": False,
            "total_pagado": "0",
            "tipo_pago": "pagado",
            "pagos": [],
            "error": data.get("error", "No se pudo obtener el pago."),
        }

    except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        return {
            "tiene_pago": False,
            "total_pagado": "0",
            "tipo_pago": "pagado",
            "pagos": [],
            "error": "No fue posible conectar con Sonrisar Cobros.",
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
    # Obtener mes y año desde GET (si están)
    hoy = date.today()
    year = int(request.GET.get("year", hoy.year))
    month = int(request.GET.get("month", hoy.month))

    # -------------------------------
    # 🔍 BUSCADOR
    # -------------------------------
    q = request.GET.get("q", "").strip()
    resultados = None

    if q:
        resultados = Appointment.objects.filter(
            Q(paciente__nombre__icontains=q) |
            Q(paciente__apellido__icontains=q) |
            Q(paciente__ci__icontains=q) |
            Q(motivo__icontains=q)
        ).select_related("paciente").order_by("fecha", "hora")

    # -------------------------------
    # 📅 CALENDARIO
    # -------------------------------
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

    # ✅ NUEVO: slots (ocupado/libre) para TODOS los días del mes
    horarios_base = generar_horarios()  # 09:00 -> 19:30 c/30min
    slots_por_dia = {}

    # 🔴 HORARIOS BLOQUEADOS FIJOS
    HORARIOS_BLOQUEADOS = {"14:00", "14:30"}

    # Días que realmente aparecen en la grilla
    dias_en_grilla = set()
    for semana in semanas:
        for d in semana:
            if d != 0:
                dias_en_grilla.add(d)

    # Construimos slots para cada día del mes visible
    for d in dias_en_grilla:
        citas_del_dia = citas_por_dia.get(d, [])
        citas_por_bloque = agrupar_citas_por_bloque(citas_del_dia)

        slots = []
        for h in horarios_base:
            hora_txt = h.strftime("%H:%M")

            if hora_txt in HORARIOS_BLOQUEADOS:
                slots.append({
                    "hora": h,
                    "bloqueado": True,
                    "motivo": "Descanso",
                })
                continue

            citas_en_bloque = citas_por_bloque.get(h, [])

            if citas_en_bloque:
                slots.append({
                    "hora": h,
                    "ocupado": True,
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
                    ]

                })
            else:
                slots.append({
                    "hora": h,
                    "ocupado": False,
                })

        slots_por_dia[d] = slots

    # ✅ FIX: claves como string para el template
    slots_por_dia_str = {str(k): v for k, v in slots_por_dia.items()}

    # -------------------------------
    # ◀▶ Mes anterior / siguiente
    # -------------------------------
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
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    nombre_mes = MESES[month]

    # -------------------------------
    # CONTEXTO
    # -------------------------------
    context = {
        "hoy": hoy,
        "year": year,
        "month": month,
        "nombre_mes": nombre_mes,
        "semanas": semanas,

        "citas_por_dia": citas_por_dia,

        "slots_por_dia": slots_por_dia,
        "slots_por_dia_str": slots_por_dia_str,

        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,

        "q": q,
        "resultados": resultados,
    }

    return render(
        request,
        "core/agenda_mensual_calendario.html",
        context
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

    if "endodoncia" in m:
        return "#8e24aa"  # lila

    if "extracción" in m or "extraccion" in m:
        return "#d32f2f"  # rojo

    if "prótesis" in m or "protesis" in m:
        return "#e91e63"  # rosado

    if "urgencia" in m:
        return "#ff8c00"  # naranja

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
    fin_semana = inicio_semana + timedelta(days=5)  # lunes a sábado

    dias = [inicio_semana + timedelta(days=i) for i in range(6)]
    horarios = generar_horarios()

    citas_semana = (
        Appointment.objects
        .filter(fecha__range=[inicio_semana, fin_semana])
        .select_related("paciente")
        .prefetch_related("procedimientos")
        .order_by("fecha", "hora")
    )

    if q:
        palabras = q.split()

        filtro = Q()
        for palabra in palabras:
            filtro &= (
                Q(paciente__nombre__icontains=palabra) |
                Q(paciente__apellido__icontains=palabra) |
                Q(paciente__ci__icontains=palabra)
            )

        citas_semana = citas_semana.filter(filtro)

    citas_por_dia = {}
    for dia in dias:
        citas_dia = [c for c in citas_semana if c.fecha == dia]
        citas_por_dia[dia] = agrupar_citas_por_bloque(citas_dia)

    filas = []
    for hora in horarios:
        celdas = []

        for dia in dias:
            citas_en_bloque = citas_por_dia.get(dia, {}).get(hora, [])

            if citas_en_bloque:
                citas_preparadas = []
                for cita in citas_en_bloque:
                    citas_preparadas.append({
                        "id": cita.id,
                        "paciente": cita.paciente,
                        "motivo": cita.motivo,
                        "procedimientos": [p.nombre for p in cita.procedimientos.all()],
                        "hora": cita.hora,
                        "color": color_cita_por_motivo(cita.motivo),
                    })

                celdas.append({
                    "ocupado": True,
                    "citas": citas_preparadas,
                    "fecha": dia,
                    "hora": hora,
                })
            else:
                celdas.append({
                    "ocupado": False,
                    "citas": [],
                    "fecha": dia,
                    "hora": hora,
                })

        filas.append({
            "hora": hora,
            "celdas": celdas,
        })

    resultados_paciente = []
    if q:
        palabras = q.split()

        filtro = Q()
        for palabra in palabras:
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
            .order_by("-fecha", "-hora")
        )

    semana_anterior = inicio_semana - timedelta(days=7)
    semana_siguiente = inicio_semana + timedelta(days=7)

    # =========================
    # MINI ALMANAQUE (1 mes)
    # =========================
    mini_fecha_str = request.GET.get("mini_fecha")
    if mini_fecha_str:
        try:
            mini_fecha_base = datetime.strptime(mini_fecha_str, "%Y-%m-%d").date()
        except ValueError:
            mini_fecha_base = fecha_base
    else:
        mini_fecha_base = fecha_base

    def construir_mes(anio, mes):
        cal = calendar.Calendar(firstweekday=0)  # lunes
        semanas_crudas = cal.monthdayscalendar(anio, mes)

        citas_mes = Appointment.objects.filter(
            fecha__year=anio,
            fecha__month=mes
        ).values_list("fecha", flat=True)

        dias_con_citas = {f.day for f in citas_mes}

        semanas = []
        for semana in semanas_crudas:
            fila = []
            for d in semana:
                if d == 0:
                    fila.append(None)
                else:
                    fecha_real = date(anio, mes, d)
                    fila.append({
                        "day": d,
                        "date": fecha_real,
                        "is_today": fecha_real == hoy,
                        "is_selected": fecha_real == fecha_base,
                        "has_appointments": d in dias_con_citas,
                    })
            semanas.append(fila)

        meses_es = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        return {
            "year": anio,
            "month": mes,
            "label": f"{meses_es[mes]} {anio}",
            "weeks": semanas,
        }

    mini_mes_actual_num = mini_fecha_base.month
    mini_anio_actual = mini_fecha_base.year

    if mini_mes_actual_num == 1:
        mini_prev_month = 12
        mini_prev_year = mini_anio_actual - 1
    else:
        mini_prev_month = mini_mes_actual_num - 1
        mini_prev_year = mini_anio_actual

    if mini_mes_actual_num == 12:
        mini_next_month = 1
        mini_next_year = mini_anio_actual + 1
    else:
        mini_next_month = mini_mes_actual_num + 1
        mini_next_year = mini_anio_actual

    mini_mes_actual = construir_mes(mini_anio_actual, mini_mes_actual_num)

    mini_prev_date = date(mini_prev_year, mini_prev_month, 1)
    mini_next_date = date(mini_next_year, mini_next_month, 1)

    contexto = {
        "dias": dias,
        "filas": filas,
        "inicio_semana": inicio_semana,
        "fin_semana": fin_semana,
        "semana_anterior": semana_anterior,
        "semana_siguiente": semana_siguiente,
        "hoy": hoy,
        "q": q,
        "resultados_paciente": resultados_paciente,
        "fecha_base": fecha_base,
        "mini_mes_actual": mini_mes_actual,
        "mini_prev_date": mini_prev_date,
        "mini_next_date": mini_next_date,
        "mini_fecha_base": mini_fecha_base,
    }

    return render(request, "core/agenda_pro.html", contexto)


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
    presupuestos = Budget.objects.filter(paciente=paciente)

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
    query = request.GET.get("q", "").strip().lower()

    citas = (
        Appointment.objects
        .exclude(estado="cancelado")
        .filter(monto_total__gt=0)
        .select_related("paciente")
        .order_by("fecha", "hora")[:300]
    )

    deudores_map = {}
    deuda_presupuestos_cache = {}

    for cita in citas:
        nombre = f"{cita.paciente.apellido}, {cita.paciente.nombre}".lower()

        if query and query not in nombre:
            continue

        info_pago = obtener_pago_cobros_cita(cita.id)

        try:
            total_pagado_decimal = Decimal(str(info_pago["total_pagado"]))
        except (InvalidOperation, TypeError, ValueError):
            total_pagado_decimal = Decimal("0")

        monto_total = cita.monto_total or Decimal("0")
        tiene_pago_cobros = bool(info_pago.get("tiene_pago"))

        # 🔹 cálculo de deuda por cita (tu lógica intacta)
        if tiene_pago_cobros:
            debe_cita = monto_total - total_pagado_decimal
            if debe_cita < 0:
                debe_cita = Decimal("0")
        elif cita.pagado:
            debe_cita = Decimal("0")
        else:
            debe_cita = monto_total

        patient_id = cita.paciente.id

        # 🔹 cache presupuestos
        if patient_id not in deuda_presupuestos_cache:
            presupuestos = Budget.objects.filter(
                paciente=cita.paciente
            ).exclude(estado="cancelado")

            total_presupuestos = Decimal("0")

            for presupuesto in presupuestos:
                try:
                    saldo = presupuesto.saldo_pendiente or Decimal("0")
                except:
                    saldo = Decimal("0")

                if saldo > 0:
                    total_presupuestos += saldo

            deuda_presupuestos_cache[patient_id] = total_presupuestos

        deuda_presupuestos = deuda_presupuestos_cache[patient_id]

        # 🔹 crear deudor
        if patient_id not in deudores_map:
            deudores_map[patient_id] = {
                "patient_id": patient_id,
                "paciente": f"{cita.paciente.apellido}, {cita.paciente.nombre}",
                "deuda_citas": Decimal("0"),
                "deuda_presupuestos": deuda_presupuestos,
                "deuda_total": Decimal("0"),
                "ultima_fecha": cita.fecha,
                "cita_pendiente_id": None,
                "cita_pendiente_fecha": None,
            }

        # 🔹 sumar deuda
        if debe_cita > 0:
            deudores_map[patient_id]["deuda_citas"] += debe_cita

            # ✅ CLAVE: elegir cita pendiente (la más vieja con deuda)
            actual_fecha = deudores_map[patient_id]["cita_pendiente_fecha"]

            if actual_fecha is None or cita.fecha < actual_fecha:
                deudores_map[patient_id]["cita_pendiente_id"] = cita.id
                deudores_map[patient_id]["cita_pendiente_fecha"] = cita.fecha

        # 🔹 actualizar última fecha
        if cita.fecha > deudores_map[patient_id]["ultima_fecha"]:
            deudores_map[patient_id]["ultima_fecha"] = cita.fecha

    deudores = []

    for data in deudores_map.values():
        data["deuda_total"] = data["deuda_citas"] + data["deuda_presupuestos"]

        # limpieza
        data.pop("cita_pendiente_fecha", None)

        if data["deuda_total"] > 0:
            deudores.append(data)

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