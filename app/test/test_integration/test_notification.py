from django.test import TestCase
from django.utils import timezone
from app.models import Event, Notification, User, Venue

class NotificationSignalIntegrationTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador",
            email="org@example.com",
            password="pass123",
            is_organizer=True
        )

        self.venue_old = Venue.objects.create(
            name="Sala A", address="Calle 1", city="Ciudad", capacity=100, contact="123456"
        )

        self.venue_new = Venue.objects.create(
            name="Sala B", address="Calle 2", city="Ciudad", capacity=150, contact="789123"
        )

        self.event = Event.objects.create(
            title="Evento Test",
            description="Evento de integración",
            scheduled_at=timezone.now() + timezone.timedelta(days=3),
            organizer=self.organizer,
            venue=self.venue_old,
        )

    def test_signal_creates_notification_on_event_change(self):
        # Cambiamos fecha y lugar
        self.event.scheduled_at += timezone.timedelta(days=2)
        self.event.venue = self.venue_new
        self.event.save()

        # Obtener las notificaciones relacionadas al evento
        notifications = Notification.objects.filter(event=self.event)

        # Aseguramos que hay al menos una notificación (fallará si no)
        self.assertGreater(notifications.count(), 0, "No se creó ninguna notificación para el evento")

        notif = notifications.first()
        # Aseguramos que notif no es None para que el análisis estático no falle
        self.assertIsNotNone(notif, "No se encontró la notificación")

        # Ahora podemos acceder con seguridad a sus atributos sin warnings
        self.assertTrue(notif.to_all_event_attendees) # type: ignore
        self.assertEqual(notif.created_by, self.organizer) # type: ignore
        self.assertIn("📅", notif.message) # type: ignore
        self.assertIn("📍", notif.message) # type: ignore
        self.assertEqual(notif.title, "🛎️ ¡Cambio importante en tu evento!") # type: ignore


    def test_signal_does_not_trigger_on_other_field_change(self):
        self.event.description = "Descripción actualizada"
        self.event.save()

        # No debe crearse notificación
        self.assertEqual(Notification.objects.count(), 0)

    def test_no_notification_on_event_creation(self):
        # Crear un nuevo evento no debe generar notificación
        new_event = Event.objects.create(
            title="Nuevo evento",
            description="Evento recién creado",
            scheduled_at=timezone.now() + timezone.timedelta(days=10),
            organizer=self.organizer,
            venue=self.venue_old,
        )
        self.assertEqual(Notification.objects.filter(event=new_event).count(), 0)

    def test_multiple_notifications_for_multiple_changes(self):
        # Cambio 1
        self.event.scheduled_at += timezone.timedelta(days=1)
        self.event.save()
        self.assertEqual(Notification.objects.filter(event=self.event).count(), 1)

        # Cambio 2
        self.event.venue = self.venue_new
        self.event.save()
        self.assertEqual(Notification.objects.filter(event=self.event).count(), 2)

    def test_notification_on_event_date_change(self):
        self.event.scheduled_at += timezone.timedelta(days=1)
        self.event.save()

        notifications = Notification.objects.filter(event=self.event)
        self.assertGreater(notifications.count(), 0)
        notif = notifications.first()
        self.assertIn("📅", notif.message) # type: ignore

    def test_notification_on_event_venue_change(self):
        self.event.venue = self.venue_new
        self.event.save()

        notifications = Notification.objects.filter(event=self.event)
        self.assertGreater(notifications.count(), 0)
        notif = notifications.first()
        self.assertIn("📍", notif.message) # type: ignore
