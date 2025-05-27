import re
import datetime
from babel.dates import format_datetime
from django.utils import timezone
from playwright.sync_api import expect
from ...models import Event, User, Venue, Category # type: ignore
from .base import BaseE2ETest


class TestFavoriteE2E(BaseE2ETest):
    def setUp(self):
        super().setUp()

        self.venue = Venue.objects.create(
            name="Espacio 75", address="Calle 75", city="La Plata",
            capacity=150, contact="contacto@espacio75.com"
        )

        self.category = Category.objects.create(name="Stand-up", description="Humor en vivo")

        self.organizer = User.objects.create_user(
            username="organizador", password="password123", is_organizer=True
        )

        self.user = User.objects.create_user(
            username="usuario", password="password123"
        )

        scheduled_date = timezone.make_aware(datetime.datetime(2025, 8, 1, 21, 0))
        self.event = Event.objects.create(
            title="Show de Humor",
            description="Un espectáculo para reír a carcajadas",
            scheduled_at=scheduled_date,
            organizer=self.organizer,
            venue=self.venue
        )
        self.event.categories.add(self.category)

    def test_toggle_favorite_and_verify_in_list(self):
        """⭐️ Marca evento como favorito y verifica que aparece en la lista de favoritos"""
        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}/events/")

        # Click en el botón de estrella para marcar favorito
        self.page.get_by_role("button", name="Marcar como favorito").click()

        # Verificar que se ve como favorita (estrella llena)
        expect(self.page.locator("button.btn-fav-toggle i.bi-star-fill")).to_have_class(re.compile("text-warning"))

        # Ir a la vista de favoritos
        self.page.goto(f"{self.live_server_url}/favorites/")

        # Verificar que aparece en la tabla
        rows = self.page.locator("table.table-fav tbody tr")
        expect(rows).to_have_count(1)
        expect(rows.nth(0).locator("td").nth(0)).to_have_text("Show de Humor")

    def test_remove_favorite_and_verify_empty_state(self):
        """💔 Elimina un favorito y verifica que aparezca el estado vacío"""
        self.login_user("usuario", "password123")

        # Marcar como favorito
        self.page.goto(f"{self.live_server_url}/events/")
        self.page.get_by_role("button", name="Marcar como favorito").click()

        # Ir a favoritos
        self.page.goto(f"{self.live_server_url}/favorites/")

        # Forzar vista tabla si está en modo tarjetas
        toggle_button = self.page.locator("#toggleView")
        if "Ver como tabla" in toggle_button.inner_text():
            toggle_button.click()

        # Buscar la fila con el evento y quitar de favoritos
        row = self.page.locator("table.table-fav tbody tr").filter(has_text="Show de Humor")
        remove_button = row.locator("button.btn-fav-remove")
        remove_button.click()

        # Confirmar SweetAlert
        self.page.wait_for_selector(".swal2-confirm", timeout=5000)
        self.page.locator(".swal2-confirm").click()

        # Verificar mensaje de estado vacío
        expect(self.page.locator(".empty-state")).to_be_visible()
        expect(self.page.locator("h4")).to_have_text("Aún no tenés eventos favoritos")


    def test_toggle_card_view_and_back(self):
        """🔄 Cambiar de tabla a tarjetas y volver"""
        self.login_user("usuario", "password123")
        self.page.goto(f"{self.live_server_url}/events/")
        self.page.get_by_role("button", name="Marcar como favorito").click()
        self.page.goto(f"{self.live_server_url}/favorites/")

        # Cambiar a vista de tarjetas
        self.page.get_by_role("button", name="Ver como tarjetas").click()
        card_view = self.page.locator("#cardView")
        expect(card_view).not_to_have_class(re.compile("d-none"))

        # Volver a tabla
        self.page.get_by_role("button", name="Ver como tabla").click()
        table_view = self.page.locator(".table-wrapper-fav")
        expect(table_view).not_to_have_class(re.compile("d-none"))
