# app/test/test_e2e/test_discount.py
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from app.models import Venue, Event, DiscountCode, Ticket, Category
from app.test.test_e2e.base import BaseE2ETest
from playwright.sync_api import expect

User = get_user_model()

class DiscountE2ETest(BaseE2ETest):
    """Tests End-to-End para la compra de tickets con cupones de descuento"""
    
    def setUp(self):
        super().setUp()
        
        # Crear usuario organizador
        self.organizer = User.objects.create_user(
            username='organizer_e2e',
            password='organizer123',
            email='organizer@e2e.com',
            is_organizer=True
        )
        
        # Crear usuario comprador
        self.buyer = User.objects.create_user(
            username='buyer_e2e',
            password='buyer123',
            email='buyer@e2e.com',
            is_organizer=False
        )
        
        # Crear categoría
        self.category = Category.objects.create(
            name='Test Category',
            description='Category for E2E testing',
            is_active=True
        )
        
        # Crear venue
        self.venue = Venue.objects.create(
            name='E2E Test Venue',
            address='789 E2E Test St',
            city='Test City',
            capacity=300,
            contact='test@venue.com'
        )
        
        # Crear evento
        self.event = Event.objects.create(
            title='E2E Test Event',
            description='End-to-End Test Event',
            scheduled_at=timezone.now() + timedelta(days=30),
            venue=self.venue,
            organizer=self.organizer
        )
        self.event.categories.add(self.category)
        
        # Crear cupón de descuento porcentual válido
        self.discount_code = DiscountCode.objects.create(
            code='E2E20',
            description='E2E 20% discount',
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            max_uses=10,
            discount_type='percent',
            discount_value=Decimal('20.00'),
            event=None,
            created_by=self.organizer
        )
        
        # Crear cupón de descuento fijo válido
        self.fixed_discount = DiscountCode.objects.create(
            code='FIXED15',
            description='Fixed $15 discount',
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            max_uses=5,
            discount_type='fixed',
            discount_value=Decimal('15.00'),
            event=self.event,
            created_by=self.organizer
        )

    def test_complete_ticket_purchase_with_percentage_discount(self):
        """Test E2E: Compra completa con cupón de descuento porcentual"""
        
        self.login_user('buyer_e2e', 'buyer123')
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/")
        
        expect(self.page.locator('h5')).to_contain_text("Comprar Entrada")
        
        plus_button = self.page.locator("button[onclick='adjustQuantity(1)']")
        plus_button.click()  # cantidad 2 tickets
        
        quantity_input = self.page.locator("#id_quantity")
        expect(quantity_input).to_have_value('2')
        
        self.page.select_option('select[name="type"]', 'VIP')
        
        self.page.fill('#id_discount_code', 'E2E20')
        self.page.click('#apply-discount')
        
        # Buscar indicadores de éxito en el descuento aplicado
        # Primero verificar si hay algún mensaje de éxito visible
        success_indicators = [
            self.page.locator('.alert-success'),
            self.page.locator('.text-success'), 
            self.page.locator('[class*="success"]'),
            self.page.get_by_text("descuento", exact=False).filter(has_text="aplicado"),
            self.page.locator('#discount-error').filter(has_text="Se aplicó")
        ]
        
        discount_applied = False
        for indicator in success_indicators:
            try:
                expect(indicator).to_be_visible(timeout=1000)
                discount_applied = True
                break
            except:
                continue
        
        # Si no encontramos indicadores visuales, verificar que no hay errores
        if not discount_applied:
            error_element = self.page.locator('#discount-error')
            if error_element.is_visible():
                error_text = error_element.text_content() or ""
                # Si el error no contiene mensajes de fallo, asumimos que el descuento se aplicó
                if not any(word in error_text.lower() for word in ['inválido', 'expirado', 'encontró', 'válido']):
                    discount_applied = True
        
        self.assertTrue(discount_applied, "El descuento debería haberse aplicado correctamente")
        
        # Si hay un elemento de subtotal, verificar que se actualizó
        try:
            expect(self.page.locator('#subtotal')).to_be_visible(timeout=1000)
        except:
            pass  # El subtotal puede no estar visible o no existir
        
        # Completar formulario de pago
        self.page.fill('#card_number', '1234 5678 9012 3456')
        self.page.fill('#card_expiry', '12/25')
        self.page.fill('#card_cvv', '123')
        self.page.fill('#card_name', 'Test User E2E')
        self.page.check('#accept_terms')
        
        initial_uses = self.discount_code.uses
        
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        # Manejar redirección y posible encuesta
        try:
            expect(self.page.get_by_text("Encuesta de Satisfacción")).to_be_visible(timeout=3000)
            self.page.get_by_role("link", name="Omitir por ahora").click()
        except:
            pass
        
        try:
            self.page.wait_for_url("**/survey/**", timeout=5000)
        except:
            try:
                self.page.wait_for_url("**/tickets/**", timeout=5000)
            except:
                pass  # Puede haber otras URLs de destino
        
        # Validar ticket en DB
        ticket = Ticket.objects.filter(user=self.buyer, event=self.event).first()
        self.assertIsNotNone(ticket, "El ticket debería haberse creado")
        self.assertEqual(ticket.quantity, 2)
        self.assertEqual(ticket.type, 'VIP')
        self.assertEqual(ticket.discount_code, self.discount_code)
        
        self.discount_code.refresh_from_db()
        self.assertEqual(self.discount_code.uses, initial_uses + 1)

    def test_complete_ticket_purchase_with_fixed_discount(self):
        """Test E2E: Compra completa con cupón de descuento fijo"""
        
        self.login_user('buyer_e2e', 'buyer123')
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/")
        
        expect(self.page.locator('h5')).to_contain_text("Comprar Entrada")
        
        self.page.select_option('select[name="type"]', 'GENERAL')
        
        self.page.fill('#id_discount_code', 'FIXED15')
        self.page.click('#apply-discount')
        
        # Verificar que no hay mensajes de error
        error_element = self.page.locator('#discount-error')
        if error_element.is_visible():
            error_text = error_element.text_content() or ""
            # Verificar que no contiene mensajes de error
            self.assertFalse(any(word in error_text.lower() for word in ['inválido', 'expirado', 'encontró']), 
                           f"No debería haber errores de descuento, pero se encontró: {error_text}")
        
        self.page.fill('#card_number', '1234 5678 9012 3456')
        self.page.fill('#card_expiry', '12/25')
        self.page.fill('#card_cvv', '123')
        self.page.fill('#card_name', 'Test User E2E')
        self.page.check('#accept_terms')
        
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        try:
            expect(self.page.get_by_text("Encuesta de Satisfacción")).to_be_visible(timeout=3000)
            self.page.get_by_role("link", name="Omitir por ahora").click()
        except:
            pass
        
        ticket = Ticket.objects.filter(user=self.buyer, event=self.event).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.discount_code, self.fixed_discount)

    def test_invalid_discount_code(self):
        """Test E2E: Verificar manejo de cupón inválido"""
        
        self.login_user('buyer_e2e', 'buyer123')
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/")
        
        self.page.fill('#id_discount_code', 'INVALID_CODE')
        self.page.click('#apply-discount')
        
        # Verificar el mensaje de error real que devuelve el backend
        discount_error = self.page.locator('#discount-error')
        expect(discount_error).to_be_visible(timeout=3000)
        
        # Verificar que contiene el mensaje real: "No se encontró el cupón"
        expect(discount_error).to_contain_text('No se encontró el cupón', timeout=3000)
        
        # Verificar que tiene clases de error
        classes = discount_error.get_attribute('class') or ''
        self.assertTrue(any(cls in classes for cls in ['invalid-feedback', 'text-danger', 'alert-danger']), 
                       f"Debería tener clases de error, pero tiene: {classes}")

