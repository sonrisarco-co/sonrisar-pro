from datetime import date, time
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth.models import User
from django.db.models.deletion import ProtectedError
from django.test import TestCase, Client
from django.urls import reverse
from .models import (Appointment, Odontologo, Patient, TratamientoGeisha,
                     CobroTratamientoGeisha, LiquidacionGeisha, DetalleLiquidacionGeisha)


class ComisionesGeishaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('responsable', password='prueba')
        self.client.force_login(self.user)
        self.paciente = Patient.objects.create(nombre='Ana', apellido='Prueba', ci='123')
        self.cita = Appointment.objects.create(paciente=self.paciente,
            odontologo=Odontologo.objects.get(codigo='geisha'), fecha=date(2026, 10, 19),
            hora=time(10), motivo='Conducto', estado='asistio')
        self.r = self.cita.tratamientos_geisha.get()
        self.r.importe = Decimal('8000')
        self.r.estado = 'terminado'
        self.r.save()
        self.total = '8000'
        self.mock = patch('core.views._obtener_pagos_cobros_citas_bulk', side_effect=self.resumen).start()
        self.addCleanup(patch.stopall)
        self.url = reverse('comision_geisha_detalle', args=[self.r.pk])

    def resumen(self, ids):
        return {pk: {'total_pagado': self.total} for pk in ids}

    def asignar(self, monto='8000', cita=None):
        return self.client.post(self.url, {'accion': 'asignar', 'cita': (cita or self.cita).pk, 'monto': monto})

    def pagar(self, ids=None):
        return self.client.post(reverse('comisiones_geisha_liquidar'), {
            'tratamientos': ids or [self.r.pk], 'fecha': '2026-10-19', 'metodo': 'transferencia', 'referencia': 'Banco 123'})

    def test_solo_terminado_y_cobro_completo_comision_y_comprobante(self):
        self.asignar()
        response = self.client.get(reverse('comisiones_geisha'))
        self.assertEqual(response.context['total_disponible'], Decimal('2400'))
        self.assertContains(response, 'Disponible para pagar')
        self.pagar()
        d = DetalleLiquidacionGeisha.objects.get()
        self.assertEqual(d.comision, Decimal('2400'))
        self.assertEqual(d.importe, Decimal('8000'))
        self.assertContains(self.client.get(reverse('liquidacion_geisha', args=[d.liquidacion_id])), '2400')
        self.pagar()
        self.assertEqual(LiquidacionGeisha.objects.count(), 1)

    def test_parcial_o_en_proceso_no_habilita(self):
        self.total = '4000'
        self.asignar('4000')
        self.pagar()
        self.assertFalse(LiquidacionGeisha.objects.exists())
        self.total = '8000'
        self.asignar()
        self.r.estado = 'en_proceso'; self.r.save()
        self.pagar()
        self.assertFalse(LiquidacionGeisha.objects.exists())

    def test_no_reutiliza_fondos_entre_tratamientos(self):
        self.asignar('6000')
        otro = TratamientoGeisha.objects.create(cita=self.cita, clave='extra', nombre='Otro', importe=3000)
        response = self.client.post(reverse('comision_geisha_detalle', args=[otro.pk]), {
            'accion': 'asignar', 'cita': self.cita.pk, 'monto': '3000'})
        self.assertContains(response, 'No hay suficiente dinero')
        self.assertFalse(otro.cobros_asignados.exists())

    def test_cobros_en_varias_citas_y_rechaza_otro_paciente(self):
        segunda = Appointment.objects.create(paciente=self.paciente, fecha=self.cita.fecha,
            hora=time(12), motivo='Cuota')
        self.total = '4000'
        self.asignar('4000'); self.asignar('4000', segunda)
        self.pagar()
        self.assertEqual(DetalleLiquidacionGeisha.objects.get().comision, Decimal('2400'))
        otro_paciente = Patient.objects.create(nombre='Otra', apellido='Persona', ci='456')
        tercera = Appointment.objects.create(paciente=otro_paciente, fecha=self.cita.fecha, hora=time(13), motivo='Otro')
        # Nueva fila sin liquidar para comprobar el aislamiento por paciente.
        otro = TratamientoGeisha.objects.create(cita=self.cita, clave='extra', nombre='Extra', importe=1000)
        self.client.post(reverse('comision_geisha_detalle', args=[otro.pk]), {'accion':'asignar','cita':tercera.pk,'monto':'1000'})
        self.assertFalse(otro.cobros_asignados.exists())

    def test_devolucion_o_caida_cobros_bloquea_y_lote_es_atomico(self):
        self.asignar()
        self.total = '7900'
        self.pagar()
        self.assertFalse(LiquidacionGeisha.objects.exists())
        self.mock.return_value = None
        self.mock.side_effect = None
        self.pagar()
        self.assertFalse(LiquidacionGeisha.objects.exists())
        self.mock.side_effect = self.resumen
        self.total = '8000'
        self.pagar([self.r.pk, 999999])
        self.assertFalse(LiquidacionGeisha.objects.exists())

    def test_pago_bloquea_importes_asignaciones_reapertura_y_borrado(self):
        self.asignar(); self.pagar()
        self.client.post(self.url, {'accion':'importe','importe':'9000'})
        self.asignar('0')
        self.client.post(reverse('tratamiento_geisha_estado', args=[self.r.pk]), {'estado':'en_proceso'})
        self.r.refresh_from_db()
        self.assertEqual(self.r.importe, Decimal('8000'))
        self.assertEqual(self.r.estado, 'terminado')
        self.assertEqual(self.r.cobros_asignados.get().monto, Decimal('8000'))
        with self.assertRaises(ProtectedError):
            self.r.delete()

    def test_no_sobreasigna_importe_y_puede_quitar_asignacion(self):
        self.total = '9000'
        self.asignar('9000')
        self.assertFalse(CobroTratamientoGeisha.objects.exists())
        self.asignar()
        self.client.post(self.url, {'accion':'importe','importe':'7000'})
        self.r.refresh_from_db(); self.assertEqual(self.r.importe, Decimal('8000'))
        self.asignar('0')
        self.assertFalse(CobroTratamientoGeisha.objects.exists())

    def test_cambios_procedimientos_conservan_registro_financiero(self):
        from .models import Procedure
        self.asignar()
        self.cita.procedimientos.add(Procedure.objects.create(nombre='Corrección'))
        self.assertTrue(TratamientoGeisha.objects.filter(pk=self.r.pk).exists())

    def test_seguridad_y_csrf(self):
        no_responsable = User.objects.create_user('Geisha', password='prueba')
        self.client.force_login(no_responsable)
        self.assertEqual(self.client.get(reverse('comisiones_geisha')).status_code, 403)
        self.assertEqual(self.client.post(self.url, {'accion':'importe','importe':'1'}).status_code, 403)
        self.assertEqual(self.client.get(reverse('tratamientos_geisha')).status_code, 200)
        protegido = Client(enforce_csrf_checks=True); protegido.force_login(self.user)
        self.assertEqual(protegido.post(reverse('comisiones_geisha_liquidar')).status_code, 403)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('comisiones_geisha_liquidar')).status_code, 405)

    def test_devolucion_posterior_senalada_sin_cambiar_historial(self):
        self.asignar(); self.pagar(); self.total = '0'
        response = self.client.get(reverse('comisiones_geisha'))
        self.assertContains(response, 'Revisar cobros')
        self.assertEqual(DetalleLiquidacionGeisha.objects.get().comision, Decimal('2400'))
