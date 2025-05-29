from django.test import TestCase, Client
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
import json

from app.models import User, Venue, Event, Category, Ticket, DiscountCode

class DiscountIntegrationTest(TestCase):
    def setUp(self):
        """Configuración inicial para los tests de integración"""
        self.client = Client()
        
        # Crear usuario organizador
        self.user = User.objects.create_user(
            username='organizer',
            password='testpass123',
            email='organizer@example.com'
        )
        self.user.is_organizer = True
        self.user.save()
        
        # Crear usuario comprador
        self.buyer = User.objects.create_user(
            username='buyer',
            password='buyerpass123',
            email='buyer@example.com'
        )
        
        # Crear venue y evento
        self.venue = Venue.objects.create(
            name='Integration Test Venue',
            address='456 Integration St',
            capacity=200
        )
        
        self.event = Event.objects.create(
            title='Integration Test Event',
            description='Integration Test Description',
            scheduled_at=timezone.now() + timedelta(days=30),
            venue=self.venue,
            organizer=self.user
        )
        
        # Crear código de descuento válido
        self.valid_discount = DiscountCode.objects.create(
            code='VALID20',
            description='20% discount',
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            max_uses=100,
            discount_type='percent',
            discount_value=Decimal('20.00'),
            event=None,  # Aplica a todos los eventos
            created_by=self.user
        )
        
        # Crear código de descuento específico para el evento
        self.event_specific_discount = DiscountCode.objects.create(
            code='EVENT10',
            description='Event specific discount',
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            max_uses=50,
            discount_type='fixed',
            discount_value=Decimal('10.00'),
            event=self.event,
            created_by=self.user
        )

    def test_validar_cupon_ajax_valid_code(self):
        """Test: Validación AJAX de cupón válido"""
        url = reverse('validar_cupon')
        response = self.client.get(url, {
            'codigo': 'VALID20',
            'event_id': self.event.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['discount_value'], 20.0)
        self.assertEqual(data['discount_type'], 'percent')
        self.assertIn('Se aplicó un descuento', data['message'])

    def test_validar_cupon_ajax_invalid_code(self):
        """Test: Validación AJAX de cupón inválido"""
        url = reverse('validar_cupon')
        response = self.client.get(url, {
            'codigo': 'INVALID',
            'event_id': self.event.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'not_found')
        self.assertIn('No se encontró el cupón', data['message'])

    def test_validar_cupon_ajax_event_specific(self):
        """Test: Validación AJAX de cupón específico para evento"""
        url = reverse('validar_cupon')
        response = self.client.get(url, {
            'codigo': 'EVENT10',
            'event_id': self.event.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['discount_value'], 10.0)
        self.assertEqual(data['discount_type'], 'fixed')

    def test_ticket_create_with_valid_discount(self):
        """Test: Crear ticket con cupón válido incrementa usos"""
        self.client.login(username='buyer', password='buyerpass123')
        
        # Verificar usos iniciales
        initial_uses = self.valid_discount.uses
        
        url = reverse('ticket_create', kwargs={'event_id': self.event.id})
        response = self.client.post(url, {
            'quantity': 2,
            'type': 'GENERAL',
            'discount_code': 'VALID20',
            # Campos de tarjeta simulados
            'card_number': '1234567890123456',
            'card_expiry': '12/25',
            'card_cvv': '123',
            'card_name': 'John Doe'
        })
        
        # Verificar redirección (compra exitosa)
        self.assertEqual(response.status_code, 302)
        
        # Verificar que el ticket fue creado con descuento
        ticket = Ticket.objects.filter(user=self.buyer, event=self.event).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.discount_code, self.valid_discount)
        
        # Verificar que los usos se incrementaron
        self.valid_discount.refresh_from_db()
        self.assertEqual(self.valid_discount.uses, initial_uses + 1)

    def test_ticket_create_with_invalid_discount(self):
        """Test: Crear ticket con cupón inválido no aplica descuento"""
        self.client.login(username='buyer', password='buyerpass123')
        
        url = reverse('ticket_create', kwargs={'event_id': self.event.id})
        response = self.client.post(url, {
            'quantity': 1,
            'type': 'VIP',
            'discount_code': 'NONEXISTENT',
            'card_number': '1234567890123456',
            'card_expiry': '12/25',
            'card_cvv': '123',
            'card_name': 'Jane Doe'
        })
        
        # Verificar redirección (compra exitosa sin descuento)
        self.assertEqual(response.status_code, 302)
        
        # Verificar que el ticket fue creado sin descuento
        ticket = Ticket.objects.filter(user=self.buyer, event=self.event).first()
        self.assertIsNotNone(ticket)
        self.assertIsNone(ticket.discount_code)

    def test_ticket_create_with_expired_discount(self):
        """Test: Cupón expirado no se aplica"""
        # Crear cupón expirado
        expired_discount = DiscountCode.objects.create(
            code='EXPIRED',
            valid_from=date.today() - timedelta(days=10),
            valid_until=date.today() - timedelta(days=1),
            max_uses=100,
            discount_type='percent',
            discount_value=Decimal('30.00'),
            created_by=self.user
        )
        
        self.client.login(username='buyer', password='buyerpass123')
        
        url = reverse('ticket_create', kwargs={'event_id': self.event.id})
        response = self.client.post(url, {
            'quantity': 1,
            'type': 'GENERAL',
            'discount_code': 'EXPIRED',
            'card_number': '1234567890123456',
            'card_expiry': '12/25',
            'card_cvv': '123',
            'card_name': 'Test User'
        })
        
        # Verificar que el ticket se creó sin descuento
        ticket = Ticket.objects.filter(user=self.buyer, event=self.event).first()
        self.assertIsNotNone(ticket)
        self.assertIsNone(ticket.discount_code)
        
        # Los usos no deben incrementarse
        expired_discount.refresh_from_db()
        self.assertEqual(expired_discount.uses, 0)

    def test_multiple_tickets_increment_uses_correctly(self):
        """Test: Múltiples tickets con el mismo cupón incrementan usos correctamente"""
        self.client.login(username='buyer', password='buyerpass123')
        
        initial_uses = self.valid_discount.uses
        
        # Primera compra
        url = reverse('ticket_create', kwargs={'event_id': self.event.id})
        self.client.post(url, {
            'quantity': 1,
            'type': 'GENERAL',
            'discount_code': 'VALID20',
            'card_number': '1234567890123456',
            'card_expiry': '12/25',
            'card_cvv': '123',
            'card_name': 'First Purchase'
        })
        
        # Crear otro usuario para segunda compra
        second_buyer = User.objects.create_user(
            username='buyer2',
            password='buyerpass123',
            email='buyer2@example.com'
        )
        
        self.client.login(username='buyer2', password='buyerpass123')
        
        # Segunda compra
        self.client.post(url, {
            'quantity': 2,
            'type': 'VIP',
            'discount_code': 'VALID20',
            'card_number': '1234567890123456',
            'card_expiry': '12/25',
            'card_cvv': '123',
            'card_name': 'Second Purchase'
        })
        
        # Verificar que los usos se incrementaron correctamente (2 compras = 2 usos)
        self.valid_discount.refresh_from_db()
        self.assertEqual(self.valid_discount.uses, initial_uses + 2)

    def test_discount_reaches_max_uses(self):
        """Test: Cupón que alcanza el máximo de usos se vuelve inválido"""
        # Crear cupón con solo 1 uso disponible
        limited_discount = DiscountCode.objects.create(
            code='LIMITED1',
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            max_uses=1,
            uses=0,
            discount_type='fixed',
            discount_value=Decimal('5.00'),
            created_by=self.user
        )
        
        self.client.login(username='buyer', password='buyerpass123')
        
        # Primera compra (debería funcionar)
        url = reverse('ticket_create', kwargs={'event_id': self.event.id})
        response = self.client.post(url, {
            'quantity': 1,
            'type': 'GENERAL',
            'discount_code': 'LIMITED1',
            'card_number': '1234567890123456',
            'card_expiry': '12/25',
            'card_cvv': '123',
            'card_name': 'First User'
        })
        
        # Verificar que se aplicó el descuento
        ticket = Ticket.objects.filter(user=self.buyer, event=self.event).first()
        self.assertEqual(ticket.discount_code, limited_discount)
        
        # Verificar que el cupón ya no es válido
        limited_discount.refresh_from_db()
        self.assertEqual(limited_discount.uses, 1)
        self.assertFalse(limited_discount.is_valid())