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
        # Crear ticket previo de 4 entradas
        Ticket.objects.create(user=self.user, event=self.event, quantity=4, type="GENERAL")

        self.login_user("usuario_comprador", "password123")
        self.page.goto(self.live_server_url + f"/tickets/create/{self.event.id}/") # type: ignore

        # Esperar que la página cargue
        expect(self.page.locator("h5")).to_have_text("Comprar Entrada")

        # Verificamos que el input tenga como máximo permitido "0"
        max_attr = self.page.get_attribute("#id_quantity", "max")
        self.assertEqual(max_attr, "0")

        # Intentamos igual poner "1" a mano
        self.page.fill("#id_quantity", "1")

        # Click en el botón de compra
        self.page.click("text=Confirmar compra")

        # Verificamos que se muestre el mensaje de error correspondiente


        expect(self.page.locator(".text-danger")).to_contain_text(
            "No puedes comprar más de 4 entradas por evento"
        )

    def test_usuario_puede_comprar_exactamente_4_entradas(self):
        """
        Test E2E que verifica que un usuario SÍ puede comprar exactamente 4 entradas
        """
        # Login del usuario
        self.login_user("usuario_comprador", "password123")
        
        # Ir a la página de compra
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/") # type: ignore
        
        # Comprar exactamente 4 entradas usando botones +/-
        plus_button = self.page.locator("button[onclick='adjustQuantity(1)']")
        plus_button.click()  # 2
        plus_button.click()  # 3
        plus_button.click()  # 4
        
        # Verificar que la cantidad es 4
        expect(self.page.locator("#id_quantity")).to_have_value("4")
        
        # Llenar datos de la tarjeta
        self.page.fill("#card_number", "1234 5678 9012 3456")
        self.page.fill("#card_expiry", "12/25")
        self.page.fill("#card_cvv", "123")
        self.page.fill("#card_name", "Juan Perez")
        self.page.check("#accept_terms")
        
        # Confirmar compra
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        # NUEVO: Manejar la encuesta de satisfacción
        try:
            expect(self.page.get_by_text("Encuesta de Satisfacción")).to_be_visible(timeout=3000)
            self.page.get_by_role("link", name="Omitir por ahora").click()
        except:
            pass
        
        # Verificar que la compra fue exitosa
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")
        
        # Verificar en la base de datos
        ticket = Ticket.objects.filter(user=self.user, event=self.event).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.quantity, 4) # type: ignore
        
        # PASO EXTRA: Verificar que ahora no puede comprar más
        self.page.goto(f"{self.live_server_url}/events/{self.event.id}/") # type: ignore
        
        # Buscar el mensaje de advertencia
        warning_message = self.page.locator(".alert-warning")
        expect(warning_message).to_be_visible()
        expect(warning_message).to_contain_text("No puedes comprar entradas")

    def test_boton_mas_no_permite_superar_limite(self):
        """
        Test que verifica que el botón + no permite superar el límite disponible
        """
        # Crear un ticket existente de 3 entradas para el usuario
        Ticket.objects.create(user=self.user, event=self.event, quantity=3, type="GENERAL")
        
        # Login del usuario
        self.login_user("usuario_comprador", "password123")
        
        # Ir a la página de compra (aunque no debería poder acceder)
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/") # type: ignore
        
        # El input debería tener data-max="1" (solo puede comprar 1 más)
        quantity_input = self.page.locator("#id_quantity")
        max_value = quantity_input.get_attribute("data-max")
        self.assertEqual(max_value, "1")
        
        # Intentar hacer clic en + múltiples veces
        plus_button = self.page.locator("button[onclick='adjustQuantity(1)']")
        plus_button.click()  # Debería quedarse en 1 (no puede superar data-max)
        plus_button.click()  # Debería quedarse en 1
        plus_button.click()  # Debería quedarse en 1
        
        # Verificar que se mantiene en 1
        expect(quantity_input).to_have_value("1")

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
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/") # type: ignore
        
        # Usar botones para llegar a 4
        plus_button = self.page.locator("button[onclick='adjustQuantity(1)']")
        plus_button.click()  # 2
        plus_button.click()  # 3
        plus_button.click()  # 4
        
        self.page.fill("#card_number", "1234 5678 9012 3456")
        self.page.fill("#card_expiry", "12/25")
        self.page.fill("#card_cvv", "123")
        self.page.fill("#card_name", "Juan Perez")
        self.page.check("#accept_terms")
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        # NUEVO: Manejar la encuesta de satisfacción
        try:
            expect(self.page.get_by_text("Encuesta de Satisfacción")).to_be_visible(timeout=3000)
            self.page.get_by_role("link", name="Omitir por ahora").click()
        except:  # noqa: E722
            pass
        
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")
        
        # Cerrar sesión
        self.page.get_by_role("button", name="Cerrar Sesión").click()
        
        # SEGUNDO USUARIO: También puede comprar 4 entradas
        self.login_user("segundo_usuario", "password123")
        
        # Verificar que el segundo usuario VE el botón (no tiene límite alcanzado)
        self.page.goto(f"{self.live_server_url}/events/{self.event.id}/") # type: ignore
        expect(self.page.get_by_role("link", name="Comprar Ticket")).to_be_visible()
        
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/") # type: ignore
        
        # Usar botones para llegar a 4
        plus_button = self.page.locator("button[onclick='adjustQuantity(1)']")
        plus_button.click()  # 2
        plus_button.click()  # 3
        plus_button.click()  # 4
        
        self.page.fill("#card_number", "1234 5678 9012 3456")
        self.page.fill("#card_expiry", "12/25")
        self.page.fill("#card_cvv", "123")
        self.page.fill("#card_name", "Maria Lopez")
        self.page.check("#accept_terms")
        self.page.get_by_role("button", name="Confirmar compra").click()
        
        # NUEVO: Manejar la encuesta de satisfacción
        try:
            expect(self.page.get_by_text("Encuesta de Satisfacción")).to_be_visible(timeout=3000)
            self.page.get_by_role("link", name="Omitir por ahora").click()
        except:
            pass
        
        expect(self.page).to_have_url(f"{self.live_server_url}/tickets/")
        
        # Verificar que ambos usuarios tienen sus tickets
        tickets_user1 = Ticket.objects.filter(user=self.user, event=self.event).first()
        tickets_user2 = Ticket.objects.filter(user=user2, event=self.event).first()
        
        self.assertEqual(tickets_user1.quantity, 4) # type: ignore
        self.assertEqual(tickets_user2.quantity, 4) # type: ignore

    def test_no_se_pueden_comprar_entradas_si_el_evento_esta_lleno(self):
        """
        Test E2E que verifica que NO se pueden comprar entradas si se alcanzó la capacidad del evento.
        """

        # Establecemos una capacidad pequeña para forzar fácilmente el límite
        self.venue.capacity = 5
        self.venue.save()

        # Creamos 5 tickets con distintos usuarios para llenar el evento
        for i in range(5):
            nuevo_usuario = User.objects.create_user(
                username=f"user_{i}",
                email=f"user{i}@example.com",
                password="123456"
            )
            Ticket.objects.create(user=nuevo_usuario, event=self.event, quantity=1, type="GENERAL")

        # Creamos un usuario nuevo que intentará comprar
        cliente_extra = User.objects.create_user(
            username="cliente_extra",
            email="extra@example.com",
            password="password123"
        )

        # Login con el nuevo usuario
        self.login_user("cliente_extra", "password123")

        # Ir al detalle del evento
        self.page.goto(f"{self.live_server_url}/events/{self.event.id}/")  # type: ignore

        # Verificar que NO aparece el botón de compra
        expect(self.page.get_by_role("link", name="Comprar Ticket")).to_have_count(0)

        # Intentar ir directo a la URL de compra
        self.page.goto(f"{self.live_server_url}/tickets/create/{self.event.id}/")  # type: ignore

        # Verifica que muestra un mensaje claro de cupo agotado (adaptá si el texto cambia)
        expect(self.page.locator(".alert-danger, .alert, .mensaje-cupo-agotado")).to_contain_text("Cupo agotado")


        # Confirmar que no se creó ningún ticket nuevo para ese usuario
        tickets_para_extra = Ticket.objects.filter(user=cliente_extra, event=self.event)
        self.assertEqual(tickets_para_extra.count(), 0)
