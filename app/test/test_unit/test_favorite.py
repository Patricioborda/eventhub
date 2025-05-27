# app/test/test_unit/test_favorite.py
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model
from app.models import Event, Favorite   # type: ignore



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
            Favorite.objects.create(user=self.organizer, event=self.event)

    def test_clean_raises_if_missing_user_or_event(self):
        fav = Favorite(user=None, event=self.event)
        with self.assertRaises(ValidationError):
            fav.clean()
        fav = Favorite(user=self.organizer, event=None)
        with self.assertRaises(ValidationError):
            fav.clean()

    def test_toggle_favorite_method(self):
        fav, created = Favorite.toggle(self.organizer, self.event)  # type: ignore
        self.assertTrue(created)
        fav, created2 = Favorite.toggle(self.organizer, self.event)  # type: ignore
        self.assertFalse(created2)
        self.assertFalse(Favorite.objects.filter(user=self.organizer, event=self.event).exists())

    def test_toggle_different_user(self):
        another_user = User.objects.create_user(username="otro", password="1234")
        Favorite.toggle(another_user, self.event)  # type: ignore
        self.assertTrue(Favorite.objects.filter(user=another_user, event=self.event).exists())

    def test_toggle_different_event(self):
        new_event = Event.objects.create(
            title="E2", description="D2", scheduled_at="2025-01-02T15:00:00Z", organizer=self.organizer
        )
        Favorite.toggle(self.organizer, new_event)  # type: ignore
        self.assertTrue(Favorite.objects.filter(user=self.organizer, event=new_event).exists())
