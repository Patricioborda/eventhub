import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from app.models import User, Event, Venue, Category, Favorite


class BaseFavoriteTestCase(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="organizador", email="org@test.com", password="password123", is_organizer=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", email="reg@test.com", password="password123"
        )
        self.venue = Venue.objects.create(
            name="Teatro Luna", address="Calle 123", city="La Plata", capacity=100, contact="mail@test.com"
        )
        self.category = Category.objects.create(name="Música", description="Eventos musicales")

        self.event = Event.objects.create(
            title="Show de Rock",
            description="Recital de prueba",
            scheduled_at=timezone.now() + datetime.timedelta(days=3),
            organizer=self.organizer,
            venue=self.venue,
        )
        self.event.categories.add(self.category)

        self.client = Client()


class FavoriteIntegrationTest(BaseFavoriteTestCase):
    def test_agregar_a_favoritos(self):
        self.client.login(username="regular", password="password123")
        response = self.client.post(reverse("toggle_favorite", args=[self.event.id])) # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Favorite.objects.filter(user=self.regular_user, event=self.event).exists())

    def test_quitar_de_favoritos(self):
        Favorite.objects.create(user=self.regular_user, event=self.event)
        self.client.login(username="regular", password="password123")
        response = self.client.post(reverse("toggle_favorite", args=[self.event.id])) # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Favorite.objects.filter(user=self.regular_user, event=self.event).exists())

    def test_vista_favoritos_autenticado(self):
        Favorite.objects.create(user=self.regular_user, event=self.event)
        self.client.login(username="regular", password="password123")
        response = self.client.get(reverse("favorites_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "favorites/list.html")
        self.assertIn("events", response.context)
        self.assertEqual(len(response.context["events"]), 1)

    def test_vista_favoritos_no_autenticado_redirige(self):
        response = self.client.get(reverse("favorites_list"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/")) # type: ignore

    def test_toggle_no_autenticado_redirige(self):
        response = self.client.post(reverse("toggle_favorite", args=[self.event.id])) # type: ignore
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/")) # type: ignore
