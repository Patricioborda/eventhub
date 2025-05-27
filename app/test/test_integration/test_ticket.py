from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from app.models import User, Venue, Category, Event, Ticket

class TicketIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.venue = Venue.objects.create(name="Teatro", address="Av Siempre Viva", city="Springfield", capacity=100, contact="email@test.com")
        self.category = Category.objects.create(name="Teatro", description="Teatro y espectáculos")
        self.event = Event.objects.create(
            title="Obra de teatro",
            description="Una obra espectacular",
            scheduled_at=timezone.now() + timezone.timedelta(days=1),
            organizer=self.user,
            venue=self.venue
        )
        self.event.categories.add(self.category)

        # Usuario compra 3 entradas antes del test
        Ticket.objects.create(user=self.user, event=self.event, quantity=3, type="GENERAL")

    def test_no_puede_comprar_mas_de_4(self):
        self.client.login(username='testuser', password='pass123')

        url = reverse('ticket_create', args=[self.event.id])
        post_data = {
            'quantity': 2,  # intenta comprar 2 más
            'type': 'GENERAL',
            'card_number': '1234 5678 9012 3456',
            'card_expiry': '12/25',
            'card_cvv': '123',
            'card_name': 'Juan Perez'
        }

        response = self.client.post(url, post_data, follow=True)

        # No debe redirigir: sigue en la misma página (no se creó el ticket)
        self.assertContains(response, "No puedes comprar más de 4 entradas por evento.")
        self.assertEqual(Ticket.objects.filter(user=self.user, event=self.event).count(), 1)
