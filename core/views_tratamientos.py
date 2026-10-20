from urllib.parse import urlsplit

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import TratamientoGeisha


class FiltrosTratamientos(forms.Form):
    q = forms.CharField(required=False, label="Paciente o tratamiento",
                        widget=forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Nombre, cédula o tratamiento"}))
    estado = forms.ChoiceField(required=False, choices=[("", "Todos")] + TratamientoGeisha.ESTADOS,
                               widget=forms.Select(attrs={"class": "form-select form-select-sm"}))
    desde = forms.DateField(required=False, label="Atención desde",
                           widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}))
    hasta = forms.DateField(required=False, label="Atención hasta",
                           widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}))

    def clean(self):
        datos = super().clean()
        if datos.get("desde") and datos.get("hasta") and datos["desde"] > datos["hasta"]:
            raise forms.ValidationError("La fecha inicial no puede ser posterior a la final.")
        return datos


def atenciones_geisha():
    return TratamientoGeisha.objects.filter(cita__odontologo__codigo="geisha", cita__estado="asistio")


@login_required
def tratamientos_geisha(request):
    filtros = FiltrosTratamientos(request.GET)
    registros = atenciones_geisha().select_related("cita__paciente", "cita__odontologo")
    if filtros.is_valid():
        datos = filtros.cleaned_data
        for palabra in datos.get("q", "").split():
            registros = registros.filter(Q(cita__paciente__nombre__icontains=palabra) |
                                         Q(cita__paciente__apellido__icontains=palabra) |
                                         Q(cita__paciente__ci__icontains=palabra) | Q(nombre__icontains=palabra))
        if datos.get("desde"):
            registros = registros.filter(cita__fecha__gte=datos["desde"])
        if datos.get("hasta"):
            registros = registros.filter(cita__fecha__lte=datos["hasta"])
        if datos.get("estado"):
            registros = registros.filter(estado=datos["estado"])
    else:
        registros = registros.none()
    resumen = registros.aggregate(total=Count("pk"),
        en_proceso=Count("pk", filter=Q(estado="en_proceso")),
        terminados=Count("pk", filter=Q(estado="terminado")))
    imprimir = request.GET.get("imprimir") == "1"
    pagina = None if imprimir else Paginator(registros, 50).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    params.pop("imprimir", None)
    return render(request, "core/tratamientos_geisha.html", {
        "filtros": filtros, "resumen": resumen, "registros": registros if imprimir else pagina,
        "pagina": pagina, "parametros": params.urlencode(), "imprimir": imprimir,
        "fecha_informe": timezone.localtime(), "estados": TratamientoGeisha.ESTADOS,
        "estado_filtro": dict(TratamientoGeisha.ESTADOS).get(filtros.cleaned_data.get("estado"), "Todos"),
    })


@login_required
@require_POST
@transaction.atomic
def tratamiento_geisha_estado(request, id):
    registro = get_object_or_404(atenciones_geisha().select_for_update(of=("self",)), pk=id)
    estado = request.POST.get("estado")
    if estado not in dict(TratamientoGeisha.ESTADOS):
        messages.error(request, "Seleccioná un estado válido.")
    elif estado != registro.estado and hasattr(registro, "comision_pagada"):
        messages.error(request, "La comisión ya fue pagada; no se puede reabrir el tratamiento.")
    elif estado != registro.estado:
        registro.estado = estado
        registro.fecha_finalizacion = timezone.localdate() if estado == "terminado" else None
        registro.save(update_fields=["estado", "fecha_finalizacion"])
        messages.success(request, f"{registro.nombre}: {registro.get_estado_display()}.")
    destino = urlsplit(request.POST.get("next", ""))
    if not destino.scheme and not destino.netloc and destino.path == reverse("tratamientos_geisha"):
        return redirect(destino.geturl())
    return redirect("tratamientos_geisha")
