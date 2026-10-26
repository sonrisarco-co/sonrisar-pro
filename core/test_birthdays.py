from datetime import date
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .birthdays import birthday_rows
from .models import Patient, BirthdayGreeting


class BirthdayTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='birthday-test')
        self.client.force_login(self.user)
        self.patient = Patient.objects.create(nombre='Ana', apellido='Prueba', fecha_nacimiento=date(1990, 10, 26), telefono='099123456')

    @patch('core.birthdays.timezone.localdate', return_value=date(2026, 10, 26))
    def test_message_and_manual_confirmation_are_separate_and_idempotent(self, _):
        row = birthday_rows(10, 26)[0]
        self.assertIn('https://wa.me/59899123456?', row['whatsapp_url'])
        self.assertEqual(row['age'], 36)
        self.assertContains(self.client.get(reverse('birthdays')), 'Ana')
        self.assertEqual(BirthdayGreeting.objects.count(), 0)
        url = reverse('birthday_mark', args=[self.patient.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        for _ in range(2):
            response = self.client.post(url, {'next': 'https://example.org/'})
            self.assertRedirects(response, reverse('birthdays'))
        self.assertEqual(BirthdayGreeting.objects.count(), 1)
        self.assertEqual(BirthdayGreeting.objects.get().marcado_por, self.user)
        self.assertIsNotNone(birthday_rows(10)[0]['greeting'])

    @patch('core.birthdays.timezone.localdate', return_value=date(2026, 10, 25))
    def test_future_birthday_cannot_be_marked(self, _):
        self.client.post(reverse('birthday_mark', args=[self.patient.pk]))
        self.assertFalse(BirthdayGreeting.objects.exists())

    @patch('core.birthdays.timezone.localdate', return_value=date(2027, 10, 26))
    def test_new_year_pending_and_invalid_phone(self, _):
        BirthdayGreeting.objects.create(paciente=self.patient, year=2026)
        self.patient.telefono = ''
        self.patient.save()
        row = birthday_rows(10)[0]
        self.assertIsNone(row['greeting'])
        self.assertEqual(row['whatsapp_url'], '')
        self.assertEqual(birthday_rows(11), [])

    def test_authentication_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('birthdays')).status_code, 302)
