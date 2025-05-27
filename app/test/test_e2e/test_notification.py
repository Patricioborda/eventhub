from django.utils import timezone
import datetime
from playwright.sync_api import expect
from app.models import Ticket, User, Event, Venue, Notification
from app.test.test_e2e.base import BaseE2ETest

class NotificationOnEventChangeTest(BaseE2ETest):
    
    def setUp(self):
        super().setUp()
        self.organizer = User.objects.create_user(
            username="organizer", email="org@example.com", password="password123", is_organizer=True
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="password123", is_organizer=False
        )
        self.venue1 = Venue.objects.create(name="Sala A", address="Dirección 1", city="Ciudad", capacity=100, contact="contacto1@example.com")
        self.venue2 = Venue.objects.create(name="Sala B", address="Dirección 2", city="Ciudad", capacity=100, contact="contacto2@example.com")

        self.event_date = timezone.make_aware(datetime.datetime(2025, 7, 15, 20, 0))
        self.event = Event.objects.create(
            title="Evento Original",
            description="Descripción original",
            scheduled_at=self.event_date,
            organizer=self.organizer,
            venue=self.venue1,
        )
        # Crear un ticket para other_user en el evento
        Ticket.objects.create(user=self.other_user, event=self.event, quantity=1, type='GENERAL')

    def test_notification_created_when_event_date_changes(self):
        """Al cambiar la fecha del evento, se crea una notificación general"""

        # Login usuario común
        self.login_user("otheruser", "password123")

        # Cambiar fecha del evento
        new_date = self.event_date + datetime.timedelta(days=1)
        self.event.scheduled_at = new_date
        self.event.save()

        # Verificar que se creó una notificación general del evento
        notif = Notification.objects.filter(
            event=self.event,
            to_all_event_attendees=True,
            message__icontains="Fecha"
        ).first()
        assert notif is not None, "No se creó la notificación de cambio de fecha para el evento"

        # Navegar a la página detalle de la notificación
        self.page.goto(f"{self.live_server_url}/notifications/{notif.pk}/")
        self.page.wait_for_selector(".containerNotificaciones")

        # Buscar en el detalle que el mensaje contiene "Fecha"
        detalle_text = self.page.locator(".containerNotificaciones").inner_text()
        assert "Fecha" in detalle_text, "El mensaje de detalle no contiene 'Fecha'"

    def test_notification_created_when_event_venue_changes(self):
        """Al cambiar el lugar del evento, se crea una notificación general"""

        self.login_user("otheruser", "password123")

        # Cambiar lugar del evento
        self.event.venue = self.venue2
        self.event.save()

        # Verificar que se creó una notificación general del evento
        notif = Notification.objects.filter(
            event=self.event,
            to_all_event_attendees=True,
            message__icontains="Lugar"
        ).first()
        assert notif is not None, "No se creó la notificación de cambio de lugar para el evento"

        # Navegar a la página detalle de la notificación
        self.page.goto(f"{self.live_server_url}/notifications/{notif.pk}/")
        self.page.wait_for_selector(".containerNotificaciones")

        # Buscar en el detalle que el mensaje contiene "Lugar"
        detalle_text = self.page.locator(".containerNotificaciones").inner_text()
        assert "Lugar" in detalle_text, "El mensaje de detalle no contiene 'Lugar'"
