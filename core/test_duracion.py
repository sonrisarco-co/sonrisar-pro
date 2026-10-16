from datetime import date, time
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory
from django.template.loader import get_template
from .forms import AppointmentForm
from .models import Appointment, Patient, Procedure, TimeBlock
from .views import agenda_pro, agenda_day, appointment_move_time, bloquear_horario


class DuracionCitaTests(TestCase):
    def setUp(self):
        self.paciente = Patient.objects.create(nombre="Prueba", apellido="Duración")
        self.fecha = date(2026, 10, 20)
        self.procedimiento = Procedure.objects.create(nombre="Control")

    def cita(self, hora=time(10), duracion=45, **kw):
        return Appointment.objects.create(paciente=self.paciente, fecha=self.fecha,
                                          hora=hora, duracion=duracion, **kw)

    def form(self, hora="10:00", duracion=30, instance=None):
        return AppointmentForm({"paciente": self.paciente.id, "fecha": self.fecha,
            "hora": hora, "duracion": duracion, "estado": "pendiente",
            "procedimientos": [self.procedimiento.id], "monto_total": "0"}, instance=instance)

    def test_opciones_se_guardan_y_se_calcula_el_fin(self):
        for duracion, fin in [(15, time(10, 15)), (30, time(10, 30)),
                              (45, time(10, 45)), (60, time(11))]:
            form = self.form(duracion=duracion)
            self.assertTrue(form.is_valid(), form.errors)
            cita = form.save()
            self.assertEqual(cita.hora_fin, fin)
            cita.delete()
        self.assertFalse(self.form(duracion=20).is_valid())
        self.assertEqual(AppointmentForm().initial["duracion"], 30)

    def test_rechaza_cruces_y_permite_limite_exacto(self):
        self.cita()
        self.assertFalse(self.form("10:30", 15).is_valid())
        self.assertFalse(self.form("09:30", 60).is_valid())
        self.assertTrue(self.form("10:45", 30).is_valid())
        self.assertTrue(self.form("09:30", 30).is_valid())

    def test_descanso_bloqueo_y_cierre_se_validan_por_todo_el_intervalo(self):
        self.assertFalse(self.form("13:30", 45).is_valid())
        self.assertFalse(self.form("19:30", 60).is_valid())
        self.assertTrue(self.form("19:30", 30).is_valid())
        TimeBlock.objects.create(fecha=self.fecha, hora=time(11, 15))
        self.assertFalse(self.form("10:45", 60).is_valid())

    def test_editar_y_cancelar_no_confunde_su_propia_reserva(self):
        cita = self.cita(duracion=30)
        self.assertTrue(self.form(duracion=45, instance=cita).is_valid())
        cita.estado = "cancelado"
        cita.save()
        self.assertTrue(self.form(duracion=60).is_valid())

    def test_mover_conserva_duracion_y_rechaza_destino_ocupado(self):
        cita = self.cita()
        self.cita(hora=time(12), duracion=30)
        request = RequestFactory().post('/', {'hora': '11:45', 'fecha': str(self.fecha)})
        response = appointment_move_time(request, cita.id)
        self.assertEqual(response.status_code, 400)
        cita.refresh_from_db()
        self.assertEqual(cita.hora, time(10))
        response = appointment_move_time(RequestFactory().post('/', {
            'hora': '11:00', 'fecha': str(self.fecha)}), cita.id)
        self.assertEqual(response.status_code, 200)
        cita.refresh_from_db()
        self.assertEqual(cita.hora_fin, time(11, 45))

    def calendario(self, q=""):
        with patch('core.views.render', side_effect=lambda request, template, context: context):
            return agenda_pro(RequestFactory().get('/', {'fecha': str(self.fecha), 'q': q}))

    def test_una_tarjeta_ocupa_el_intervalo_y_no_oculta_conflictos_antiguos(self):
        cita = self.cita(duracion=60)
        contexto = self.calendario()
        filas = {f['hora']: f['celdas'][1] for f in contexto['filas']}
        self.assertEqual(filas[time(10)]['rowspan'], 3)
        self.assertTrue(filas[time(10, 30)]['ocultar'])
        self.assertFalse(filas[time(11)].get('ocultar', False))
        self.assertEqual(sum(len(c['citas']) for c in filas.values()), 1)
        self.cita(hora=time(10, 30), duracion=15)
        contexto = self.calendario()
        filas = {f['hora']: f['celdas'][1] for f in contexto['filas']}
        self.assertFalse(filas[time(10)].get('rowspan', 1) > 1)
        self.assertEqual(len(filas[time(10, 30)]['citas']), 1)

    def test_busqueda_no_libera_reservas_de_otro_paciente(self):
        self.cita(duracion=60)
        contexto = self.calendario('Otro')
        fila = next(f for f in contexto['filas'] if f['hora'] == time(10, 30))
        self.assertTrue(fila['celdas'][1]['bloqueado'])

    def test_agenda_del_dia_reserva_continuacion_sin_duplicar_paciente(self):
        cita = self.cita(duracion=60)
        with patch('core.views.render', side_effect=lambda request, template, context: context), \
             patch('core.views._obtener_contexto_financiero_citas', return_value={}), \
             patch('core.views.obtener_resumen_cobros_pacientes_bulk', return_value={}):
            contexto = agenda_day(RequestFactory().get('/'), 20, 10, 2026)
        filas = {f['hora']: f for f in contexto['horarios']}
        self.assertTrue(filas[time(10, 30)]['bloqueado'])
        self.assertEqual(filas[time(10)]['citas_exactas'][0]['duracion'], 60)
        self.assertEqual(sum(len(f['citas_exactas']) + len(f['citas_extra'])
                             for f in filas.values()), 1)

    def test_templates_compilan(self):
        for name in ['agenda_pro', 'agenda_day', 'appointment_form_partial']:
            get_template(f'core/{name}.html')
