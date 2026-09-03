from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from .views import _armar_cita_agenda_rapida, _combinar_pagos_citas


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
