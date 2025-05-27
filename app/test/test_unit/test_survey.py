from django.test import TestCase
from django.contrib.auth import get_user_model
from app.models import Event, Ticket, Category, Venue, SatisfactionSurvey
from django.utils import timezone
from django.core.exceptions import ValidationError
import datetime
from django.urls import reverse

User = get_user_model()

class SatisfactionSurveyModelTest(TestCase):
    # Test: Se puede crear una encuesta válida con todos los campos requeridos
    def test_create_valid_survey(self):
        # Crear datos mínimos
        user = User.objects.create_user(username="testuser", email="testuser@example.com", password="testpass")
        organizer = User.objects.create_user(username="org", email="org@example.com", password="orgpass", is_organizer=True)
        venue = Venue.objects.create(name="Test Venue", address="Calle 1", city="Ciudad", capacity=100, contact="contacto@prueba.com")
        category = Category.objects.create(name="TestCat", description="desc")
        event = Event.objects.create(title="Test Event", description="desc", scheduled_at=timezone.now() + datetime.timedelta(days=1), organizer=organizer, venue=venue)
        event.categories.add(category)
        ticket = Ticket.objects.create(event=event, user=user, quantity=1, type='GENERAL')
        # Crear encuesta válida
        survey = SatisfactionSurvey.objects.create(event=event, ticket=ticket, user=user, rating=4, observations="Muy bueno")
        self.assertEqual(survey.rating, 4)
        self.assertEqual(survey.observations, "Muy bueno")
        self.assertEqual(survey.user, user)
        self.assertEqual(survey.event, event)
        self.assertEqual(survey.ticket, ticket)

    # Test: No se puede crear una encuesta sin calificación (rating)
    def test_cannot_create_survey_without_rating(self):
        user = User.objects.create_user(username="testuser2", email="testuser2@example.com", password="testpass")
        organizer = User.objects.create_user(username="org2", email="org2@example.com", password="orgpass", is_organizer=True)
        venue = Venue.objects.create(name="Test Venue2", address="Calle 2", city="Ciudad", capacity=100, contact="contacto@prueba.com")
        category = Category.objects.create(name="TestCat2", description="desc")
        event = Event.objects.create(title="Test Event2", description="desc", scheduled_at=timezone.now() + datetime.timedelta(days=1), organizer=organizer, venue=venue)
        event.categories.add(category)
        ticket = Ticket.objects.create(event=event, user=user, quantity=1, type='GENERAL')
        with self.assertRaises(Exception):
            SatisfactionSurvey.objects.create(event=event, ticket=ticket, user=user, observations="Sin rating")

    # Test: No se puede crear más de una encuesta para el mismo ticket y usuario
    def test_cannot_create_duplicate_survey_for_same_ticket_user(self):
        user = User.objects.create_user(username="testuser3", email="testuser3@example.com", password="testpass")
        organizer = User.objects.create_user(username="org3", email="org3@example.com", password="orgpass", is_organizer=True)
        venue = Venue.objects.create(name="Test Venue3", address="Calle 3", city="Ciudad", capacity=100, contact="contacto@prueba.com")
        category = Category.objects.create(name="TestCat3", description="desc")
        event = Event.objects.create(title="Test Event3", description="desc", scheduled_at=timezone.now() + datetime.timedelta(days=1), organizer=organizer, venue=venue)
        event.categories.add(category)
        ticket = Ticket.objects.create(event=event, user=user, quantity=1, type='GENERAL')
        SatisfactionSurvey.objects.create(event=event, ticket=ticket, user=user, rating=5)
        with self.assertRaises(Exception):
            SatisfactionSurvey.objects.create(event=event, ticket=ticket, user=user, rating=4)

    # Test: El campo observaciones es opcional al crear una encuesta
    def test_observations_field_is_optional(self):
        user = User.objects.create_user(username="testuser4", email="testuser4@example.com", password="testpass")
        organizer = User.objects.create_user(username="org4", email="org4@example.com", password="orgpass", is_organizer=True)
        venue = Venue.objects.create(name="Test Venue4", address="Calle 4", city="Ciudad", capacity=100, contact="contacto@prueba.com")
        category = Category.objects.create(name="TestCat4", description="desc")
        event = Event.objects.create(title="Test Event4", description="desc", scheduled_at=timezone.now() + datetime.timedelta(days=1), organizer=organizer, venue=venue)
        event.categories.add(category)
        ticket = Ticket.objects.create(event=event, user=user, quantity=1, type='GENERAL')
        survey = SatisfactionSurvey.objects.create(event=event, ticket=ticket, user=user, rating=3)
        self.assertEqual(survey.rating, 3)
        self.assertTrue(survey.observations is None or survey.observations == "")

    # Test: Un organizador no puede acceder al listado de encuestas (admin)
    def test_organizer_cannot_access_survey_list(self):
        self.client.login(username="org6", password="orgpass")
        response = self.client.get(reverse("survey_list"))
        # Debe redirigir o mostrar error de permiso
        self.assertNotEqual(response.status_code, 200)
        self.assertIn(response.status_code, [302, 403])
        # Opcional: verificar mensaje de error en el contenido si es 200
        if response.status_code == 200:
            self.assertIn(b'No tienes permiso', response.content) 