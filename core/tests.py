from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, RequestFactory, override_settings
from django.urls import reverse

from .models import Patient, Appointment, Budget, BudgetPayment
from .views import (
    _armar_cita_agenda_rapida, _combinar_pagos_citas,
    _obtener_contexto_financiero_citas, patient_finances,
)


class FinanzasSaldoCitasTests(TestCase):
    def setUp(self):
        self.paciente = Patient.objects.create(nombre="Prueba", apellido="Saldo")
        self.presupuesto = Budget.objects.create(
            paciente=self.paciente, total=18700, estado="confirmado",
        )
        BudgetPayment.objects.create(presupuesto=self.presupuesto, monto=18700)
        self.citas = [
            Appointment.objects.create(
                paciente=self.paciente, fecha=fecha, hora=time(10, 30),
                monto_total=monto, estado="asistio",
            )
            for fecha, monto in [(date(2026, 7, 14), 7000), (date(2026, 8, 12), 6100)]
        ]

    def contexto(self, pagado, devuelto=0):
        with patch("core.views.obtener_detalle_cobros_paciente", return_value={
            "ok": True, "total_pagado": pagado,
            "total_pagado_bruto": pagado + devuelto, "total_devuelto": devuelto,
        }), patch("core.views.render", side_effect=lambda request, template, context: context):
            return patient_finances(RequestFactory().get("/"), self.paciente.id)

    @override_settings(DEBUG=False)
    def test_ajuste_pagado_aparte_conserva_saldo_y_coincide_con_agenda(self):
        antes = self.contexto(19600)
        self.assertEqual(antes["saldo_a_favor"], Decimal("6500"))
        hoy = Appointment.objects.create(
            paciente=self.paciente, fecha=date(2026, 9, 9), hora=time(10, 30),
            monto_total=900, estado="asistio",
        )
        despues = self.contexto(20500)
        self.assertEqual(despues["saldo_a_favor"], antes["saldo_a_favor"])
        self.assertEqual(despues["saldo_pendiente"], 0)
        self.assertEqual(despues["presupuestos"][0]["saldo"], 0)
        pagos = {
            cita.id: {"total_pagado": monto}
            for cita, monto in zip(self.citas + [hoy], [18700, 900, 900])
        }
        with patch("core.views._obtener_pagos_cobros_citas_bulk", return_value=pagos):
            agenda = _obtener_contexto_financiero_citas([hoy], hoy.fecha)
        self.assertEqual(agenda[hoy.id]["saldo_a_favor_restante"], despues["saldo_a_favor"])
        self.assertEqual(agenda[hoy.id]["saldo_generado"], 0)

    def test_devolucion_reduce_saldo_sin_reponer_pago_del_presupuesto(self):
        contexto = self.contexto(12000, devuelto=7600)
        self.assertEqual(contexto["saldo_a_favor"], 0)
        self.assertEqual(contexto["saldo_pendiente"], 1100)

    def test_cita_cancelada_no_consume_saldo(self):
        Appointment.objects.create(
            paciente=self.paciente, fecha=date(2026, 9, 9), hora=time(10),
            monto_total=900, estado="cancelado",
        )
        self.assertEqual(self.contexto(19600)["saldo_a_favor"], 6500)

    def test_presupuesto_pendiente_se_muestra_separado_del_saldo_de_citas(self):
        BudgetPayment.objects.all().delete()
        contexto = self.contexto(13100)
        self.assertEqual(contexto["saldo_a_favor"], 0)
        self.assertEqual(contexto["saldo_pendiente"], 0)
        self.assertEqual(contexto["presupuestos"][0]["saldo"], 18700)


class AgendaNoAsistioTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user("operador_agenda"))
        paciente = Patient.objects.create(nombre="Prueba", apellido="Agenda")
        self.cita = Appointment.objects.create(
            paciente=paciente, fecha=date(2026, 9, 9), hora=time(10),
            estado="confirmado", monto_total=900, pagado=True,
            historia_actualizada=True,
        )
        from django.urls import reverse
        self.url = reverse("appointment_no_show", args=[self.cita.id])

    def test_cambia_solo_la_asistencia_y_admite_repetir(self):
        for _ in range(2):
            response = self.client.post(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["estado"], "No asistió")
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "no_asistio")
        self.assertEqual(self.cita.monto_total, 900)
        self.assertTrue(self.cita.pagado)
        self.assertTrue(self.cita.historia_actualizada)

    def test_get_no_cambia_estado(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "confirmado")

    def test_cancelada_no_cambia(self):
        self.cita.estado = "cancelado"
        self.cita.save()
        self.assertEqual(self.client.post(self.url).status_code, 409)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "cancelado")

    def test_requiere_csrf(self):
        from django.test import Client
        self.assertEqual(Client(enforce_csrf_checks=True).post(self.url).status_code, 403)

    def test_plantilla_agenda_compila(self):
        from django.template.loader import get_template
        get_template("core/agenda_day.html")


class DeudoresArchivadosTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_user("operador_deudores"))
        self.activo = Patient.objects.create(
            nombre="Activa", apellido="Deudora", ci="DEU-1"
        )
        self.archivado = Patient.objects.create(
            nombre="Archivada", apellido="Deudora", ci="DEU-2",
            archivado_deudores=True,
        )
        Appointment.objects.create(
            paciente=self.activo, fecha=date(2026, 8, 1), hora=time(10),
            motivo="Prueba", estado="asistio", monto_total=900,
        )
        Appointment.objects.create(
            paciente=self.archivado, fecha=date(2026, 7, 1), hora=time(11),
            motivo="Prueba", estado="asistio", monto_total=500,
        )
        Appointment.objects.create(
            paciente=self.activo, fecha=date(2026, 8, 2), hora=time(10),
            motivo="Cita cancelada", estado="cancelado", monto_total=12000,
        )

    def _resumen_cobros_sin_pagos(self, patient_ids):
        return {
            int(patient_id): {"total_pagado": Decimal("0")}
            for patient_id in patient_ids
        }

    def test_archivar_y_restaurar_conserva_saldo_y_actualiza_total_activo(self):
        url = reverse("deudores_general")
        with patch(
            "core.views.obtener_resumen_cobros_pacientes_bulk",
            side_effect=self._resumen_cobros_sin_pagos,
        ):
            respuesta = self.client.get(url)
        self.assertContains(respuesta, "Deuda total activa: $ 900")
        self.assertContains(respuesta, "Deudora, Activa")
        self.assertNotContains(respuesta, "Deudora, Archivada")

        archivar_url = reverse("deudor_archivar", args=[self.activo.id])
        respuesta = self.client.post(archivar_url, {"next": f"{url}?estado=archivados"})
        self.assertRedirects(respuesta, f"{url}?estado=archivados")
        self.activo.refresh_from_db()
        self.assertTrue(self.activo.archivado_deudores)

        with patch(
            "core.views.obtener_resumen_cobros_pacientes_bulk",
            side_effect=self._resumen_cobros_sin_pagos,
        ):
            respuesta = self.client.get(f"{url}?estado=archivados")
        self.assertContains(respuesta, "Deudora, Activa")
        self.assertContains(respuesta, "Deudora, Archivada")
        self.assertContains(respuesta, "Total: $ 900")
        self.assertNotContains(respuesta, "Deuda total activa")

        restaurar_url = reverse("deudor_restaurar", args=[self.activo.id])
        respuesta = self.client.post(restaurar_url, {"next": url})
        self.assertRedirects(respuesta, url)
        self.activo.refresh_from_db()
        self.assertFalse(self.activo.archivado_deudores)

        with patch(
            "core.views.obtener_resumen_cobros_pacientes_bulk",
            side_effect=self._resumen_cobros_sin_pagos,
        ):
            respuesta = self.client.get(url)
        self.assertContains(respuesta, "Deuda total activa: $ 900")
        self.assertContains(respuesta, "Deudora, Activa")
        self.assertNotContains(respuesta, "Deudora, Archivada")


class AgendaAsistioTests(AgendaNoAsistioTests):
    def setUp(self):
        super().setUp()
        from django.urls import reverse
        self.url = reverse("appointment_attended", args=[self.cita.id])

    def test_cambia_solo_la_asistencia_y_admite_repetir(self):
        self.cita.estado = "no_asistio"
        self.cita.monto_total = 0
        self.cita.pagado = False
        self.cita.save()
        for _ in range(2):
            response = self.client.post(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["estado"], "Asistió")
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "asistio")
        self.assertEqual(self.cita.monto_total, 0)
        self.assertFalse(self.cita.pagado)
        self.assertTrue(self.cita.historia_actualizada)


class AgendaSaldoAFavorTests(SimpleTestCase):
    def test_conserva_el_pago_web_si_cobros_local_no_tiene_la_cita(self):
        pagos_locales = {3: {"total_pagado": "0", "pagos": []}}
        pagos_web = {
            3: {"total_pagado": "900", "pagos": [{"id": 10}]},
        }

        combinados = _combinar_pagos_citas(pagos_locales, pagos_web)

        self.assertEqual(combinados[3]["total_pagado"], "900")

    def test_muestra_en_una_cita_posterior_el_saldo_que_sigue_disponible(self):
        paciente = SimpleNamespace(
            id=616,
            nombre="Luana",
            apellido="Corbo",
            fecha_nacimiento=date(2000, 1, 1),
            ci="",
        )
        procedimientos = SimpleNamespace(all=lambda: [])
        cita = SimpleNamespace(
            id=3,
            paciente=paciente,
            hora=time(12, 30),
            motivo="Ajuste (ortodoncia)",
            procedimientos=procedimientos,
            estado="asistio",
            get_estado_display=lambda: "Asistió",
            historia_actualizada=False,
            monto_total=Decimal("900"),
            primera_cita_id=1,
        )
        contexto = {
            cita.id: {
                "pago_cita": Decimal("900"),
                "deuda_cita": Decimal("0"),
                "saldo_generado": Decimal("0"),
                "saldo_usado": Decimal("0"),
                "saldo_a_favor_restante": Decimal("100"),
                "ultimo_pago_id": None,
                "cobros_error": None,
            }
        }

        cita.duracion = 15
        cita.hora_fin = time(10, 45)
        cita_agenda = _armar_cita_agenda_rapida(cita, contexto)

        self.assertTrue(cita_agenda["tiene_saldo_a_favor"])
        self.assertEqual(cita_agenda["saldo_a_favor"], Decimal("100"))


class EsquemaTurnosMixtosTests(SimpleTestCase):
    def test_horarios_lunes_a_viernes_coinciden_con_referencia(self):
        from .views import horarios_para_fecha
        esperado = [f"{h:02d}:{m:02d}" for h in range(9, 20) for m in (0, 15, 30, 45)]
        for dia in range(12, 17):
            self.assertEqual([h.strftime('%H:%M') for h in horarios_para_fecha(date(2026, 10, dia))], esperado)

    def test_sabado_conserva_horarios(self):
        from .views import horarios_para_fecha, generar_horarios
        self.assertEqual(horarios_para_fecha(date(2026, 10, 17)),
                         [time(h, m) for h in range(9, 20) for m in (0, 15, 30, 45)])

    def test_citas_se_agrupan_en_su_turno_sin_cambiar_hora(self):
        from .views import agrupar_citas_por_bloque
        fecha = date(2026, 10, 14)
        citas = [SimpleNamespace(fecha=fecha, hora=h) for h in
                 [time(9, 15), time(10, 45), time(11, 14), time(11, 15), time(18, 30), time(19, 30)]]
        bloques = agrupar_citas_por_bloque(citas, mixto=True)
        self.assertEqual(set(bloques), {time(9, 15), time(10, 45), time(11), time(11, 15), time(18, 30), time(19, 30)})
        self.assertEqual(bloques[time(11)][0].hora, time(11, 14))
        self.assertEqual(sum(map(len, bloques.values())), len(citas))


class GrillaTurnosMixtosTests(TestCase):
    def test_calendario_separa_quince_minutos_y_conserva_sabado(self):
        from .views import agenda_pro
        paciente = Patient.objects.create(nombre='Prueba', apellido='Turnos')
        cita = Appointment.objects.create(paciente=paciente, fecha=date(2026, 10, 14), hora=time(10, 45))
        with patch('core.views.render', side_effect=lambda request, template, context: context):
            contexto = agenda_pro(RequestFactory().get('/', {'fecha': '2026-10-14'}))
        filas = {fila['hora']: fila['celdas'] for fila in contexto['filas']}
        self.assertEqual(filas[time(10, 45)][2]['citas'][0]['id'], cita.id)
        self.assertFalse(filas[time(10, 45)][2]['bloqueado'])
        self.assertFalse(filas[time(10, 45)][5]['bloqueado'])
        self.assertFalse(filas[time(9)][5]['bloqueado'])
        self.assertFalse(filas[time(9)][2]['bloqueado'])
        self.assertEqual(filas[time(14)][2]['motivo_bloqueo'], 'Descanso')
        self.assertFalse(filas[time(14)][5]['bloqueado'])

    def test_agenda_diaria_conserva_citas_antiguas_y_separa_turnos(self):
        from .views import agenda_day
        paciente = Patient.objects.create(nombre='Prueba', apellido='Diaria')
        for hora in [time(9, 30), time(10, 45), time(18, 15), time(19, 30)]:
            Appointment.objects.create(paciente=paciente, fecha=date(2026, 10, 14), hora=hora)
        with patch('core.views.render', side_effect=lambda request, template, context: context), \
             patch('core.views._obtener_contexto_financiero_citas', return_value={}), \
             patch('core.views.obtener_resumen_cobros_pacientes_bulk', return_value={}):
            contexto = agenda_day(RequestFactory().get('/'), 14, 10, 2026)
        filas = {fila['hora']: fila for fila in contexto['horarios']}
        for hora in [time(9, 30), time(10, 45), time(18, 15), time(19, 30)]:
            self.assertEqual(len(filas[hora]['citas_exactas']), 1)
        self.assertTrue(filas[time(14)]['bloqueado'])
        self.assertTrue(filas[time(14, 30)]['bloqueado'])


class DuracionPredeterminadaTests(TestCase):
    def test_nueva_cita_ofrece_30_y_edicion_conserva_duracion(self):
        from .forms import AppointmentForm
        paciente = Patient.objects.create(nombre="Prueba", apellido="Duración")
        cita = Appointment.objects.create(paciente=paciente, fecha=date(2026, 10, 14), hora=time(19))
        self.assertEqual(cita.duracion, 30)
        self.assertEqual(AppointmentForm()["duracion"].value(), 30)
        cita.duracion = 15
        cita.save()
        self.assertEqual(AppointmentForm(instance=cita)["duracion"].value(), 15)

    def test_media_hora_reserva_dos_filas_y_libera_el_final(self):
        from .views import agenda_pro
        paciente = Patient.objects.create(nombre="Prueba", apellido="Intervalo")
        Appointment.objects.create(paciente=paciente, fecha=date(2026, 10, 15), hora=time(19))
        with patch("core.views.render", side_effect=lambda request, template, context: context):
            contexto = agenda_pro(RequestFactory().get("/", {"fecha": "2026-10-15"}))
        filas = {fila["hora"]: fila["celdas"][3] for fila in contexto["filas"]}
        self.assertEqual(filas[time(19)]["rowspan"], 2)
        self.assertTrue(filas[time(19, 15)]["ocultar"])
        self.assertFalse(filas[time(19, 30)]["bloqueado"])
        self.assertFalse(filas[time(19, 45)]["bloqueado"])


class PatientCIFormatTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.patient = Patient.objects.create(
            nombre="Paciente", apellido="Existente", ci="1.234.567-8", telefono="099123456",
        )

    def request(self, ci):
        from django.contrib.messages.storage.fallback import FallbackStorage
        request = self.factory.post("/pacientes/nuevo/", {
            "nombre": "Nuevo", "apellido": "Paciente", "ci": ci, "telefono": "099123456",
        })
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_reject_duplicate_in_normal_and_quick_create(self):
        from .views import patient_new, patient_quick_new
        for ci in ("12345678", "1.234.567-8", "1 234 567-8"):
            with patch("core.views.render", return_value="invalid"):
                self.assertEqual(patient_new(self.request(ci)), "invalid")
            self.assertEqual(patient_quick_new(self.request(ci)).status_code, 400)
        self.assertEqual(Patient.objects.count(), 1)

    def test_create_stores_searchable_digits_and_preserves_next(self):
        from .views import patient_new
        request = self.request("2.345.678-9")
        request.GET = {"next": "/agenda/"}
        response = patient_new(request)
        patient = Patient.objects.get(ci="23456789")
        self.assertEqual(response.url, f"/agenda/?paciente_id={patient.id}")

    def test_edit_preserves_historical_ci_and_rejects_other_patient_ci(self):
        from .views import patient_edit
        response = patient_edit(self.request("12345678"), self.patient.id)
        self.assertEqual(response.status_code, 302)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.ci, "1.234.567-8")
        other = Patient.objects.create(nombre="Otro", apellido="Paciente", ci="23456789")
        with patch("core.views.render", return_value="invalid"):
            self.assertEqual(patient_edit(self.request("2.345.678-9"), self.patient.id), "invalid")
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.ci, "1.234.567-8")
