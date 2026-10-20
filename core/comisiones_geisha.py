"""Comisiones del 30%: fondos asignados por tratamiento, sin duplicar cobros."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps
from types import SimpleNamespace

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from activity.middleware import manager
from .models import (Appointment, TratamientoGeisha, CobroTratamientoGeisha,
                     LiquidacionGeisha, DetalleLiquidacionGeisha)

CERO = Decimal("0.00")


def responsable(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not manager(request.user):
            raise PermissionDenied("Solo los responsables pueden administrar comisiones.")
        return view(request, *args, **kwargs)
    return wrapped


def fondos(citas):
    # No recurrir al booleano pagado ni a valores locales si Cobros no responde.
    from .views import _obtener_pagos_cobros_citas_bulk
    resultado = {}
    ids = sorted(set(citas))
    for inicio in range(0, len(ids), 100):
        lote = ids[inicio:inicio + 100]
        respuesta = _obtener_pagos_cobros_citas_bulk(lote)
        if respuesta is None:
            raise ValidationError("No se pudo verificar Sonrisar Cobros. No se habilitan pagos hasta recuperar la conexión.")
        for pk in lote:
            try:
                valor = Decimal(respuesta[pk]["total_pagado"])
                if not valor.is_finite():
                    raise ValueError
                resultado[pk] = max(valor, CERO)
            except (KeyError, InvalidOperation, ValueError, TypeError):
                raise ValidationError("Cobros devolvió información incompleta. Volvé a intentar.")
    return resultado


def evaluar(registros):
    asignaciones = list(CobroTratamientoGeisha.objects.filter(
        tratamiento_id__in=[r.pk for r in registros]).select_related("cita"))
    # One treatment per appointment has an unambiguous price and payment source.
    cantidades = dict(TratamientoGeisha.objects.filter(cita_id__in=[r.cita_id for r in registros])
                     .values("cita_id").annotate(total=Count("pk")).values_list("cita_id", "total"))
    con_asignaciones = {a.tratamiento_id for a in asignaciones}
    automaticos = {r.pk for r in registros if cantidades[r.cita_id] == 1
                  and r.pk not in con_asignaciones
                  and not DetalleLiquidacionGeisha.objects.filter(tratamiento=r).exists()}
    citas = {a.cita_id for a in asignaciones} | {r.cita_id for r in registros if r.pk in automaticos}
    totales = dict(CobroTratamientoGeisha.objects.filter(cita_id__in=citas)
                   .values("cita_id").annotate(total=Sum("monto")).values_list("cita_id", "total"))
    error = ""
    try:
        disponibles = fondos(citas)
    except ValidationError as exc:
        disponibles = {}
        error = exc.messages[0]
    por_tratamiento = {}
    for asignacion in asignaciones:
        por_tratamiento.setdefault(asignacion.tratamiento_id, []).append(asignacion)
    for registro in registros:
        registro.automatico = registro.pk in automaticos
        registro.requiere_desglose = cantidades[registro.cita_id] > 1
        registro.importe_automatico = False
        if cantidades[registro.cita_id] == 1 and registro.importe is None:
            registro.importe = registro.cita.monto_total or CERO
            registro.importe_automatico = True
        registro.asignaciones = por_tratamiento.get(registro.pk, [])
        if registro.automatico and registro.importe and registro.importe > 0:
            libre = max(disponibles.get(registro.cita_id, CERO) - totales.get(registro.cita_id, CERO), CERO)
            monto = min(registro.importe, libre)
            if monto:
                registro.asignaciones = [SimpleNamespace(cita_id=registro.cita_id, cita=registro.cita, monto=monto)]
        registro.cobrado = sum((a.monto for a in registro.asignaciones), CERO)
        registro.comision = ((registro.importe or CERO) * Decimal("0.30")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        registro.alerta = "Cobro sin verificar" if registro.automatico and registro.cita_id not in disponibles else ""
        for a in registro.asignaciones:
            if a.cita.paciente_id != registro.cita.paciente_id:
                registro.alerta = "Revisar paciente de la asignación"
            elif a.cita_id not in disponibles:
                registro.alerta = "Cobro sin verificar"
            elif totales.get(a.cita_id, CERO) > disponibles[a.cita_id]:
                registro.alerta = "Revisar cobros: el importe asignado supera lo cobrado actualmente"
        registro.liquidado = DetalleLiquidacionGeisha.objects.filter(tratamiento=registro).exists()
        registro.disponible = bool(not registro.liquidado and not registro.alerta
            and registro.importe and registro.importe > 0 and registro.cobrado == registro.importe
            and registro.estado == "terminado" and registro.cita.estado == "asistio"
            and registro.cita.odontologo.codigo == "geisha")
        if registro.liquidado:
            registro.situacion = "Pagada"
        elif registro.alerta:
            registro.situacion = registro.alerta
        elif not registro.importe:
            registro.situacion = ("Desglosar importe: varios tratamientos en la cita"
                                  if registro.requiere_desglose else "Definir el total en la cita")
        elif registro.cobrado < registro.importe:
            registro.situacion = "Pendiente de cobro completo"
        elif registro.estado != "terminado":
            registro.situacion = "Pendiente de terminar"
        elif registro.disponible:
            registro.situacion = "Disponible para pagar"
        else:
            registro.situacion = "Revisar atención"
    return error


class ImporteForm(forms.Form):
    importe = forms.DecimalField(label="Importe final del tratamiento", max_digits=10, decimal_places=2, min_value=Decimal("0.01"))


class AsignacionForm(forms.Form):
    cita = forms.ModelChoiceField(queryset=Appointment.objects.none(), label="Cita donde se registró el pago en Cobros")
    monto = forms.DecimalField(label="Importe cobrado asignado (0 para quitar)", max_digits=10, decimal_places=2, min_value=0)

    def __init__(self, *args, paciente_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cita"].queryset = Appointment.objects.filter(paciente_id=paciente_id).order_by("-fecha", "-hora")


class LiquidacionForm(forms.Form):
    fecha = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    metodo = forms.ChoiceField(choices=LiquidacionGeisha._meta.get_field("metodo").choices)
    referencia = forms.CharField(required=False, max_length=200, label="Referencia / observaciones")

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha de pago no puede ser futura.")
        return fecha


@responsable
def comisiones(request):
    registros = list(TratamientoGeisha.objects.select_related("cita__paciente", "cita__odontologo")
                     .filter(cita__odontologo__codigo="geisha"))
    error = evaluar(registros)
    estado = request.GET.get("situacion", "")
    q = request.GET.get("q", "").strip().casefold()
    if q:
        registros = [r for r in registros if q in f"{r.cita.paciente} {r.nombre}".casefold()]
    if estado == "disponibles":
        registros = [r for r in registros if r.disponible]
    elif estado == "pagadas":
        registros = [r for r in registros if r.liquidado]
    elif estado == "pendientes":
        registros = [r for r in registros if not r.liquidado and not r.disponible]
    return render(request, "core/comisiones_geisha.html", {
        "registros": registros, "error_cobros": error, "q": request.GET.get("q", ""),
        "situacion": estado, "form": LiquidacionForm(),
        "total_disponible": sum((r.comision for r in registros if r.disponible), CERO),
        "liquidaciones": LiquidacionGeisha.objects.annotate(total=Sum("detalles__comision")),
    })


@responsable
@transaction.atomic
def detalle(request, id):
    registro = get_object_or_404(TratamientoGeisha.objects.select_for_update().select_related(
        "cita__paciente", "cita__odontologo"), pk=id)
    pagado = DetalleLiquidacionGeisha.objects.filter(tratamiento=registro).exists()
    error = evaluar([registro])
    importe_form = ImporteForm(initial={"importe": registro.importe})
    asignacion_form = AsignacionForm(paciente_id=registro.cita.paciente_id, initial={"cita": registro.cita_id})
    if request.method == "POST":
        if pagado:
            messages.error(request, "La comisión ya fue pagada. Sus importes y asignaciones están bloqueados.")
            return redirect("comision_geisha_detalle", id=id)
        try:
            if request.POST.get("accion") == "importe":
                importe_form = ImporteForm(request.POST)
                if importe_form.is_valid():
                    importe = importe_form.cleaned_data["importe"]
                    asignado = registro.cobros_asignados.aggregate(total=Sum("monto"))["total"] or CERO
                    if importe < asignado:
                        raise ValidationError("Quitá primero las asignaciones que superan el nuevo importe.")
                    registro.importe = importe
                    registro.save(update_fields=["importe"])
                    messages.success(request, "Importe actualizado.")
                    return redirect("comision_geisha_detalle", id=id)
            elif request.POST.get("accion") == "asignar":
                asignacion_form = AsignacionForm(request.POST, paciente_id=registro.cita.paciente_id)
                if asignacion_form.is_valid():
                    cita_id = asignacion_form.cleaned_data["cita"].pk
                    cita = Appointment.objects.select_for_update().get(pk=cita_id)
                    monto = asignacion_form.cleaned_data["monto"]
                    if cita.paciente_id != registro.cita.paciente_id:
                        raise ValidationError("El pago debe corresponder al mismo paciente.")
                    otros = CobroTratamientoGeisha.objects.filter(cita=cita).exclude(tratamiento=registro).aggregate(total=Sum("monto"))["total"] or CERO
                    en_tratamiento = registro.cobros_asignados.exclude(cita=cita).aggregate(total=Sum("monto"))["total"] or CERO
                    if monto and (not registro.importe or en_tratamiento + monto > registro.importe):
                        raise ValidationError("Definí el importe final. Lo asignado no puede superar ese importe.")
                    if monto and otros + monto > fondos([cita.pk])[cita.pk]:
                        raise ValidationError("No hay suficiente dinero cobrado disponible en esa cita. Revisá los pagos y las asignaciones a otros tratamientos.")
                    if monto:
                        CobroTratamientoGeisha.objects.update_or_create(tratamiento=registro, cita=cita, defaults={"monto": monto})
                    else:
                        registro.cobros_asignados.filter(cita=cita).delete()
                    messages.success(request, "Asignación actualizada; no se creó un nuevo cobro.")
                    return redirect("comision_geisha_detalle", id=id)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
    return render(request, "core/comision_geisha_detalle.html", {
        "registro": registro, "importe_form": importe_form, "asignacion_form": asignacion_form,
        "error_cobros": error, "pagado": pagado,
    })


@responsable
@require_POST
@transaction.atomic
def liquidar(request):
    form = LiquidacionForm(request.POST)
    try:
        ids = {int(pk) for pk in request.POST.getlist("tratamientos")}
    except (ValueError, TypeError):
        ids = set()
    if not form.is_valid() or not ids:
        messages.error(request, "Seleccioná tratamientos y completá una fecha de pago válida, método y referencia.")
        return redirect("comisiones_geisha")
    registros = list(TratamientoGeisha.objects.select_for_update(of=("self",)).filter(pk__in=ids)
                     .select_related("cita__paciente", "cita__odontologo").order_by("pk"))
    fuentes = set(CobroTratamientoGeisha.objects.filter(tratamiento_id__in=ids).values_list("cita_id", flat=True))
    fuentes.update(r.cita_id for r in registros)
    list(Appointment.objects.select_for_update().filter(pk__in=fuentes).order_by("pk"))
    evaluar(registros)
    if len(registros) != len(ids) or any(not r.disponible for r in registros):
        messages.error(request, "No se registró ningún pago. Todos los tratamientos seleccionados deben estar terminados, cobrados al 100% y sin comisión pagada. Revisá el informe.")
        return redirect("comisiones_geisha")
    liquidacion = LiquidacionGeisha.objects.create(usuario=request.user, **form.cleaned_data)
    for registro in registros:
        # Freeze the price and reserve the verified automatic funds only when paid.
        if registro.importe_automatico:
            registro.save(update_fields=["importe"])
        if registro.automatico:
            CobroTratamientoGeisha.objects.create(tratamiento=registro, cita=registro.cita, monto=registro.importe)
        DetalleLiquidacionGeisha.objects.create(liquidacion=liquidacion, tratamiento=registro,
            paciente=str(registro.cita.paciente), nombre=registro.nombre,
            importe=registro.importe, porcentaje=30, comision=registro.comision)
    messages.success(request, "Pago a Geisha registrado. El comprobante está disponible para imprimir.")
    return redirect("liquidacion_geisha", id=liquidacion.pk)


@responsable
def comprobante(request, id):
    liquidacion = get_object_or_404(LiquidacionGeisha.objects.select_related("usuario"), pk=id)
    return render(request, "core/liquidacion_geisha.html", {"liquidacion": liquidacion,
        "total": liquidacion.detalles.aggregate(total=Sum("comision"))["total"] or CERO})
