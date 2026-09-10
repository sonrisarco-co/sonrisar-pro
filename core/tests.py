from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, RequestFactory, override_settings

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

        cita_agenda = _armar_cita_agenda_rapida(cita, contexto)

        self.assertTrue(cita_agenda["tiene_saldo_a_favor"])
        self.assertEqual(cita_agenda["saldo_a_favor"], Decimal("100"))
