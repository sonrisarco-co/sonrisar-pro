from datetime import time
from .test_cancelaciones import CancelacionAgendaTests
from .views import appointment_confirm
from .forms import AppointmentForm
from .models import Appointment, TimeBlock


class SinRespuestaAgendaTests(CancelacionAgendaTests):
    def marcar(self):
        return appointment_confirm(
            self.factory.post('/', {'estado': 'sin_respuesta'}), self.cita.pk)

    def test_sin_respuesta_libera_intervalo_y_conserva_registro(self):
        for duracion in (15, 30, 45, 60):
            with self.subTest(duracion=duracion):
                self.cita.estado = 'pendiente'
                self.cita.duracion = duracion
                self.cita.save()
                self.assertEqual(self.marcar().status_code, 200)
                self.cita.refresh_from_db()
                self.assertEqual(self.cita.estado, 'sin_respuesta')
                self.assertEqual(self.cita.monto_total, 2000)
                self.assertEqual(self.cita.procedimientos.count(), 1)
                ctx = self.agenda()
                self.assertEqual([c.pk for c in ctx['citas_sin_respuesta']], [self.cita.pk])
                self.assertEqual(ctx['citas_canceladas'], [])
                for slot in ctx['horarios']:
                    if time(10) <= slot['hora'] < self.cita.hora_fin:
                        self.assertFalse(slot['ocupado_exacto'])
                        self.assertFalse(slot['bloqueado'])
                for params in ({}, {'q': 'Prueba'}, {'odontologo': str(self.cita.odontologo_id)}):
                    for fila in self.calendario(params)['filas']:
                        if time(10) <= fila['hora'] < self.cita.hora_fin:
                            celda = fila['celdas'][1]
                            self.assertFalse(celda['ocupado'])
                            self.assertFalse(celda['bloqueado'])
                            self.assertFalse(celda.get('ocultar', False))

    def test_puede_reutilizar_turno_y_no_reconfirmar_encima(self):
        self.marcar()
        form = AppointmentForm({'paciente': self.patient.pk, 'fecha': self.fecha,
            'hora': '10:00', 'duracion': 60, 'estado': 'pendiente',
            'odontologo': self.cita.odontologo_id,
            'procedimientos': [self.procedimiento.pk], 'monto_total': 0})
        self.assertTrue(form.is_valid(), form.errors)
        nueva = form.save()
        response = appointment_confirm(self.factory.post('/'), self.cita.pk)
        self.assertEqual(response.status_code, 409)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, 'sin_respuesta')
        celda = next(f for f in self.calendario()['filas'] if f['hora'] == time(10))['celdas'][1]
        self.assertEqual([c['id'] for c in celda['citas']], [nueva.pk])

    def test_respeta_bloqueo_manual(self):
        self.marcar()
        TimeBlock.objects.create(fecha=self.fecha, hora=time(10), motivo='Bloqueo manual')
        slot = next(h for h in self.agenda()['horarios'] if h['hora'] == time(10))
        self.assertTrue(slot['bloqueado'])
        self.assertEqual(appointment_confirm(self.factory.post('/'), self.cita.pk).status_code, 409)

    def test_reconfirmar_libre_reserva_nuevamente(self):
        self.marcar()
        self.assertEqual(appointment_confirm(self.factory.post('/'), self.cita.pk).status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, 'confirmado')
        self.assertEqual(self.agenda()['citas_sin_respuesta'], [])
