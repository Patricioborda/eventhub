from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from app.models import Event, Notification, Ticket, User, Venue

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

        self.event_date = timezone.now() + timezone.timedelta(days=3)  # <-- Guardamos la fecha aquí

        self.event = Event.objects.create(
            title="Evento Test",
            description="Evento de integración",
            scheduled_at=self.event_date,  # Usamos self.event_date acá
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

    def test_only_ticket_holders_receive_notification(self):
        user_with_ticket = User.objects.create_user(username="withticket", password="123")
        Ticket.objects.create(user=user_with_ticket, event=self.event, quantity=1, type='GENERAL')

        user_no_ticket = User.objects.create_user(username="noticket", password="123")

        # Cambia la fecha del evento (o cualquier cambio que dispare la notificación)
        self.event.scheduled_at = self.event.scheduled_at + timezone.timedelta(days=1)
        self.event.save()

        # Obtener notificaciones individuales con usuario
        notified_users_individual = Notification.objects.filter(user__isnull=False).values_list('user_id', flat=True)
        # Obtener notificaciones masivas para todos los asistentes del evento
        notify_all_event = Notification.objects.filter(to_all_event_attendees=True, event=self.event)

        # Obtener IDs de usuarios con tickets
        ticket_holders_ids = Ticket.objects.filter(event=self.event).values_list('user_id', flat=True).distinct()

        # Construir set de usuarios notificados por notificaciones individuales
        notified_users_set = set(notified_users_individual)

        # Si hay notificación masiva, agrego todos los ticket holders
        if notify_all_event.exists():
            notified_users_set.update(ticket_holders_ids)

        print("Usuarios con ticket:", list(ticket_holders_ids))
        print("Usuarios notificados individuales:", list(notified_users_individual))
        print("Usuarios notificados totales:", notified_users_set)

        self.assertIn(user_with_ticket.id, notified_users_set, "Usuario con ticket no recibió notificación") # type: ignore
        self.assertNotIn(user_no_ticket.id, notified_users_set, "Usuario sin ticket recibió notificación") # type: ignore
        self.assertNotIn(self.organizer.id, notified_users_set, "Organizador recibió notificación") # type: ignore
