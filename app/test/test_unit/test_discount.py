from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta
from app.models import User, Venue, Event, Category, Ticket, DiscountCode  # Incluye DiscountCode

class DiscountCodeModelTest(TestCase):
    def setUp(self) -> None:
        self.organizer = User.objects.create_user(
            username="organizador_test",
            email="organizador@example.com",
            password="password123",
            is_organizer=True,
        )
        self.venue = Venue.objects.create(
            name="Centro de Convenciones",
            address="Ciudad",
            city="Ciudad",
            capacity=100,
            contact="Contacto"
        )
        self.category1 = Category.objects.create(name="Tecnología")
        self.category2 = Category.objects.create(name="Educación")
        self.categories = [self.category1, self.category2]

    def test_discount_code_creation(self):
        """Test: Crear un código de descuento válido"""
        discount = DiscountCode.objects.create(
            code='TEST10',
            description='10% discount',
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            max_uses=100,
            discount_type='percent',
            discount_value=Decimal('10.00'),
            created_by=self.organizer
        )
        
        self.assertEqual(discount.code, 'TEST10')
        self.assertEqual(discount.uses, 0)
        self.assertTrue(discount.is_valid())

    def test_discount_code_is_valid_with_expired_date(self):
        """Test: Código de descuento expirado debe ser inválido"""
        discount = DiscountCode.objects.create(
            code='EXPIRED',
            valid_from=date.today() - timedelta(days=10),
            valid_until=date.today() - timedelta(days=1),  # Expirado
            max_uses=100,
            discount_type='fixed',
            discount_value=Decimal('5.00'),
            created_by=self.organizer
        )
        
        self.assertFalse(discount.is_valid())
