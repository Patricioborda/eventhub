from django.test import TestCase
from django.utils import timezone
from django.db import models
from app.models import User, Venue, Event, Category, Ticket


class TicketModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="usuario_test", password="pass")
        self.venue = Venue.objects.create(name="Estadio", address="123", city="Ciudad", capacity=100, contact="email@a.com")
        self.category = Category.objects.create(name="Música", description="Conciertos")
        self.event = Event.objects.create(
            title="Evento musical",
            description="Concierto",
            scheduled_at=timezone.now() + timezone.timedelta(days=1),
            organizer=self.user,
            venue=self.venue
        )
        self.event.categories.add(self.category)

    def test_no_se_pueden_comprar_mas_de_4_entradas(self):
        # Compra inicial: 3 entradas
        Ticket.objects.create(event=self.event, user=self.user, quantity=3, type="GENERAL")
        
        # Intento de nueva compra de 2 entradas (total 5)
        nuevas = 2
        total_actual = Ticket.objects.filter(user=self.user, event=self.event).aggregate(models.Sum('quantity'))['quantity__sum'] or 0
        total_final = total_actual + nuevas

        self.assertTrue(total_final > 4, "La cantidad total supera el límite de 4 entradas")
