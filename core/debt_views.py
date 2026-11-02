"""Lectura y clasificación de saldos; los cobros permanecen en Cobros."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .debt_categories import CATEGORIAS, ETIQUETAS, OPCIONES, CERO, categoria_cita, desglosar
from .models import Appointment, Patient


def pagos_por_sesion(ids):
    """Información completa en lotes cortos; no se inventan ceros si falla la API."""
    from .views import _obtener_pagos_cobros_citas_bulk, _combinar_pagos_citas
    ids = sorted(set(ids))
    if not ids:
        return {}

    def consultar(lote):
        datos = _obtener_pagos_cobros_citas_bulk(lote)
        if settings.DEBUG:
            web = _obtener_pagos_cobros_citas_bulk(
                lote, base_url='https://sonrisar-cobros-1.onrender.com')
            datos = _combinar_pagos_citas(datos, web) if datos is not None or web is not None else None
        if datos is None:
            raise ValueError('No se pudieron verificar los pagos de las sesiones.')
        resultado = {}
        for pk in lote:
            valor = Decimal(str(datos[pk]['total_pagado']))
            if not valor.is_finite():
                raise ValueError('Importe inválido en Cobros.')
            resultado[pk] = valor
        return resultado

    try:
        resultado = {}
        lotes = [ids[i:i + 100] for i in range(0, len(ids), 100)]
        with ThreadPoolExecutor(max_workers=3) as executor:
            for lote in executor.map(consultar, lotes):
                resultado.update(lote)
        return resultado
    except (KeyError, ValueError, InvalidOperation, TypeError):
        return None


def desglosar_deudores(deudores, resumenes, filtro):
    ids = [d['patient_id'] for d in deudores]
    citas_por_paciente = defaultdict(list)
    categorias = {}
    citas = (Appointment.objects.filter(paciente_id__in=ids)
             .prefetch_related('procedimientos').order_by('fecha', 'hora', 'pk'))
    for cita in citas:
        citas_por_paciente[cita.paciente_id].append(cita)
        categorias[cita.pk] = categoria_cita(cita)
    necesitan_pagos = []
    for d in deudores:
        sesiones = citas_por_paciente[d['patient_id']]
        tipos = {categorias[c.pk] for c in sesiones
                 if c.estado != 'cancelado' and (c.monto_total or 0) > 0}
        if len(tipos) > 1 and d['deuda_citas'] > 0:
            necesitan_pagos.extend(c.pk for c in sesiones)
    pagos = pagos_por_sesion(necesitan_pagos) if necesitan_pagos else {}

    totales = {cat: CERO for cat, nombre in CATEGORIAS}
    totales['revisar'] = CERO
    visibles = []
    for d in deudores:
        componentes = desglosar(
            citas_por_paciente[d['patient_id']], categorias, pagos,
            Decimal(str(resumenes[d['patient_id']]['total_pagado'])),
            d['deuda_citas'], d['deuda_total'],
        )
        for componente in componentes:
            totales[componente['categoria']] += componente['saldo']
        seleccionados = [c for c in componentes if filtro == 'todos' or c['categoria'] == filtro]
        if seleccionados or (d['deuda_total'] == 0 and filtro == 'todos'):
            d['componentes'] = seleccionados
            d['deuda_mostrada'] = sum((c['saldo'] for c in seleccionados), CERO)
            visibles.append(d)
    return visibles, totales


@login_required
@require_http_methods(['GET', 'POST'])
def sesiones_deudor(request, patient_id):
    paciente = get_object_or_404(Patient, pk=patient_id)
    volver = request.POST.get('next') or request.GET.get('next') or reverse('deudores_general')
    if not url_has_allowed_host_and_scheme(volver, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        volver = reverse('deudores_general')
    if request.method == 'POST':
        seleccion = request.POST.get('categoria')
        if seleccion not in dict(OPCIONES):
            return HttpResponseBadRequest('Categoría inválida.')
        try:
            cita_id = int(request.POST.get('cita_id', ''))
        except (ValueError, TypeError):
            return HttpResponseBadRequest('Sesión inválida.')
        with transaction.atomic():
            cita = get_object_or_404(Appointment.objects.select_for_update(),
                                     pk=cita_id, paciente=paciente)
            if cita.deuda_categoria != seleccion:
                cita.deuda_categoria = seleccion
                cita.save(update_fields=['deuda_categoria'])
        from urllib.parse import urlencode
        return redirect(reverse('deudor_sesiones', args=[paciente.pk]) + '?' + urlencode({'next': volver}))

    citas = list(Appointment.objects.filter(paciente=paciente)
                 .prefetch_related('procedimientos').order_by('-fecha', '-hora', '-pk'))
    pagos = pagos_por_sesion([c.pk for c in citas])
    filas = [{'cita': c, 'categoria': ETIQUETAS[categoria_cita(c)],
              'pagado': pagos[c.pk] if pagos is not None else None} for c in citas]
    return render(request, 'core/deudor_sesiones.html', {
        'paciente': paciente, 'filas': filas, 'opciones': OPCIONES,
        'volver': volver, 'pagos_error': pagos is None,
    })
