from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .debt_categories import categoria_cita
from .models import Appointment, Patient, Budget


class CategoriasDeudaTests(SimpleTestCase):
    def cita(self, motivo, categoria='auto', procedimientos=()):
        return SimpleNamespace(motivo=motivo, deuda_categoria=categoria,
                               procedimientos=SimpleNamespace(all=lambda: [SimpleNamespace(nombre=p) for p in procedimientos]))

    def test_detecta_tildes_plurales_y_puente(self):
        for texto, esperado in [('Prótesis', 'protesis'), ('Endodoncia', 'endodoncia'),
                               ('Coronas', 'corona'), ('Puente fijo', 'protesis'),
                               ('Control', 'general')]:
            self.assertEqual(categoria_cita(self.cita(texto)), esperado)

    def test_motivos_mixtos_requieren_categoria_y_override_resuelve_control(self):
        self.assertEqual(categoria_cita(self.cita('Corona', procedimientos=['Corona', 'Resina'])), 'revisar')
        self.assertEqual(categoria_cita(self.cita('Control', 'endodoncia')), 'endodoncia')


class DeudasTratamientosTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('deudas_tratamientos')
        self.client.force_login(self.user)
        self.paciente = Patient.objects.create(nombre='Paciente', apellido='Prueba')
        self.url = reverse('deudores_general')

    def cita(self, motivo, monto, dia, categoria='auto', estado='asistio'):
        return Appointment.objects.create(paciente=self.paciente, fecha=date(2026, 10, dia),
                                           hora=time(11), motivo=motivo, monto_total=monto,
                                           deuda_categoria=categoria, estado=estado)

    def consultar(self, pagado, pagos=None, params=None):
        with patch('core.views.obtener_resumen_cobros_pacientes_bulk', return_value={
            self.paciente.pk: {'ok': True, 'total_pagado': Decimal(str(pagado))},
        }), patch('core.debt_views.pagos_por_sesion', return_value=pagos or {}):
            return self.client.get(self.url, params or {})

    def test_tres_sesiones_un_cargo_y_pagos_en_citas_posteriores(self):
        primera = self.cita('Endodoncia', 6000, 1)
        segunda = self.cita('Endodoncia', 0, 8)
        tercera = self.cita('Control', 0, 15, categoria='endodoncia')
        r = self.consultar(3500, {primera.pk: 0, segunda.pk: 2000, tercera.pk: 1500})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total_general'], 2500)
        componente = r.context['deudores'][0]['componentes'][0]
        self.assertEqual(componente['categoria'], 'endodoncia')
        self.assertEqual(componente['total'], 6000)
        self.assertEqual(componente['abonado'], 3500)
        self.assertEqual(componente['saldo'], 2500)
        self.assertEqual(sum(Appointment.objects.values_list('monto_total', flat=True)), 6000)

    def test_separa_tratamientos_y_cuenta_cada_pago_una_vez(self):
        endo = self.cita('Endodoncia', 6000, 1)
        corona = self.cita('Corona', 7500, 2)
        control = self.cita('Control', 0, 9, categoria='endodoncia')
        limpieza = self.cita('Limpieza', 900, 10)
        pagos = {endo.pk: 2000, corona.pk: 1000, control.pk: 1500, limpieza.pk: 900}
        r = self.consultar(5400, pagos)
        componentes = r.context['deudores'][0]['componentes']
        self.assertEqual({c['categoria']: c['saldo'] for c in componentes}, {'endodoncia': 2500, 'corona': 6500})
        self.assertEqual(sum(c['saldo'] for c in componentes), r.context['total_general'])
        filtro = self.consultar(5400, pagos, {'categoria': 'endodoncia', 'q': 'Prueba'})
        self.assertEqual(filtro.context['total_general'], 9000)
        self.assertEqual(filtro.context['total_seccion'], 2500)
        self.assertEqual(len(filtro.context['deudores'][0]['componentes']), 1)

    def test_saldo_no_asignado_no_se_descuenta_dos_veces(self):
        endo = self.cita('Endodoncia', 6000, 1)
        corona = self.cita('Corona', 7500, 2)
        r = self.consultar(4000, {endo.pk: 1000, corona.pk: 1000})
        d = r.context['deudores'][0]
        self.assertEqual(d['componentes'][0]['categoria'], 'revisar')
        self.assertEqual(d['componentes'][0]['saldo'], 9500)
        self.assertEqual(r.context['total_general'], 9500)

    def test_api_de_sesiones_incompleta_no_fabrica_saldos_por_tratamiento(self):
        self.cita('Endodoncia', 6000, 1)
        self.cita('Corona', 7500, 2)
        with patch('core.views.obtener_resumen_cobros_pacientes_bulk', return_value={
            self.paciente.pk: {'ok': True, 'total_pagado': 4000},
        }), patch('core.debt_views.pagos_por_sesion', return_value=None):
            r = self.client.get(self.url)
        self.assertEqual(r.context['deudores'][0]['componentes'][0]['categoria'], 'revisar')
        self.assertEqual(r.context['total_general'], 9500)

    def test_presupuesto_del_mismo_tratamiento_no_suma_de_nuevo(self):
        self.cita('Prótesis', 21000, 1)
        Budget.objects.create(paciente=self.paciente, estado='confirmado', total=21000)
        r = self.consultar(10000)
        self.assertEqual(r.context['total_general'], 11000)
        self.assertEqual(r.context['total_seccion'], 11000)
        self.assertEqual(r.context['deudores'][0]['componentes'][0]['categoria'], 'protesis')

    def test_pago_total_y_saldo_a_favor_excluidos(self):
        self.cita('Corona', 7500, 1)
        for pagado in (7500, 8000):
            r = self.consultar(pagado)
            self.assertEqual(r.context['deudores'], [])
            self.assertEqual(r.context['total_general'], 0)

    def test_categoria_archivada_no_se_suma_al_total_activo(self):
        self.cita('Prótesis', 21000, 1)
        self.paciente.archivado_deudores = True
        self.paciente.save()
        r = self.consultar(10000, params={'estado': 'archivados', 'categoria': 'protesis'})
        self.assertEqual(r.context['total_general'], 0)
        self.assertEqual(r.context['total_seccion'], 11000)

    def test_asignar_control_modifica_solo_categoria_y_conserva_cita_del_pago(self):
        cita = self.cita('Control', 0, 8)
        url = reverse('deudor_sesiones', args=[self.paciente.pk])
        r = self.client.post(url, {'cita_id': cita.pk, 'categoria': 'endodoncia', 'next': self.url + '?categoria=endodoncia'})
        self.assertEqual(r.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.deuda_categoria, 'endodoncia')
        self.assertEqual(cita.fecha, date(2026, 10, 8))
        self.assertEqual(cita.monto_total, 0)
        self.assertEqual(cita.motivo, 'Control')
        self.assertFalse(cita.pagado)
        with patch('core.debt_views.pagos_por_sesion', return_value={cita.pk: Decimal('1500')}):
            r = self.client.get(url)
        self.assertContains(r, 'Registrar pago en esta cita')
        self.assertContains(r, reverse('cobros_nuevo_desde_cita', args=[cita.pk]))
        self.assertEqual(r.context['filas'][0]['pagado'], 1500)

    def test_rechaza_categoria_invalida_y_cita_de_otro_paciente(self):
        cita = self.cita('Control', 0, 8)
        url = reverse('deudor_sesiones', args=[self.paciente.pk])
        self.assertEqual(self.client.post(url, {'cita_id': cita.pk, 'categoria': 'no-existe'}).status_code, 400)
        self.assertEqual(self.client.post(url, {'cita_id': 'abc', 'categoria': 'general'}).status_code, 400)
        otro = Patient.objects.create(nombre='Otro', apellido='Paciente')
        otra_cita = Appointment.objects.create(paciente=otro, fecha=date(2026, 10, 9), hora=time(11))
        self.assertEqual(self.client.post(url, {'cita_id': otra_cita.pk, 'categoria': 'corona'}).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_formulario_compatible_con_citas_anteriores_y_proteccion_csrf(self):
        from .forms import AppointmentForm
        from .models import Procedure
        from django.test import Client
        cita = self.cita('Control', 0, 8, categoria='endodoncia')
        procedimiento = Procedure.objects.create(nombre='Control')
        # Un cliente anterior que no envía el campo nuevo conserva la categoría.
        datos = {'paciente': self.paciente.pk, 'fecha': '2026-10-08', 'hora': '11:00',
                 'duracion': 30, 'odontologo': cita.odontologo_id,
                 'procedimientos': [procedimiento.pk], 'estado': 'asistio', 'monto_total': 0}
        form = AppointmentForm(datos, instance=cita)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['deuda_categoria'], 'endodoncia')
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.user)
        url = reverse('deudor_sesiones', args=[self.paciente.pk])
        self.assertEqual(cliente.post(url, {'cita_id': cita.pk, 'categoria': 'general'}).status_code, 403)

    @override_settings(DEBUG=False)
    def test_pagos_por_sesion_rechaza_faltantes_y_consulta_lotes(self):
        from .debt_views import pagos_por_sesion
        def responder(ids):
            self.assertLessEqual(len(ids), 100)
            return {pk: {'total_pagado': '100'} for pk in ids}
        with patch('core.views._obtener_pagos_cobros_citas_bulk', side_effect=responder) as obtener:
            r = pagos_por_sesion(range(1, 252))
        self.assertEqual(len(r), 251)
        self.assertEqual(obtener.call_count, 3)
        with patch('core.views._obtener_pagos_cobros_citas_bulk', return_value={}):
            self.assertIsNone(pagos_por_sesion([1]))
