import datetime
from django.test import TestCase
from django.utils import timezone

from app.models import Event, User, Venue, Category

class EventModelTest(TestCase):
    def setUp(self) -> None:
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )
        self.venue = Venue.objects.create(name="Centro de Convenciones", address="Ciudad", city="Ciudad", capacity=100, contact="Contacto")
        self.category1 = Category.objects.create(name="Tecnología")
        self.category2 = Category.objects.create(name="Educación")
        self.categories = [self.category1, self.category2]


    def test_event_creation(self):
        """Verifica la creación correcta de un evento usando el método create"""
        event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue,
        )
        # Agrego category1 explícitamente, porque no existe self.category
        event.categories.add(self.category1)

        self.assertEqual(event.title, "Evento de prueba")
        self.assertEqual(event.description, "Descripción del evento de prueba")
        self.assertEqual(event.organizer, self.organizer)
        self.assertIsNotNone(event.created_at)
        self.assertIsNotNone(event.updated_at)
        self.assertIn(self.category1, event.categories.all())

    def test_event_validate_with_valid_data(self):
        """Verifica que la validación de un evento con datos válidos no arroja errores"""
        scheduled_at = timezone.now() + datetime.timedelta(days=1)
        errors = Event.validate(
            title="Título válido",
            description="Descripción válida",
            venue=self.venue,
            scheduled_at=scheduled_at,
            categories=[self.category1],
        )
        self.assertEqual(errors, {})

    def test_event_validate_with_empty_title(self):
        """Verifica que la validación falla si el título está vacío"""
        scheduled_at = timezone.now() + datetime.timedelta(days=1)
        errors = Event.validate(
            title="",
            description="Descripción válida",
            venue=self.venue,
            scheduled_at=scheduled_at,
            categories=[self.category1],
        )
        self.assertIn("title", errors)
        self.assertEqual(errors["title"], "Por favor ingrese un título")

    def test_event_validate_with_empty_description(self):
        """Verifica que la validación falla si la descripción está vacía"""
        scheduled_at = timezone.now() + datetime.timedelta(days=1)
        errors = Event.validate(
            title="Título válido",
            description="",
            venue=self.venue,
            scheduled_at=scheduled_at,
            categories=[self.category1],
        )
        self.assertIn("description", errors)
        self.assertEqual(errors["description"], "Por favor ingrese una descripción")

    def test_event_new_with_valid_data(self):
        """Verifica que se puede crear un evento correctamente con datos válidos usando Event.new"""
        scheduled_at = timezone.now() + datetime.timedelta(days=2)
        success, errors = Event.new(
            title="Nuevo evento",
            description="Descripción del nuevo evento",
            venue=self.venue,
            scheduled_at=scheduled_at,
            organizer=self.organizer,
            categories=[self.category1],
        )

        self.assertTrue(success)
        self.assertIsNone(errors)

        new_event = Event.objects.get(title="Nuevo evento")
        self.assertEqual(new_event.description, "Descripción del nuevo evento")
        self.assertEqual(new_event.organizer, self.organizer)
        self.assertIn(self.category1, new_event.categories.all())

    def test_event_new_with_invalid_data(self):
        """Verifica que no se puede crear un evento con datos inválidos usando Event.new"""
        scheduled_at = timezone.now() + datetime.timedelta(days=2)
        initial_count = Event.objects.count()

        success, errors = Event.new(
            title="",
            description="Descripción del evento",
            venue=self.venue,
            scheduled_at=scheduled_at,
            organizer=self.organizer,
            categories=[self.category1],
        )

        self.assertFalse(success)
        if errors is not None:
            self.assertIn("title", errors)
        else:
            self.fail("Errors is None, expected a dict with errors")

        self.assertEqual(Event.objects.count(), initial_count)

    def test_event_update(self):
        """Verifica que un evento puede ser actualizado correctamente con todos los campos"""
        event = Event.objects.create(
            title="Evento original",
            description="Descripción original",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue,
        )
        event.categories.add(self.category1)

        new_title = "Evento actualizado"
        new_description = "Nueva descripción"
        new_scheduled_at = timezone.now() + datetime.timedelta(days=3)
        new_category = Category.objects.create(name="Seminario")

        event.update(
            title=new_title,
            description=new_description,
            scheduled_at=new_scheduled_at,
            organizer=self.organizer,
            venue=self.venue,
            categories=[new_category],
        )

        updated_event = Event.objects.get(pk=event.pk)
        self.assertEqual(updated_event.title, new_title)
        self.assertEqual(updated_event.description, new_description)
        self.assertEqual(updated_event.scheduled_at.time(), new_scheduled_at.time())
        self.assertIn(new_category, updated_event.categories.all())

    def test_event_update_partial(self):
        """Verifica que se puede actualizar parcialmente un evento (solo algunos campos)"""
        event = Event.objects.create(
            title="Evento de prueba",
            description="Descripción del evento de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            organizer=self.organizer,
            venue=self.venue,
        )
        event.categories.add(self.category1)

        original_title = event.title
        original_scheduled_at = event.scheduled_at
        new_description = "Solo la descripción ha cambiado"

        event.update(
            title=None,
            description=new_description,
            scheduled_at=None,
            organizer=None,
            venue=None,
            categories=None,
        )

        updated_event = Event.objects.get(pk=event.pk)
        self.assertEqual(updated_event.title, original_title)
        self.assertEqual(updated_event.description, new_description)
        self.assertEqual(updated_event.scheduled_at, original_scheduled_at)
