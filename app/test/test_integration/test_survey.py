from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from app.models import Event, Ticket, Category, Venue, SatisfactionSurvey
from django.utils import timezone
import datetime

User = get_user_model()

class SatisfactionSurveyIntegrationTest(TestCase):
    def setUp(self):
        # Crear usuario y datos mínimos
        self.user = User.objects.create_user(username="testuser", email="testuser@example.com", password="testpass")
        self.organizer = User.objects.create_user(username="org", email="org@example.com", password="orgpass", is_organizer=True)
        self.venue = Venue.objects.create(name="Test Venue", address="Calle 1", city="Ciudad", capacity=100, contact="contacto@prueba.com")
        self.category = Category.objects.create(name="TestCat", description="desc")
        self.event = Event.objects.create(title="Test Event", description="desc", scheduled_at=timezone.now() + datetime.timedelta(days=1), organizer=self.organizer, venue=self.venue)
        self.event.categories.add(self.category)
        self.ticket = Ticket.objects.create(event=self.event, user=self.user, quantity=1, type='GENERAL')

    def test_user_can_create_survey_for_own_ticket(self):
        """
        Test de integración: Un usuario puede crear una encuesta de satisfacción para un ticket propio recién comprado.
        """
        self.client.login(username="testuser", password="testpass")
        # Simular que el usuario acaba de comprar el ticket (como hace la vista)
        session = self.client.session
        session['last_ticket_id'] = self.ticket.id
        session.save()
        url = reverse('survey_create', kwargs={'ticket_id': self.ticket.id})
        data = {
            'rating': 5,
            'observations': '¡Excelente experiencia!'
        }
        response = self.client.post(url, data, follow=True)
        # Debe redirigir a la lista de tickets
        self.assertRedirects(response, reverse('ticket_list'))
        # La encuesta debe haberse creado
        survey = SatisfactionSurvey.objects.get(ticket=self.ticket)
        self.assertEqual(survey.rating, 5)
        self.assertEqual(survey.observations, '¡Excelente experiencia!')
        self.assertEqual(survey.user, self.user)
        self.assertEqual(survey.event, self.event)

    def test_user_cannot_create_duplicate_survey_for_same_ticket(self):
        """
        Test de integración: Un usuario no puede crear más de una encuesta para el mismo ticket (unicidad).
        """
        self.client.login(username="testuser", password="testpass")
        # Simular compra
        session = self.client.session
        session['last_ticket_id'] = self.ticket.id
        session.save()
        url = reverse('survey_create', kwargs={'ticket_id': self.ticket.id})
        data = {
            'rating': 4,
            'observations': 'Primera respuesta'
        }
        # Primer envío: debe funcionar
        response1 = self.client.post(url, data, follow=True)
        self.assertRedirects(response1, reverse('ticket_list'))
        self.assertEqual(SatisfactionSurvey.objects.filter(ticket=self.ticket, user=self.user).count(), 1)
        # Simular que el usuario intenta enviar otra encuesta para el mismo ticket
        session = self.client.session
        session['last_ticket_id'] = self.ticket.id
        session.save()
        data2 = {
            'rating': 5,
            'observations': 'Intento duplicado'
        }
        response2 = self.client.post(url, data2, follow=True)
        # Debe redirigir o mostrar error, pero no crear otra encuesta
        self.assertEqual(SatisfactionSurvey.objects.filter(ticket=self.ticket, user=self.user).count(), 1)
        # Puede redirigir a event_detail o ticket_list, o mostrar mensaje
        self.assertIn(response2.status_code, [200, 302])

    def test_cannot_create_survey_without_rating(self):
        """
        Test de integración: No se puede crear una encuesta sin calificación (rating requerido).
        """
        self.client.login(username="testuser", password="testpass")
        # Simular compra
        session = self.client.session
        session['last_ticket_id'] = self.ticket.id
        session.save()
        url = reverse('survey_create', kwargs={'ticket_id': self.ticket.id})
        data = {
            # 'rating' omitido
            'observations': 'Olvidé poner rating'
        }
        response = self.client.post(url, data)
        # Debe quedarse en la misma página (no redirigir)
        self.assertEqual(response.status_code, 200)
        # No debe haberse creado la encuesta
        self.assertFalse(SatisfactionSurvey.objects.filter(ticket=self.ticket, user=self.user).exists())
        # El formulario debe mostrar un error relacionado con rating
        self.assertIn(b'campo', response.content.lower())

    def test_observations_field_is_optional(self):
        """
        Test de integración: El campo observaciones es opcional al crear una encuesta.
        """
        self.client.login(username="testuser", password="testpass")
        # Simular compra
        session = self.client.session
        session['last_ticket_id'] = self.ticket.id
        session.save()
        url = reverse('survey_create', kwargs={'ticket_id': self.ticket.id})
        data = {
            'rating': 4
            # 'observations' omitido
        }
        response = self.client.post(url, data, follow=True)
        # Debe redirigir a la lista de tickets
        self.assertRedirects(response, reverse('ticket_list'))
        # La encuesta debe haberse creado y el campo observations debe estar vacío o None
        survey = SatisfactionSurvey.objects.get(ticket=self.ticket)
        self.assertEqual(survey.rating, 4)
        self.assertTrue(survey.observations is None or survey.observations == "")

    def test_organizer_cannot_create_survey(self):
        """
        Test de integración: Un organizador no puede crear una encuesta de satisfacción (ni forzando el acceso).
        """
        self.client.login(username="org", password="orgpass")
        # El organizador compra un ticket (caso forzado)
        ticket = Ticket.objects.create(event=self.event, user=self.organizer, quantity=1, type='GENERAL')
        # Simular compra
        session = self.client.session
        session['last_ticket_id'] = ticket.id
        session.save()
        url = reverse('survey_create', kwargs={'ticket_id': ticket.id})
        data = {
            'rating': 5,
            'observations': 'Intento de organizador'
        }
        response = self.client.post(url, data, follow=True)
        # No debe crearse la encuesta
        self.assertFalse(SatisfactionSurvey.objects.filter(ticket=ticket, user=self.organizer).exists())
        # Debe redirigir o mostrar error
        self.assertIn(response.status_code, [200, 302, 403])

    def test_user_cannot_create_survey_for_other_users_ticket(self):
        """
        Test de integración: Un usuario no puede crear una encuesta para un ticket que no le pertenece.
        """
        # Crear otro usuario y ticket
        other_user = User.objects.create_user(username="otheruser", email="otheruser@example.com", password="otherpass")
        ticket = Ticket.objects.create(event=self.event, user=other_user, quantity=1, type='GENERAL')
        self.client.login(username="testuser", password="testpass")
        # Simular compra (aunque no es su ticket)
        session = self.client.session
        session['last_ticket_id'] = ticket.id
        session.save()
        url = reverse('survey_create', kwargs={'ticket_id': ticket.id})
        data = {
            'rating': 5,
            'observations': 'Intento para otro usuario'
        }
        response = self.client.post(url, data, follow=True)
        # No debe crearse la encuesta
        self.assertFalse(SatisfactionSurvey.objects.filter(ticket=ticket, user=self.user).exists())
        # Debe redirigir o mostrar error
        self.assertIn(response.status_code, [200, 302, 403])

    def test_only_admin_can_access_survey_list(self):
        """
        Test de integración: Solo el admin puede acceder al listado de encuestas (survey_list).
        """
        url = reverse('survey_list')
        # Usuario regular
        self.client.login(username="testuser", password="testpass")
        response = self.client.get(url)
        self.assertIn(response.status_code, [302, 403])
        self.client.logout()
        # Organizador
        self.client.login(username="org", password="orgpass")
        response = self.client.get(url)
        self.assertIn(response.status_code, [302, 403])
        self.client.logout()
        # Admin
        admin = User.objects.create_superuser(username="admin", email="admin@example.com", password="adminpass")
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
