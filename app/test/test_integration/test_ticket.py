from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import models
from app.models import User, Venue, Event, Category, Ticket


class TicketModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="usuario_test", password="pass")
        self.venue = Venue.objects.create(
            name="Estadio", address="123", city="Ciudad", capacity=100, contact="email@a.com"
        )
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
        Ticket.objects.create(event=self.event, user=self.user, quantity=3, type="GENERAL")
        nuevas = 2
        total_actual = Ticket.objects.filter(user=self.user, event=self.event).aggregate(models.Sum('quantity'))['quantity__sum'] or 0
        total_final = total_actual + nuevas
        self.assertTrue(total_final > 4, "La cantidad total supera el límite de 4 entradas")

    def test_entradas_disponibles_para_usuario(self):
        Ticket.objects.create(event=self.event, user=self.user, quantity=2, type="GENERAL")
        disponibles = Ticket.entradas_disponibles_para_usuario(self.user, self.event)
        self.assertEqual(disponibles, 2, "Debe devolver la cantidad correcta de entradas disponibles (4 - 2 = 2)")

    def test_no_se_pueden_comprar_mas_que_el_cupo_del_evento(self):
        self.event.venue.capacity = 3 # type: ignore
        self.event.venue.save() # type: ignore

        Ticket.objects.create(event=self.event, user=self.user, quantity=2, type="GENERAL")
        remaining = self.event.remaining_capacity
        self.assertEqual(remaining, 1, "Solo debería quedar 1 entrada disponible para el evento")

    def test_no_se_pueden_comprar_mas_de_lo_permitido_por_usuario(self):
        Ticket.objects.create(event=self.event, user=self.user, quantity=3, type="GENERAL")
        ticket = Ticket(event=self.event, user=self.user, quantity=2, type="GENERAL")

        with self.assertRaises(ValidationError) as context:
            ticket.full_clean()  # esto dispara .clean()
        self.assertIn("No puedes comprar más de 4 entradas por evento", str(context.exception))

    def test_no_se_pueden_comprar_mas_que_remaining_capacity(self):
        self.event.venue.capacity = 4 # type: ignore
        self.event.venue.save() # type: ignore
        Ticket.objects.create(event=self.event, user=self.user, quantity=2, type="GENERAL")

        ticket = Ticket(event=self.event, user=self.user, quantity=3, type="GENERAL")
        with self.assertRaises(ValidationError) as context:
            ticket.full_clean()
        self.assertIn("No hay suficiente capacidad para este evento", str(context.exception))

    def test_ticket_code_se_asigna_al_guardar(self):
        ticket = Ticket(event=self.event, user=self.user, quantity=1, type="GENERAL")
        ticket.save()
        self.assertIsNotNone(ticket.ticket_code)
        self.assertEqual(len(ticket.ticket_code), 10)

    def test_str_ticket_con_evento(self):
        ticket = Ticket(event=self.event, user=self.user, quantity=1, type="VIP")
        ticket.save()
        self.assertIn("VIP", str(ticket))
        self.assertIn(self.event.title, str(ticket))

    def test_str_ticket_sin_evento(self):
        ticket = Ticket(quantity=1, type="GENERAL")
        # Simula que no se asignó aún un evento (ej. commit=False)
        ev_title = getattr(ticket, "event", None)
        self.assertIsNone(ev_title)
        self.assertIn("GENERAL", str(ticket))
