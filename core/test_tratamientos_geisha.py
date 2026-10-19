from datetime import date, time
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from activity.models import Activity
from .models import Appointment, Odontologo, Patient, Procedure, TratamientoGeisha


class TratamientosGeishaTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username="Geisha", password="prueba")
        self.client.force_login(self.usuario)
        self.paciente = Patient.objects.create(nombre="Ana", apellido="Prueba", ci="123456")
        self.geisha = Odontologo.objects.get(codigo="geisha")
        self.control = Procedure.objects.create(nombre="Control")
        self.limpieza = Procedure.objects.create(nombre="Limpieza")
        self.cita = Appointment.objects.create(paciente=self.paciente, odontologo=self.geisha,
            fecha=date(2026, 10, 19), hora=time(10), motivo="Control", estado="pendiente")
        self.cita.procedimientos.add(self.control, self.limpieza)
        self.url = reverse("tratamientos_geisha")

    def atender(self):
        self.cita.estado = "asistio"
        self.cita.save(update_fields=["estado"])
        return self.cita.tratamientos_geisha.get(nombre="Control")

    def test_solo_atenciones_geisha_y_un_registro_por_procedimiento(self):
        self.assertFalse(TratamientoGeisha.objects.exists())
        registro = self.atender()
        self.cita.save()
        self.assertEqual(self.cita.tratamientos_geisha.count(), 2)
        Appointment.objects.create(paciente=self.paciente, fecha=self.cita.fecha,
            hora=time(12), motivo="Solo Rodrigo", estado="asistio")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["resumen"], {"total": 2, "en_proceso": 2, "terminados": 0})
        self.assertContains(response, 'name="estado"')
        self.assertNotContains(response, "Solo Rodrigo")
        self.assertEqual(registro.estado, "en_proceso")

    def test_cambiar_estado_independiente_finalizacion_y_reapertura(self):
        registro = self.atender()
        url = reverse("tratamiento_geisha_estado", args=[registro.pk])
        self.client.post(url, {"estado": "terminado", "next": self.url + "?estado=terminado#tratamiento-1"})
        registro.refresh_from_db()
        self.assertEqual(registro.estado, "terminado")
        self.assertEqual(registro.fecha_finalizacion, timezone.localdate())
        self.assertTrue(self.cita.tratamientos_geisha.filter(nombre="Limpieza", estado="en_proceso").exists())
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "asistio")
        self.assertEqual(Activity.objects.filter(section="Tratamientos de Geisha", username="Geisha", action="Modificó").count(), 1)
        self.client.post(url, {"estado": "en_proceso"})
        registro.refresh_from_db()
        self.assertIsNone(registro.fecha_finalizacion)

    def test_estado_se_conserva_al_editar_cita_y_procedimientos_restantes(self):
        registro = self.atender()
        self.client.post(reverse("tratamiento_geisha_estado", args=[registro.pk]), {"estado": "terminado"})
        self.cita.observaciones = "Actualización administrativa"
        self.cita.save()
        self.cita.procedimientos.remove(self.limpieza)
        registro.refresh_from_db()
        self.assertEqual(registro.estado, "terminado")
        self.assertEqual(self.cita.tratamientos_geisha.count(), 1)

    def test_filtros_estado_paciente_fecha_y_fechas_invalidas(self):
        registro = self.atender()
        self.client.post(reverse("tratamiento_geisha_estado", args=[registro.pk]), {"estado": "terminado"})
        response = self.client.get(self.url, {"estado": "terminado", "q": "Ana Prueba", "desde": "2026-10-19", "hasta": "2026-10-19"})
        self.assertEqual(response.context["resumen"]["total"], 1)
        self.assertEqual(list(response.context["registros"])[0].pk, registro.pk)
        self.assertEqual(self.client.get(self.url, {"desde": "2026-10-20"}).context["resumen"]["total"], 0)
        response = self.client.get(self.url, {"desde": "2026-10-21", "hasta": "2026-10-19"})
        self.assertContains(response, "La fecha inicial no puede ser posterior")
        self.assertEqual(response.context["resumen"]["total"], 0)

    def test_cancelar_o_reasignar_excluye_registro_sin_perder_estado(self):
        registro = self.atender()
        self.cita.estado = "cancelado"
        self.cita.save()
        self.assertEqual(self.client.get(self.url).context["resumen"]["total"], 0)
        self.assertEqual(self.client.post(reverse("tratamiento_geisha_estado", args=[registro.pk]), {"estado": "terminado"}).status_code, 404)
        self.atender()
        self.assertEqual(self.client.get(self.url).context["resumen"]["total"], 2)
        self.cita.odontologo = Odontologo.objects.get(codigo="rodrigo")
        self.cita.save()
        self.assertEqual(self.client.get(self.url).context["resumen"]["total"], 0)

    def test_seguridad_login_csrf_metodo_estado_y_retorno(self):
        registro = self.atender()
        url = reverse("tratamiento_geisha_estado", args=[registro.pk])
        self.assertEqual(Client().get(self.url).status_code, 302)
        self.assertEqual(self.client.get(url).status_code, 405)
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.usuario)
        self.assertEqual(protegido.post(url, {"estado": "terminado"}).status_code, 403)
        response = self.client.post(url, {"estado": "invalido", "next": "https://example.com/"})
        self.assertEqual(response.url, self.url)
        registro.refresh_from_db()
        self.assertEqual(registro.estado, "en_proceso")

    def test_migracion_recupera_atenciones_previas_sin_procedimientos(self):
        Appointment.objects.bulk_create([Appointment(paciente=self.paciente, odontologo=self.geisha,
            fecha=self.cita.fecha, hora=time(11), motivo="Resina antigua", estado="asistio")])
        migracion = import_module("core.migrations.0066_tratamientos_geisha")
        migracion.registrar_atenciones_existentes(apps, SimpleNamespace(connection=SimpleNamespace(alias="default")))
        registro = TratamientoGeisha.objects.get(nombre="Resina antigua")
        self.assertEqual(registro.estado, "en_proceso")
        migracion.registrar_atenciones_existentes(apps, SimpleNamespace(connection=SimpleNamespace(alias="default")))
        self.assertEqual(TratamientoGeisha.objects.filter(nombre="Resina antigua").count(), 1)

    def test_impresion_incluye_todas_las_paginas_y_filtros(self):
        registro = self.atender()
        TratamientoGeisha.objects.bulk_create([
            TratamientoGeisha(cita=self.cita, clave=f"extra:{i}", nombre=f"Prueba {i}") for i in range(55)])
        normal = self.client.get(self.url)
        self.assertEqual(len(normal.context["registros"]), 50)
        response = self.client.get(self.url, {"imprimir": "1"})
        self.assertEqual(len(response.context["registros"]), 57)
        self.assertIsNone(response.context["pagina"])
        self.assertContains(response, "Imprimir / Guardar como PDF")
