# app/test/test_unit/test_favorite.py
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model
from app.models import Event
from eventhub.app.models import  Favorite

User = get_user_model()

class FavoriteModelTest(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="org", password="pwd", is_organizer=True
        )
        self.event = Event.objects.create(
            title="E1", description="D1", scheduled_at="2025-01-01T12:00:00Z", organizer=self.organizer
        )

    def test_str_representation(self):
        fav = Favorite.objects.create(user=self.organizer, event=self.event)
        self.assertEqual(str(fav), f"{self.organizer.username} ♥ {self.event.title}")

    def test_unique_constraint_prevents_duplicate(self):
        Favorite.objects.create(user=self.organizer, event=self.event)
        with self.assertRaises(Exception):
            # Puede ser IntegrityError o Django’s ValidationError según cómo lo captures
            Favorite.objects.create(user=self.organizer, event=self.event)

    def test_clean_raises_if_missing_user_or_event(self):
        fav = Favorite(user=None, event=self.event)
        with self.assertRaises(ValidationError):
            fav.clean()
        fav = Favorite(user=self.organizer, event=None)
        with self.assertRaises(ValidationError):
            fav.clean()

    # Si quisieras probar un método toggle (opcional):
    def test_toggle_favorite_method(self):
        # supongamos que agregaste en Favorite:
        # @classmethod
        # def toggle(cls, user, event): ...
        fav, created = Favorite.objects.get_or_create(user=self.organizer, event=self.event)
        # primera vez creado= True
        self.assertTrue(created)
        # segunda vez, debería borrarlo o devolver created=False
        toggled, created2 = Favorite.toggle(self.organizer, self.event)
        self.assertFalse(created2)
        self.assertFalse(Favorite.objects.filter(user=self.organizer, event=self.event).exists())
