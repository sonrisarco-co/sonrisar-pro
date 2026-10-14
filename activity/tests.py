from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.test import RequestFactory
from core.models import Patient, ClinicalRecord
from .models import Activity
from .middleware import ActivityMiddleware
class ActivityTests(TestCase):
    def setUp(self):
        self.geisha = get_user_model().objects.create_user('geisha', password='test-password')
        self.andres = get_user_model().objects.create_user('andres', password='test-password')
        self.andres.groups.add(Group.objects.create(name='Responsables Sonrisar'))
        self.patient = Patient.objects.create(nombre='Ana', apellido='Prueba', ci='123', telefono='099')
    def request(self, user, action):
        req = RequestFactory().post('/')
        req.user = user
        def view(req):
            action()
            return HttpResponse('ok')
        return ActivityMiddleware(view)(req)
    def test_login_required_and_activity_restricted(self):
        self.assertEqual(self.client.get('/').status_code,302)
        self.client.force_login(self.geisha)
        self.assertEqual(self.client.get('/actividad/').status_code,403)
        self.client.force_login(self.andres)
        self.assertEqual(self.client.get('/actividad/').status_code,200)
    def test_geisha_can_edit_and_audit_keeps_before_after(self):
        def change():
            self.patient.telefono='098'; self.patient.save()
        self.request(self.geisha,change)
        entry=Activity.objects.filter(username='geisha', action='Modificó').get()
        self.assertEqual(entry.changes['telefono'],{'antes':'099','después':'098'})
    def test_geisha_cannot_delete_patient_direct_or_cascade(self):
        self.client.force_login(self.geisha)
        self.assertEqual(self.client.post(f'/pacientes/eliminar/{self.patient.pk}/').status_code,403)
        with self.assertRaises(PermissionDenied):
            self.request(self.geisha,lambda: Patient.objects.filter(pk=self.patient.pk).delete())
        self.assertTrue(Patient.objects.filter(pk=self.patient.pk).exists())
    def test_geisha_cannot_delete_clinical_record(self):
        record=ClinicalRecord.objects.create(paciente=self.patient)
        with self.assertRaises(PermissionDenied):
            self.request(self.geisha,record.delete)
        self.assertTrue(ClinicalRecord.objects.filter(pk=record.pk).exists())
    def test_manager_delete_keeps_history(self):
        pk=self.patient.pk
        self.request(self.andres,self.patient.delete)
        self.assertTrue(Activity.objects.filter(username='andres',action='Eliminó',object_id=str(pk)).exists())
    def test_rollback_does_not_leave_audit(self):
        count=Activity.objects.count()
        def fail():
            self.patient.telefono='000';self.patient.save();raise ValueError('failure')
        with self.assertRaises(ValueError): self.request(self.geisha,fail)
        self.assertEqual(Activity.objects.count(),count)

    def test_geisha_can_delete_appointment(self):
        from core.models import Appointment
        from datetime import date, time
        appointment=Appointment.objects.create(paciente=self.patient, fecha=date.today(), hora=time(10))
        pk=appointment.pk
        self.request(self.geisha,appointment.delete)
        self.assertFalse(Appointment.objects.filter(pk=pk).exists())
        self.assertTrue(Activity.objects.filter(username='geisha',action='Eliminó',section='Agenda').exists())
    def test_account_setup_creates_exact_roles(self):
        from django.core.management import call_command
        from unittest.mock import patch
        get_user_model().objects.all().delete()
        with patch('activity.management.commands.configurar_usuarios.getpass', return_value='ClaveIndividualFuerte927!'):
            call_command('configurar_usuarios')
        for name in ('andres','rodrigo'):
            user=get_user_model().objects.get(username=name)
            self.assertTrue(user.groups.filter(name='Responsables Sonrisar').exists())
            self.assertFalse(user.is_superuser)
        geisha=get_user_model().objects.get(username='geisha')
        self.assertFalse(geisha.is_staff)
        self.assertFalse(geisha.groups.exists())

class AgendaLiveTests(TestCase):
    def setUp(self):
        from django.test import Client
        self.first = get_user_model().objects.create_user('operador1')
        self.second = get_user_model().objects.create_user('operador2')
        self.client.force_login(self.first)
        self.other = Client()
        self.other.force_login(self.second)
        self.url = '/actividad/agenda/cambios/'
    def test_endpoint_requires_login_and_does_not_expose_records(self):
        from django.test import Client
        self.assertEqual(Client().get(self.url).status_code,302)
        response=self.other.get(self.url)
        self.assertEqual(set(response.json()), {'revision'})
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(self.other.post(self.url).status_code,405)
    def test_other_user_sees_changed_revision_after_a_save(self):
        from core.models import Appointment
        from datetime import date, time
        from django.urls import reverse
        patient=Patient.objects.create(nombre='Prueba', apellido='En vivo')
        appointment=Appointment.objects.create(paciente=patient, fecha=date(2026,10,14), hora=time(10))
        before=self.other.get(self.url).json()['revision']
        response=self.client.post(reverse('appointment_confirm', args=[appointment.pk]), {'estado':'confirmado'})
        self.assertEqual(response.status_code,200)
        self.assertNotEqual(before,self.other.get(self.url).json()['revision'])
        self.assertTrue(Activity.objects.filter(username='operador1',action='Modificó',section='Agenda').exists())
    def test_login_and_inventory_do_not_refresh_agenda(self):
        from .live import agenda_revision
        before=agenda_revision()
        Activity.objects.create(username='operador1', action='Ingresó', section='Acceso')
        Activity.objects.create(username='operador1', action='Modificó', section='Inventario')
        self.assertEqual(before,agenda_revision())
    def test_late_commit_with_lower_id_is_detected(self):
        from .live import agenda_revision
        highest=(Activity.objects.order_by('-id').values_list('id',flat=True).first() or 0)+10
        Activity.objects.create(id=highest,username='operador1',action='Modificó',section='Agenda')
        before=agenda_revision()
        Activity.objects.create(id=highest-1,username='operador2',action='Modificó',section='Agenda')
        self.assertNotEqual(before,agenda_revision())
    def test_polling_does_not_generate_activity(self):
        before=Activity.objects.count()
        for _ in range(3): self.other.get(self.url)
        self.assertEqual(before,Activity.objects.count())
    def test_day_page_contains_initial_revision_and_live_script(self):
        response=self.client.get('/agenda/dia/14/10/2026/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'data-revision="0:0"')
        self.assertContains(response,'core/js/agenda_live.js')

class ActivityReturnTests(TestCase):
    def setUp(self):
        user=get_user_model().objects.create_user('responsable')
        group,_=Group.objects.get_or_create(name='Responsables Sonrisar')
        user.groups.add(group)
        self.client.force_login(user)
    def test_preserves_origin_through_filters_and_pagination(self):
        from django.utils import timezone
        target='/agenda/dia/14/10/2026/?almanaque_mes=2026-09-01#cita-9'
        Activity.objects.bulk_create([Activity(username='responsable',action='Modificó',section='Agenda') for _ in range(51)])
        response=self.client.get('/actividad/',{'volver':target,'fecha':timezone.localdate().isoformat(),'usuario':'responsable'})
        self.assertEqual(response.context['sonrisar_activity_return_url'],target)
        self.assertContains(response,'name="volver"')
        self.assertContains(response,'page=2')
        response=self.client.get('/actividad/',{'volver':target,'page':'2','usuario':'responsable'})
        self.assertEqual(response.context['sonrisar_activity_return_url'],target)
        self.assertContains(response,'href="/agenda/dia/14/10/2026/?almanaque_mes=2026-09-01#cita-9"')
    def test_unsafe_or_recursive_return_goes_home(self):
        from django.urls import reverse
        for target in ['https://example.com/', '//example.com/', '/\\example.com/', '/actividad/?page=2', 'javascript:alert(1)', '']:
            with self.subTest(target=target):
                response=self.client.get('/actividad/',{'volver':target})
                self.assertEqual(response.context['sonrisar_activity_return_url'],reverse('home'))
    def test_header_passes_current_page_as_origin(self):
        response=self.client.get('/agenda/dia/14/10/2026/?almanaque_mes=2026-09-01')
        self.assertContains(response,'/actividad/?volver=/agenda/dia/14/10/2026/%3Falmanaque_mes%3D2026-09-01')
    def test_login_still_authenticates_with_styled_form(self):
        self.client.logout()
        user=get_user_model().objects.get(username='responsable')
        user.set_password('StrongIndividual493!');user.save()
        response=self.client.get('/cuentas/ingresar/')
        self.assertContains(response,'name="username"')
        self.assertContains(response,'name="password"')
        response=self.client.post('/cuentas/ingresar/',{'username':'responsable','password':'StrongIndividual493!','next':'/actividad/'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(response['Location'],'/actividad/')

class PatientsLiveTests(TestCase):
    def setUp(self):
        from django.test import Client
        self.first=get_user_model().objects.create_user('recepcion')
        self.second=get_user_model().objects.create_user('odontologo')
        self.client.force_login(self.first)
        self.other=Client();self.other.force_login(self.second)
        self.url='/actividad/pacientes/cambios/'
    def test_new_patient_and_edit_are_detected_by_other_user(self):
        before=self.other.get(self.url).json()['revision']
        data={'nombre':'Paciente','apellido':'Prueba','ci':'CI-POLL','telefono':'099123456'}
        response=self.client.post('/pacientes/nuevo/',data)
        self.assertEqual(response.status_code,302)
        after=self.other.get(self.url).json()['revision']
        self.assertNotEqual(before,after)
        patient=Patient.objects.get(ci='CI-POLL')
        data['telefono']='098654321'
        response=self.client.post(f'/pacientes/editar/{patient.pk}/',data)
        self.assertEqual(response.status_code,302)
        self.assertNotEqual(after,self.other.get(self.url).json()['revision'])
        self.assertTrue(Activity.objects.filter(username='recepcion',section='Pacientes',action='Modificó').exists())
    def test_endpoint_is_authenticated_read_only_and_does_not_expose_patient_data(self):
        from django.test import Client
        self.assertEqual(Client().get(self.url).status_code,302)
        self.assertEqual(self.other.post(self.url).status_code,405)
        response=self.other.get(self.url)
        self.assertEqual(set(response.json()),{'revision'})
        self.assertIn('no-store',response['Cache-Control'])
    def test_unrelated_activity_is_ignored_but_appointments_affect_inactive_count(self):
        from .live import patients_revision
        before=patients_revision()
        Activity.objects.create(username='recepcion',action='Modificó',section='Inventario')
        self.assertEqual(before,patients_revision())
        Activity.objects.create(username='odontologo',action='Modificó',section='Agenda')
        self.assertNotEqual(before,patients_revision())
    def test_list_has_baseline_row_anchors_and_preserves_applied_filter(self):
        from .live import patients_revision
        patient=Patient.objects.create(nombre='Paciente',apellido='Prueba',ci='ROW-POLL')
        response=self.other.get('/pacientes/?q=Paciente&page=1')
        self.assertContains(response, f'id="patient-{patient.pk}"')
        self.assertContains(response, f'data-revision="{patients_revision()}"')
        self.assertContains(response,'value="Paciente"')
        self.assertContains(response,'core/js/list_live.js')
        edit=self.other.get(f'/pacientes/editar/{patient.pk}/')
        self.assertContains(edit,'data-manual="true"')
    def test_polling_does_not_add_activity(self):
        before=Activity.objects.count()
        for _ in range(3): self.other.get(self.url)
        self.assertEqual(before,Activity.objects.count())


class SystemLiveTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('equipo')
        self.client.force_login(self.user)
        self.url='/actividad/sistema/cambios/'
    def test_all_scopes_are_read_only_private_and_do_not_disclose_records(self):
        from .system_live import SCOPES
        for scope in SCOPES:
            if scope=='actividad': continue
            response=self.client.get(self.url,{'seccion':scope})
            self.assertEqual(response.status_code,200,scope)
            self.assertEqual(set(response.json()),{'revision'})
            self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(self.client.post(self.url,{'seccion':'inventario'}).status_code,405)
        self.assertEqual(self.client.get(self.url,{'seccion':'bad'}).status_code,400)
    def test_activity_scope_keeps_manager_restriction(self):
        self.assertEqual(self.client.get(self.url,{'seccion':'actividad'}).status_code,403)
        group,_=Group.objects.get_or_create(name='Responsables Sonrisar')
        self.user.groups.add(group)
        self.assertEqual(self.client.get(self.url,{'seccion':'actividad'}).status_code,200)
    def test_inventory_prosthesis_clinical_budget_image_and_odontogram_changes_detected(self):
        from .system_live import revision
        for scope,section in [('inventario','Movimientos de inventario'),('protesis','Laboratorio'),('clinica','Historia clínica'),('presupuestos','Ajustes de presupuesto'),('imagenes','Rayos X / Fotografías'),('odontograma','Odontograma')]:
            before=revision(scope)
            Activity.objects.create(username='otro_usuario',action='Modificó',section=section)
            self.assertNotEqual(before,revision(scope),scope)
    def test_non_activity_screens_ignore_login_noise(self):
        from .system_live import revision
        before=revision('general');audit=revision('actividad')
        Activity.objects.create(username='otro_usuario',action='Ingresó',section='Acceso')
        self.assertEqual(before,revision('general'))
        self.assertNotEqual(audit,revision('actividad'))
    def test_profiles_cover_routes_and_never_enable_actions_or_downloads(self):
        from .system_live import VIEWS
        from django.urls import get_resolver
        def names(patterns):
            found=set()
            for pattern in patterns:
                if hasattr(pattern,'url_patterns'): found.update(names(pattern.url_patterns))
                elif pattern.name: found.add(pattern.name)
            return found
        self.assertFalse(set(VIEWS)-names(get_resolver().url_patterns))
        for name in ['appointment_delete','budget_print','confirmar_envio','inventory_adjust_stock','logout','system_updates','agenda_day','patient_list']:
            self.assertNotIn(name,VIEWS)
        for name in ['clinical_record_new','clinical_record_edit','odontograma_paciente','odontograma_profesional','budget_edit','patient_edit','rayos_x_new']:
            self.assertTrue(VIEWS[name]['manual'])
    def test_multiple_lists_receive_automatic_profile_without_duplicate_scripts(self):
        for path in ['/inventario/','/inventario/lista-compras/','/protesis/','/presupuestos/','/pagos/','/historia/','/pacientes/inactivos/']:
            response=self.client.get(path)
            self.assertEqual(response.status_code,200,path)
            self.assertContains(response,'sonrisar-system-live-status',count=1)
            self.assertContains(response,'core/js/list_live.js',count=1)
            self.assertContains(response,'data-manual="false"')
        response=self.client.get('/pacientes/')
        self.assertNotContains(response,'sonrisar-system-live-status')
        self.assertContains(response,'core/js/list_live.js',count=1)
    def test_clinical_odontogram_and_patient_forms_are_manual_only(self):
        patient=Patient.objects.create(nombre='Prueba',apellido='Protección',ci='PROTECT')
        for path in [f'/pacientes/editar/{patient.pk}/',f'/historia/registro/nuevo/{patient.pk}/',f'/pacientes/{patient.pk}/odontograma/',f'/pacientes/{patient.pk}/odontograma-profesional/']:
            response=self.client.get(path)
            self.assertEqual(response.status_code,200,path)
            self.assertContains(response,'data-manual="true"')
    def test_financial_views_use_periodic_external_refresh(self):
        from .system_live import prepare
        from django.test import RequestFactory
        request=RequestFactory().get('/');request.user=self.user
        prepare(request,'patient_finances')
        self.assertEqual(request.sonrisar_live['periodic'],60000)
        prepare(request,'inventory_list')
        self.assertEqual(request.sonrisar_live['periodic'],0)
    def test_polling_has_no_audit_side_effect(self):
        before=Activity.objects.count()
        for _ in range(3):self.client.get(self.url,{'seccion':'protesis'})
        self.assertEqual(before,Activity.objects.count())
    def test_stock_adjustment_from_another_session_is_detected(self):
        from core.models import Inventory
        from django.test import Client
        product=Inventory.objects.create(nombre='Producto de prueba',stock=3)
        other=Client();other.force_login(get_user_model().objects.create_user('stock_otro'))
        before=self.client.get(self.url,{'seccion':'inventario'}).json()['revision']
        response=other.post(f'/inventario/stock/{product.pk}/sumar/')
        self.assertEqual(response.status_code,302)
        product.refresh_from_db();self.assertEqual(product.stock,4)
        self.assertNotEqual(before,self.client.get(self.url,{'seccion':'inventario'}).json()['revision'])
    def test_prosthesis_status_from_another_session_is_detected(self):
        from core.models import Prosthesis
        from django.test import Client
        patient=Patient.objects.create(nombre='Prueba',apellido='Prótesis',ci='PROS-POLL')
        work=Prosthesis.objects.create(paciente=patient)
        other=Client();other.force_login(get_user_model().objects.create_user('laboratorio_otro'))
        before=self.client.get(self.url,{'seccion':'protesis'}).json()['revision']
        response=other.post(f'/protesis/{work.pk}/cambiar-estado/',{'estado':'prueba'})
        self.assertEqual(response.status_code,302)
        self.assertNotEqual(before,self.client.get(self.url,{'seccion':'protesis'}).json()['revision'])
