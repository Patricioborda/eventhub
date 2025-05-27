from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime
from playwright.sync_api import expect
from app.test.test_e2e.base import BaseE2ETest
from app.models import Event, Category, Venue, Ticket, SatisfactionSurvey

User = get_user_model()

class SurveyBaseTest(BaseE2ETest):
    """Clase base para tests de encuestas de satisfacción"""

    def setUp(self):
        super().setUp()
        # Crear usuarios
        self.user = User.objects.create_user(
            username="usuario",
            email="usuario@example.com",
            password="password123"
        )
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="org123",
            is_organizer=True
        )
        # Crear venue y categoría
        self.venue = Venue.objects.create(
            name="Centro Cultural",
            address="Calle Falsa 123",
            city="La Plata",
            capacity=300,
            contact="contacto@cultura.com"
        )
        self.category = Category.objects.create(
            name="Música",
            description="Eventos musicales"
        )
        # Crear evento
        self.event = Event.objects.create(
            title="Concierto de Prueba",
            description="Un concierto para probar encuestas",
            scheduled_at=timezone.now() + datetime.timedelta(days=7),
            organizer=self.organizer,
            venue=self.venue
        )
        self.event.categories.add(self.category)

class SurveyRealFlowTest(SurveyBaseTest):
    """Tests E2E del flujo real de compra y encuesta"""

    def _comprar_ticket_y_ir_a_encuesta(self):
        """Realiza el flujo de compra y retorna el ticket creado"""
        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}{reverse('event_detail', kwargs={'id': self.event.id})}")
        self.page.get_by_role("link", name="Comprar Ticket").click()
        # Completar datos de tarjeta por id
        self.page.fill("#card_number", "4242 4242 4242 4242")
        self.page.fill("#card_expiry", "12/30")
        self.page.fill("#card_cvv", "123")
        self.page.fill("#card_name", "Juan Pérez")
        self.page.check("#accept_terms")
        # Confirmar compra
        self.page.get_by_role("button", name="Confirmar compra").click()
        # Verificar que estamos en la encuesta
        expect(self.page.get_by_text("Encuesta de Satisfacción")).to_be_visible()
        # Obtener el ticket recién creado
        ticket = Ticket.objects.filter(event=self.event, user=self.user).latest('id')
        return ticket

    def test_survey_form_loads(self):
        """Verifica que el formulario de encuesta carga correctamente tras la compra"""
        self._comprar_ticket_y_ir_a_encuesta()
        expect(self.page.get_by_text("Encuesta de Satisfacción")).to_be_visible()
        expect(self.page.get_by_text("Gracias por tu compra. Nos gustaría conocer tu opinión sobre tu experiencia.")).to_be_visible()
        expect(self.page.locator(".star-rating")).to_be_visible()
        expect(self.page.get_by_label("Observaciones")).to_be_visible()
        expect(self.page.get_by_role("button", name="Enviar Encuesta")).to_be_visible()
        expect(self.page.get_by_role("link", name="Omitir por ahora")).to_be_visible()
        stars = self.page.locator(".star-rating .star")
        expect(stars).to_have_count(5)

    def test_survey_submission_success(self):
        """Verifica que se puede enviar una encuesta exitosamente tras la compra"""
        ticket = self._comprar_ticket_y_ir_a_encuesta()
        self.page.click('label[for="star5"]')
        expect(self.page.locator('input[name="rating"]:checked')).to_have_value("5")
        filled_stars = self.page.locator(".star-rating .bi-star.text-warning")
        expect(filled_stars).to_have_count(5)
        self.page.get_by_label("Observaciones").fill("Excelente experiencia! Muy buena organización.")
        self.page.get_by_role("button", name="Enviar Encuesta").click()
        # Verificar redirección a la lista de tickets
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")
        survey = SatisfactionSurvey.objects.get(ticket=ticket)
        self.assertEqual(survey.rating, 5)
        self.assertEqual(survey.observations, "Excelente experiencia! Muy buena organización.")
        self.assertEqual(survey.user, self.user)
        self.assertEqual(survey.event, self.event)

    def test_survey_rating_required(self):
        """Verifica que no se puede enviar la encuesta sin calificación tras la compra"""
        ticket = self._comprar_ticket_y_ir_a_encuesta()
        self.page.get_by_label("Observaciones").fill("Excelente experiencia! Muy buena organización.")
        self.page.get_by_role("button", name="Enviar Encuesta").click()
        # Verificar que el mensaje de error aparece en el div (aunque no esté visible)
        error_text = self.page.locator("#rating-error").text_content()
        assert "calificación" in error_text or "obligatorio" in error_text
        # Verificar que el formulario no se envió (seguimos en la encuesta)
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/{ticket.id}/survey/")
        self.assertFalse(SatisfactionSurvey.objects.filter(ticket=ticket).exists())

    def test_no_access_to_survey_without_purchase_flow(self):
        """El usuario no puede acceder a la encuesta si no acaba de comprar el ticket (acceso directo por URL)"""
        # Crear ticket directamente (sin flujo de compra)
        from app.models import Ticket
        ticket = Ticket.objects.create(event=self.event, user=self.user, quantity=1, type='GENERAL')
        self.login_user("usuario", "password123")
        # Intentar acceder directamente a la encuesta
        self.page.goto(f"{self.live_server_url}/tickets/{ticket.id}/survey/")
        # Verificar que recibe un mensaje de error o es redirigido (por ejemplo, a la lista de eventos)
        # Puedes ajustar esto según el comportamiento real de tu app
        expect(self.page).not_to_have_url(f"{self.live_server_url}/tickets/{ticket.id}/survey/")
        # Opcional: verificar mensaje de error
        # expect(self.page.get_by_text("No tienes permiso")).to_be_visible() 

    def test_only_one_survey_per_ticket(self):
        """El usuario solo puede completar una encuesta por compra (ticket)"""
        # 1. Comprar ticket y completar encuesta
        ticket = self._comprar_ticket_y_ir_a_encuesta()
        self.page.click('label[for="star5"]')
        self.page.get_by_label("Observaciones").fill("Muy buena experiencia.")
        self.page.get_by_role("button", name="Enviar Encuesta").click()
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")
        # 2. Intentar acceder nuevamente a la encuesta para ese ticket
        self.page.goto(f"{self.live_server_url}/tickets/{ticket.id}/survey/")
        # 3. Verificar que es redirigido o recibe mensaje de que ya completó la encuesta
        expect(self.page).not_to_have_url(f"{self.live_server_url}/tickets/{ticket.id}/survey/")
        # Opcional: verificar mensaje de error o info
        # expect(self.page.get_by_text("Ya has realizado una encuesta para este ticket")).to_be_visible() 

    def test_observation_field_optional(self):
        """El usuario puede enviar la encuesta solo con la calificación (sin observación)"""
        ticket = self._comprar_ticket_y_ir_a_encuesta()
        self.page.click('label[for="star4"]')
        self.page.get_by_role("button", name="Enviar Encuesta").click()
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")
        from app.models import SatisfactionSurvey
        survey = SatisfactionSurvey.objects.get(ticket=ticket)
        self.assertEqual(survey.rating, 4)
        self.assertTrue(survey.observations is None or survey.observations == "") 