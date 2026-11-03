from datetime import date, time
from unittest.mock import patch
from django.test import TestCase, RequestFactory
from .models import Appointment, Patient, Procedure, TimeBlock
from .forms import AppointmentForm
from .views import agenda_day, agenda_pro, appointment_cancel


class CancelacionAgendaTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(nombre='Prueba', apellido='Cancelación')
        self.fecha = date(2026, 11, 3)
        self.cita = Appointment.objects.create(paciente=self.patient, fecha=self.fecha,
            hora=time(10), duracion=60, monto_total=2000, motivo='Control')
        self.procedimiento = Procedure.objects.create(nombre='Control')
        self.cita.procedimientos.add(self.procedimiento)
        self.factory = RequestFactory()

    def agenda(self, params=None):
        with patch('core.views.render', side_effect=lambda req, template, ctx: ctx), \
             patch('core.views._obtener_contexto_financiero_citas', return_value={}), \
             patch('core.views.obtener_resumen_cobros_pacientes_bulk', return_value={}):
            return agenda_day(self.factory.get('/', params or {}), 3, 11, 2026)

    def test_cancelar_conserva_datos_y_libera_todo_el_intervalo(self):
        self.assertEqual(appointment_cancel(self.factory.get('/'), self.cita.pk).status_code, 405)
        self.assertTrue(next(h for h in self.agenda()['horarios'] if h['hora'] == time(10,30))['bloqueado'])
        self.assertEqual(appointment_cancel(self.factory.post('/'), self.cita.pk).status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, 'cancelado')
        self.assertEqual(self.cita.monto_total, 2000)
        self.assertEqual(self.cita.procedimientos.count(), 1)
        ctx = self.agenda()
        self.assertEqual([c.pk for c in ctx['citas_canceladas']], [self.cita.pk])
        for h in ctx['horarios']:
            if time(10) <= h['hora'] < time(11):
                self.assertFalse(h['ocupado_exacto'])
                self.assertFalse(h['bloqueado'])
                self.assertEqual(h['citas_exactas'], [])
        form = AppointmentForm({'paciente':self.patient.pk, 'fecha': self.fecha,
            'hora':'10:00', 'duracion':60, 'estado':'pendiente',
            'odontologo':self.cita.odontologo_id, 'procedimientos':[self.procedimiento.pk],
            'monto_total':0})
        self.assertTrue(form.is_valid(), form.errors)
        replacement = form.save()
        self.assertNotEqual(replacement.pk, self.cita.pk)
        self.assertEqual(Appointment.objects.filter(paciente=self.patient).count(), 2)

    def test_cancelar_respeta_bloqueos_independientes(self):
        appointment_cancel(self.factory.post('/'), self.cita.pk)
        TimeBlock.objects.create(fecha=self.fecha, hora=time(10), motivo='Bloqueo manual')
        slot = next(h for h in self.agenda()['horarios'] if h['hora'] == time(10))
        self.assertTrue(slot['bloqueado'])
        self.assertEqual(slot['motivo'], 'Bloqueo manual')

    def calendario(self, params=None):
        query = {'fecha': str(self.fecha), **(params or {})}
        with patch('core.views.render', side_effect=lambda req, template, ctx: ctx):
            return agenda_pro(self.factory.get('/', query))

    def test_cancelar_desde_agenda_libera_calendario_y_conserva_historial(self):
        for duracion in (15, 30, 45, 60):
            with self.subTest(duracion=duracion):
                self.cita.duracion = duracion
                self.cita.estado = 'pendiente'
                self.cita.save()
                appointment_cancel(self.factory.post('/'), self.cita.pk)
                for query in ({}, {'q': 'Prueba'}, {'odontologo': str(self.cita.odontologo_id)}):
                    filas = self.calendario(query)['filas']
                    for fila in filas:
                        if time(10) <= fila['hora'] < self.cita.hora_fin:
                            celda = fila['celdas'][1]
                            self.assertFalse(celda['ocupado'])
                            self.assertFalse(celda['bloqueado'])
                            self.assertFalse(celda.get('ocultar', False))
                            self.assertEqual(celda['citas'], [])
                self.assertEqual(self.agenda()['citas_canceladas'][0].pk, self.cita.pk)

    def test_calendario_respeta_nueva_cita_y_bloqueo_manual(self):
        appointment_cancel(self.factory.post('/'), self.cita.pk)
        nueva = Appointment.objects.create(paciente=self.patient, fecha=self.fecha,
            hora=time(10), duracion=60, motivo='Nuevo turno')
        celda = next(f for f in self.calendario()['filas'] if f['hora'] == time(10))['celdas'][1]
        self.assertEqual([c['id'] for c in celda['citas']], [nueva.pk])
        self.assertTrue(celda['ocupado'])
        self.assertEqual(celda['rowspan'], 4)
        nueva.delete()
        TimeBlock.objects.create(fecha=self.fecha, hora=time(10), motivo='Bloqueo manual')
        celda = next(f for f in self.calendario()['filas'] if f['hora'] == time(10))['celdas'][1]
        self.assertTrue(celda['bloqueado'])
        self.assertEqual(celda['tipo_bloqueo'], 'horario')
