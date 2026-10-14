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
