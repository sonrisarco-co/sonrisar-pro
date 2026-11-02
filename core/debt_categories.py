"""Desglose de la deuda existente, sin crear cargos ni modificar pagos."""
from collections import defaultdict
from decimal import Decimal
import re
import unicodedata

CERO = Decimal('0')
CATEGORIAS = (
    ('general', 'General'), ('protesis', 'Prótesis'),
    ('endodoncia', 'Endodoncias'), ('corona', 'Coronas'),
)
OPCIONES = [('auto', 'Automático según el tratamiento')] + list(CATEGORIAS)
ETIQUETAS = dict(CATEGORIAS, revisar='Por clasificar')


def categoria_texto(texto):
    texto = ''.join(c for c in unicodedata.normalize('NFKD', texto.lower())
                    if not unicodedata.combining(c))
    if re.search(r'\bendodon\w*', texto):
        return 'endodoncia'
    if re.search(r'\bcorona\w*', texto):
        return 'corona'
    if re.search(r'\bprotes\w*', texto) or 'puente fijo' in texto:
        return 'protesis'
    return 'general'


def categoria_cita(cita):
    seleccion = getattr(cita, 'deuda_categoria', 'auto')
    if seleccion in dict(CATEGORIAS):
        return seleccion
    nombres = [p.nombre for p in cita.procedimientos.all()]
    if not nombres:
        nombres = [cita.motivo or '']
    categorias = {categoria_texto(nombre) for nombre in nombres}
    return next(iter(categorias)) if len(categorias) == 1 else 'revisar'


def revisar(saldo, motivo):
    return [{'categoria': 'revisar', 'nombre': ETIQUETAS['revisar'],
             'saldo': saldo, 'total': None, 'abonado': None, 'nota': motivo}]


def desglosar(citas, categorias, pagos, total_pagado, deuda_citas, deuda_total):
    """Conserva el saldo general. Nunca reparte pagos ambiguos entre tratamientos."""
    if deuda_total <= 0:
        return []
    cargos = defaultdict(lambda: CERO)
    for cita in citas:
        if cita.estado != 'cancelado':
            monto = Decimal(str(cita.monto_total or 0))
            if monto < 0:
                return revisar(deuda_total, 'Hay un ajuste de importe que requiere revisar la asignación.')
            cargos[categorias[cita.pk]] += monto
    cargos = {cat: total for cat, total in cargos.items() if total > 0}
    extra_presupuesto = max(deuda_total - deuda_citas, CERO)
    if 'revisar' in cargos:
        return revisar(deuda_total, 'Una sesión con importe incluye varios tipos de tratamiento. Indicá su categoría.')

    componentes = []
    if deuda_citas > 0:
        if len(cargos) == 1:
            cat, total = next(iter(cargos.items()))
            # Una única categoría permite usar también pagos sin cita y anticipos.
            componentes.append({'categoria': cat, 'nombre': ETIQUETAS[cat],
                                'saldo': deuda_citas, 'total': total,
                                'abonado': total - deuda_citas, 'nota': ''})
        else:
            if pagos is None:
                return revisar(deuda_total, 'No se pudieron verificar los pagos de las sesiones. Volvé a intentar.')
            abonados = defaultdict(lambda: CERO)
            for cita in citas:
                pago = pagos[cita.pk]
                cat = categorias[cita.pk]
                if pago and (cat == 'revisar' or cita.estado == 'cancelado'):
                    return revisar(deuda_total, 'Hay pagos en sesiones que necesitan una categoría.')
                abonados[cat] += pago
            pool = total_pagado - sum(abonados.values(), CERO)
            saldos = {cat: cargos.get(cat, CERO) - abonados.get(cat, CERO)
                      for cat in set(cargos) | set(abonados)}
            pool += sum((-saldo for saldo in saldos.values() if saldo < 0), CERO)
            saldos = {cat: saldo for cat, saldo in saldos.items() if saldo > 0}
            if pool != 0:
                if len(saldos) != 1:
                    return revisar(deuda_total, 'Hay saldo a favor o pagos sin asignación entre varios tratamientos. Revisá las sesiones.')
                cat = next(iter(saldos))
                saldos[cat] -= pool
            if sum(saldos.values(), CERO) != deuda_citas or any(v < 0 for v in saldos.values()):
                return revisar(deuda_total, 'Los pagos por sesión no coinciden con el saldo del paciente. Volvé a verificar.')
            for cat, nombre in CATEGORIAS:
                saldo = saldos.get(cat, CERO)
                if saldo > 0:
                    total = cargos.get(cat, CERO)
                    componentes.append({'categoria': cat, 'nombre': ETIQUETAS[cat],
                                        'saldo': saldo, 'total': total,
                                        'abonado': total - saldo, 'nota': ''})
    if extra_presupuesto:
        componentes.append({'categoria': 'general', 'nombre': 'Presupuestos',
                            'saldo': extra_presupuesto, 'total': None, 'abonado': None,
                            'nota': 'Saldo de presupuesto no cubierto por la deuda de citas; se cuenta una sola vez.'})
    return componentes
