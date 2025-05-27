import datetime
from django.utils import timezone
from django.db import models
from playwright.sync_api import expect

from app.models import User, Venue, Category, Event, Ticket
from app.test.test_e2e.base import BaseE2ETest


class TicketLimitE2ETest(BaseE2ETest):
    """Test E2E para verificar el límite de 4 entradas por evento"""

    def setUp(self):
        super().setUp()
        
        # Crear usuario regular
        self.user = User.objects.create_user(
            username="usuario_comprador",
            email="comprador@example.com",
            password="password123",
            is_organizer=False
        )
        
        # Crear organizador
        self.organizer = User.objects.create_user(
            username="organizador",
            email="organizador@example.com",
            password="password123",
            is_organizer=True
        )
        
        # Crear venue y category
        self.venue = Venue.objects.create(
            name="Teatro Municipal",
            address="Calle 123",
            city="La Plata",
            capacity=500,
            contact="contacto@teatro.com"
        )
        
        self.category = Category.objects.create(
            name="Teatro",
            description="Obras teatrales"
        )
        
        # Crear evento futuro
        self.event = Event.objects.create(
            title="Obra de Teatro Espectacular",
            description="Una obra increíble que no te puedes perder",
            scheduled_at=timezone.now() + datetime.timedelta(days=10),
            organizer=self.organizer,
            venue=self.venue
        )
        self.event.categories.add(self.category)

    def test_usuario_no_puede_comprar_mas_de_4_entradas_por_evento(self):
        """
        Test E2E que verifica que un usuario no puede comprar más de 4 entradas
        para un mismo evento. Simula el flujo completo desde el navegador.
        """
        # PASO 1: Login del usuario
        self.login_user("usuario_comprador", "password123")
        
        # PASO 2: Ir a la página de eventos
        self.page.goto(f"{self.live_server_url}/events/")
        expect(self.page.locator("h1")).to_have_text("Eventos")
        
        # PASO 3: Hacer clic en "Ver Detalle" del evento
        self.page.get_by_role("link", name="Ver Detalle").first.click()
        
        # Verificar que estamos en la página de detalle del evento
        expect(self.page.locator("h1")).to_have_text("Obra de Teatro Espectacular")
        
        # PASO 4: Hacer clic en el botón "Comprar Ticket"
        self.page.get_by_role("link", name="Comprar Ticket").click()
        
        # Verificar que estamos en la página de compra
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/create/{self.event.id}/")
        expect(self.page.locator("h5")).to_have_text("Comprar Entrada")
        
        # PASO 5: Comprar 3 entradas (primera compra)
        quantity_input = self.page.locator("#id_quantity")
        quantity_input.fill("3")
        
        # Seleccionar tipo de entrada
        self.page.select_option("select[name='type']", "GENERAL")
        
        # Llenar datos de la tarjeta (simulados)
        self.page.fill("#card_number", "1234 5678 9012 3456")
        self.page.fill("#card_expiry", "12/25")
        self.page.fill("#card_cvv", "123")
        self.page.fill("#card_name", "Juan Perez")
        
        # Aceptar términos y condiciones
        self.page.check("#accept_terms")
        
        # PASO 6: Confirmar primera compra
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        # Verificar que la compra fue exitosa y redirigió a mis tickets
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")
        
        # Verificar que se creó el ticket con 3 entradas
        ticket = Ticket.objects.filter(user=self.user, event=self.event).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.quantity, 3)
        
        # PASO 7: Intentar comprar 2 entradas más (debería fallar)
        # Volver a la página de compra
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/")
        
        # Verificar que se muestra información de entradas ya compradas
        expect(self.page.get_by_text("Ya has comprado 3 para este evento")).to_be_visible()
        
        # Intentar comprar 2 entradas más
        quantity_input = self.page.locator("#id_quantity")
        quantity_input.fill("2")
        
        # Llenar nuevamente los datos de la tarjeta
        self.page.fill("#card_number", "1234 5678 9012 3456")
        self.page.fill("#card_expiry", "12/25")
        self.page.fill("#card_cvv", "123")
        self.page.fill("#card_name", "Juan Perez")
        
        # Aceptar términos y condiciones
        self.page.check("#accept_terms")
        
        # PASO 8: Intentar confirmar la segunda compra
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        # PASO 9: Verificar que aparece el mensaje de error
        expect(self.page.get_by_text("No puedes comprar más de 4 entradas por evento. Ya compraste 3.")).to_be_visible()
        
        # Verificar que permanecemos en la página de compra (no redirigió)
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/create/{self.event.id}/")
        
        # PASO 10: Verificar que no se creó un segundo ticket
        tickets_count = Ticket.objects.filter(user=self.user, event=self.event).count()
        self.assertEqual(tickets_count, 1)
        
        # Verificar que la cantidad total sigue siendo 3
        total_quantity = Ticket.objects.filter(
            user=self.user, 
            event=self.event
        ).aggregate(total=models.Sum('quantity'))['total']
        self.assertEqual(total_quantity, 3)

    def test_usuario_puede_comprar_exactamente_4_entradas(self):
        """
        Test E2E que verifica que un usuario SÍ puede comprar exactamente 4 entradas
        """
        # Login del usuario
        self.login_user("usuario_comprador", "password123")
        
        # Ir a la página de compra
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/")
        
        # Comprar exactamente 4 entradas
        quantity_input = self.page.locator("#id_quantity")
        quantity_input.fill("4")
        
        # Llenar datos de la tarjeta
        self.page.fill("#card_number", "1234 5678 9012 3456")
        self.page.fill("#card_expiry", "12/25")
        self.page.fill("#card_cvv", "123")
        self.page.fill("#card_name", "Juan Perez")
        
        # Aceptar términos y condiciones
        self.page.check("#accept_terms")
        
        # Confirmar compra
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        # Verificar que la compra fue exitosa
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")
        
        # Verificar en la base de datos
        ticket = Ticket.objects.filter(user=self.user, event=self.event).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.quantity, 4)

    def test_usuario_no_puede_comprar_mas_de_4_en_compra_unica(self):
        """
        Test E2E que verifica que un usuario no puede comprar más de 4 entradas
        en una sola compra
        """
        # Login del usuario
        self.login_user("usuario_comprador", "password123")
        
        # Ir a la página de compra
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/")
        
        # Intentar comprar 5 entradas de una vez
        quantity_input = self.page.locator("#id_quantity")
        quantity_input.fill("5")
        
        # Llenar datos de la tarjeta
        self.page.fill("#card_number", "1234 5678 9012 3456")
        self.page.fill("#card_expiry", "12/25")
        self.page.fill("#card_cvv", "123")
        self.page.fill("#card_name", "Juan Perez")
        
        # Aceptar términos y condiciones
        self.page.check("#accept_terms")
        
        # Intentar confirmar compra
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        # Verificar que aparece el mensaje de error
        expect(self.page.get_by_text("No puedes comprar más de 4 entradas por evento. Ya compraste 0.")).to_be_visible()
        
        # Verificar que no se creó ningún ticket
        tickets_count = Ticket.objects.filter(user=self.user, event=self.event).count()
        self.assertEqual(tickets_count, 0)

    def test_diferentes_usuarios_pueden_comprar_4_entradas_cada_uno(self):
        """
        Test E2E que verifica que diferentes usuarios pueden comprar 
        4 entradas cada uno para el mismo evento
        """
        # Crear segundo usuario
        user2 = User.objects.create_user(
            username="segundo_usuario",
            email="segundo@example.com",
            password="password123",
            is_organizer=False
        )
        
        # PRIMER USUARIO: Comprar 4 entradas
        self.login_user("usuario_comprador", "password123")
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/")
        
        self.page.fill("#id_quantity", "4")
        self.page.fill("#card_number", "1234 5678 9012 3456")
        self.page.fill("#card_expiry", "12/25")
        self.page.fill("#card_cvv", "123")
        self.page.fill("#card_name", "Juan Perez")
        self.page.check("#accept_terms")
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")
        
        # Cerrar sesión
        self.page.get_by_role("button", name="Cerrar Sesión").click()
        
        # SEGUNDO USUARIO: También puede comprar 4 entradas
        self.login_user("segundo_usuario", "password123")
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/")
        
        self.page.fill("#id_quantity", "4")
        self.page.fill("#card_number", "1234 5678 9012 3456")
        self.page.fill("#card_expiry", "12/25")
        self.page.fill("#card_cvv", "123")
        self.page.fill("#card_name", "Maria Lopez")
        self.page.check("#accept_terms")
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")
        
        # Verificar que ambos usuarios tienen sus tickets
        tickets_user1 = Ticket.objects.filter(user=self.user, event=self.event).first()
        tickets_user2 = Ticket.objects.filter(user=user2, event=self.event).first()
        
        self.assertEqual(tickets_user1.quantity, 4)
        self.assertEqual(tickets_user2.quantity, 4)