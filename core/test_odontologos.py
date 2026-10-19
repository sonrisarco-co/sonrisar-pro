from datetime import date, time
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.template.loader import render_to_string

from .forms import AppointmentForm
from .models import Appointment, Odontologo, Patient, Procedure
from .scheduling import validar_reserva
from .views import agenda_day, agenda_pro


class OdontologosAgendaTests(TestCase):
    def setUp(self):
        self.rodrigo = Odontologo.objects.get(codigo="rodrigo")
        self.geisha = Odontologo.objects.get(codigo="geisha")
        self.paciente = Patient.objects.create(nombre="Paciente", apellido="Prueba")
        self.fecha = date(2026, 10, 19)
        self.cita = Appointment.objects.create(
            paciente=self.paciente, fecha=self.fecha, hora=time(10), duracion=45)

    def test_formulario_predeterminado_edicion_y_error_de_profesional(self):
        self.assertEqual(self.cita.odontologo, self.rodrigo)
        self.assertEqual(AppointmentForm()["odontologo"].value(), self.rodrigo.pk)
        datos = {"paciente": self.paciente.pk, "fecha": "2026-10-19", "hora": "10:00",
                 "duracion": 45, "odontologo": self.geisha.pk, "estado": "pendiente",
                 "procedimientos": [Procedure.objects.get(nombre="Control").pk]}
        form = AppointmentForm(datos, instance=self.cita)
        self.assertTrue(form.is_valid(), form.errors)
        guardada = form.save()
        self.assertEqual(guardada.odontologo, self.geisha)
        self.assertEqual(AppointmentForm(instance=guardada)["odontologo"].value(), self.geisha.pk)
        datos["odontologo"] = 999999
        self.assertFalse(AppointmentForm(datos, instance=guardada).is_valid())

    def test_sillon_compartido_respeta_intervalo_y_final(self):
        otra = Appointment(paciente=self.paciente, fecha=self.fecha, hora=time(10, 30),
                           duracion=30, odontologo=self.geisha)
        with self.assertRaises(ValidationError):
            validar_reserva(otra)
        otra.hora = time(10, 45)
        validar_reserva(otra)
        otra.estado = "cancelado"
        otra.hora = time(10)
        validar_reserva(otra)

    def test_filtro_calendario_no_libera_sillon_de_rodrigo(self):
        with patch("core.views.render", side_effect=lambda request, template, context: context):
            contexto = agenda_pro(RequestFactory().get("/", {
                "fecha": "2026-10-19", "odontologo": self.geisha.pk}))
        filas = {fila["hora"]: fila["celdas"][0] for fila in contexto["filas"]}
        self.assertTrue(filas[time(10)]["bloqueado"])
        self.assertFalse(filas[time(10)]["citas"])
        self.assertTrue(filas[time(10, 30)]["bloqueado"])
        self.assertFalse(filas[time(10, 45)]["bloqueado"])

    def test_filtro_diario_no_libera_sillon_de_rodrigo(self):
        request = RequestFactory().get("/", {"odontologo": self.geisha.pk})
        with patch("core.views.render", side_effect=lambda request, template, context: context), \
             patch("core.views._obtener_contexto_financiero_citas", return_value={}), \
             patch("core.views.obtener_resumen_cobros_pacientes_bulk", return_value={}):
            contexto = agenda_day(request, 19, 10, 2026)
        filas = {fila["hora"]: fila for fila in contexto["horarios"]}
        self.assertTrue(filas[time(10)]["bloqueado"])
        self.assertFalse(filas[time(10)]["citas_exactas"])
        self.assertTrue(filas[time(10, 30)]["bloqueado"])
        self.assertFalse(filas[time(10, 45)]["ocupado_exacto"])

    def test_html_incluye_selector_y_profesional_en_citas(self):
        request = RequestFactory().get("/")
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        from .views import _calendar_saved_appointment_url
        from django.urls import reverse
        destino = _calendar_saved_appointment_url(
            reverse("agenda_pro") + "?odontologo=" + str(self.geisha.pk), self.cita)
        self.assertIn("odontologo=" + str(self.rodrigo.pk), destino)
        html = render_to_string("core/appointment_form_partial.html", {
            "form": AppointmentForm(instance=self.cita), "request": request})
        self.assertIn('name="odontologo"', html)
        self.assertIn("Geisha", html)
        html = render_to_string("core/patient_appointments.html", {
            "paciente": self.paciente, "citas": [self.cita], "request": request})
        self.assertIn("Rodrigo", html)
