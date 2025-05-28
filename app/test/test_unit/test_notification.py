from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from app.models import Notification, User, Event, Venue

class NotificationModelTest(TestCase):
    def setUp(self):
        # Usuarios de prueba
        self.user = User.objects.create_user(
            username="usuario_test",
            email="usuario@example.com",
            password="password123",
        )
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )
        # Lugar de evento
        self.venue = Venue.objects.create(
            name="Teatro Colón",
            address="Calle Falsa 123",
            city="Ciudad Gótica",
            capacity=200,
            contact="0123456789"
        )
        # Evento de prueba
        self.event = Event.objects.create(
            title="Obra de teatro",
            description="Una obra espectacular",
            scheduled_at=timezone.now() + timezone.timedelta(days=5),
            organizer=self.organizer,
            venue=self.venue
        )

    # --- Tests para creación válida ---

    def test_create_personal_notification(self):
        """Notificación personal válida"""
        notification = Notification.objects.create(
            user=self.user,
            event=None,
            to_all_event_attendees=False,
            title="Notificación personal",
            message="La fecha del evento ha cambiado",
            priority="normal",
        )
        self.assertEqual(notification.user, self.user)
        self.assertIsNone(notification.event)
        self.assertFalse(notification.to_all_event_attendees)
        self.assertEqual(notification.message, "La fecha del evento ha cambiado")
        self.assertFalse(notification.is_read)
        self.assertIsNotNone(notification.created_at)

    def test_create_mass_notification(self):
        """Notificación masiva válida para todos los asistentes"""
        notification = Notification.objects.create(
            user=None,
            event=self.event,
            to_all_event_attendees=True,
            title="Notificación masiva",
            message="El lugar del evento ha cambiado",
            priority="high",
        )
        self.assertIsNone(notification.user)
        self.assertEqual(notification.event, self.event)
        self.assertTrue(notification.to_all_event_attendees)
        self.assertEqual(notification.message, "El lugar del evento ha cambiado")
        self.assertFalse(notification.is_read)
        self.assertIsNotNone(notification.created_at)

    def test_mark_notification_as_seen(self):
        """Marcar notificación como leída"""
        notification = Notification.objects.create(
            user=self.user,
            event=None,
            to_all_event_attendees=False,
            title="Notificación personal",
            message="Lugar actualizado",
            priority="normal",
        )
        notification.is_read = True
        notification.save()

        updated = Notification.objects.get(pk=notification.pk)
        self.assertTrue(updated.is_read)

class NotificationModelValidationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="usuario_test",
            email="usuario@example.com",
            password="password123",
        )
        self.venue = Venue.objects.create(
            name="Lugar test",
            address="Calle 123",
            city="Ciudad",
            capacity=100,
            contact="123456789"
        )
        self.event = Event.objects.create(
            title="Evento test",
            description="Descripción",
            scheduled_at=timezone.now() + timezone.timedelta(days=5),
            organizer=self.user,
            venue=self.venue
        )

    # --- Tests para validación de errores (método clean + constraints) ---

    def test_fail_mass_notification_without_event(self):
        """Error si to_all_event_attendees=True sin evento"""
        notification = Notification(
            user=None,
            event=None,
            to_all_event_attendees=True,
            title="Notif inválida",
            message="Sin evento",
        )
        with self.assertRaises(ValidationError) as cm:
            notification.full_clean()
        self.assertIn('event', cm.exception.message_dict)

    def test_fail_mass_notification_with_user(self):
        """Error si to_all_event_attendees=True y se asigna usuario"""
        notification = Notification(
            user=self.user,
            event=self.event,
            to_all_event_attendees=True,
            title="Notif inválida",
            message="Con usuario y para todos",
        )
        with self.assertRaises(ValidationError) as cm:
            notification.full_clean()
        self.assertIn('user', cm.exception.message_dict)

    def test_fail_personal_notification_without_user(self):
        """Error si notificación personal sin usuario"""
        notification = Notification(
            user=None,
            event=None,
            to_all_event_attendees=False,
            title="Notif inválida",
            message="Sin usuario ni evento",
        )
        with self.assertRaises(ValidationError) as cm:
            notification.full_clean()
        self.assertIn('user', cm.exception.message_dict)

    def test_fail_personal_notification_with_event(self):
        """Error si notificación personal tiene evento asignado"""
        notification = Notification(
            user=self.user,
            event=self.event,
            to_all_event_attendees=False,
            title="Notif inválida",
            message="Evento con user y sin ser masiva",
        )
        with self.assertRaises(ValidationError) as cm:
            notification.full_clean()
        self.assertIn('event', cm.exception.message_dict)
    
    def test_fail_invalid_priority_value(self):
        """Error si se asigna un valor inválido al campo priority"""
        notification = Notification(
            user=self.user,
            event=None,
            to_all_event_attendees=False,
            title="Notif inválida",
            message="Con prioridad inválida",
            priority="urgente",  # valor no permitido
        )
        with self.assertRaises(ValidationError) as cm:
            notification.full_clean()
        self.assertIn('priority', cm.exception.message_dict)

    def test_valid_priority_values(self):
        """Valores válidos permitidos en campo priority"""
        for valid_priority in ["low", "normal", "high"]:
            notification = Notification(
                user=self.user,
                event=None,
                to_all_event_attendees=False,
                title=f"Notif prioridad {valid_priority}",
                message="Mensaje de prueba",
                priority=valid_priority,
            )
            # No debe lanzar excepción
            try:
                notification.full_clean()
            except ValidationError:
                self.fail(f"Valid priority '{valid_priority}' raised ValidationError")
    
    def test_default_is_read_false(self):
        """Campo is_read debe ser False por defecto"""
        notification = Notification.objects.create(
            user=self.user,
            to_all_event_attendees=False,
            title="Notif sin leer",
            message="Mensaje de prueba",
        )
        self.assertFalse(notification.is_read)
    
    def test_created_at_auto_set(self):
        """Campo created_at debe generarse automáticamente"""
        notification = Notification.objects.create(
            user=self.user,
            to_all_event_attendees=False,
            title="Notif con fecha",
            message="Mensaje con timestamp",
        )
        self.assertIsNotNone(notification.created_at)
