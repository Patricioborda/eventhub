import re

from playwright.sync_api import expect

from app.models import User
from app.test.test_e2e.base import BaseE2ETest


class RegistrationE2ETest(BaseE2ETest):
    """Pruebas E2E para el proceso de registro"""

    def test_registration_page_loads(self):
        """Verifica que la página de registro carga correctamente"""
        self.page.goto(f"{self.live_server_url}/accounts/register/")

        # Verificar que el formulario está presente
        expect(self.page.locator("form")).to_be_visible()
        expect(self.page.locator("input[name='csrfmiddlewaretoken']")).to_be_hidden()
        expect(self.page.locator("input[name='email']")).to_be_visible()
        expect(self.page.locator("input[name='username']")).to_be_visible()
        expect(self.page.locator("input[name='password']")).to_be_visible()
        expect(self.page.locator("input[name='password-confirm']")).to_be_visible()
        expect(self.page.locator("input[name='is-organizer']")).to_be_visible()
        expect(self.page.locator("button[type='submit']")).to_be_visible()

    def test_successful_registration(self):
        """Verifica el proceso de registro exitoso"""
        self.page.goto(f"{self.live_server_url}/accounts/register/")

        # Llenar el formulario con datos válidos
        self.page.get_by_label("Email").fill("nuevo@example.com")
        self.page.get_by_label("Usuario").fill("nuevo_usuario")
        self.page.get_by_label("Contraseña", exact=True).fill("password123")
        self.page.get_by_label("Confirmar contraseña").fill("password123")

        # Enviar el formulario
        self.page.click("button[type='submit']")

        # Verificar que se redirige a events
        self.page.wait_for_url(re.compile(f"{self.live_server_url}/events/.*"))

        # Verificar que el usuario fue creado en la base de datos
        self.assertTrue(User.objects.filter(username="nuevo_usuario").exists())

    def test_successful_registration_organizer(self):
        """Verifica el proceso de registro exitoso de un organizador"""
        self.page.goto(f"{self.live_server_url}/accounts/register/")

        # Llenar el formulario con datos válidos
        self.page.get_by_label("Email").fill("nuevo@example.com")
        self.page.get_by_label("Usuario").fill("nuevo_usuario")
        self.page.get_by_label("Contraseña", exact=True).fill("password123")
        self.page.get_by_label("Confirmar contraseña").fill("password123")
        self.page.get_by_label("Es organizador?").click()

        # Enviar el formulario
        self.page.click("button[type='submit']")

        # Verificar redirección y verificación en la base de datos
        self.page.wait_for_url(re.compile(f"{self.live_server_url}/events/.*"))
        self.assertTrue(User.objects.filter(username="nuevo_usuario").exists())

    def test_duplicate_email_registration(self):
        """Verifica el intento de registro con un email existente"""
        # Crear un usuario con el email que vamos a intentar usar
        user = self.create_test_user()

        self.page.goto(f"{self.live_server_url}/accounts/register/")

        # Llenar el formulario con un email existente
        self.page.get_by_label("Email").fill(user.email)
        self.page.get_by_label("Usuario").fill("otro_usuario")
        self.page.get_by_label("Contraseña", exact=True).fill("password123")
        self.page.get_by_label("Confirmar contraseña").fill("password123")

        # Enviar el formulario
        self.page.click("button[type='submit']")

        # Verificar error
        expect(self.page).to_have_url(re.compile(r".*/register"))
        error_message = self.page.get_by_text("Ya existe un usuario con este email")
        expect(error_message).to_be_visible()

    def test_duplicate_username_registration(self):
        """Verifica el intento de registro con un nombre de usuario existente"""
        user = self.create_test_user()

        self.page.goto(f"{self.live_server_url}/accounts/register/")

        # Llenar formulario con username existente
        self.page.get_by_label("Email").fill("otro@example.com")
        self.page.get_by_label("Usuario").fill(user.username)
        self.page.get_by_label("Contraseña", exact=True).fill("password123")
        self.page.get_by_label("Confirmar contraseña").fill("password123")

        # Verificar error
        self.page.click("button[type='submit']")
        expect(self.page).to_have_url(re.compile(r".*/register"))
        error_message = self.page.get_by_text("Ya existe un usuario con este nombre de usuario")
        expect(error_message).to_be_visible()

    def test_password_mismatch_registration(self):
        """Verifica el intento de registro con contraseñas que no coinciden"""
        self.page.goto(f"{self.live_server_url}/accounts/register/")

        # Llenar el formulario con contraseñas diferentes
        self.page.get_by_label("Email").fill("nuevo@example.com")
        self.page.get_by_label("Usuario").fill("nuevo_usuario")
        self.page.get_by_label("Contraseña", exact=True).fill("password123")
        self.page.get_by_label("Confirmar contraseña").fill("diferente456")

        # Verificar error
        self.page.click("button[type='submit']")
        expect(self.page).to_have_url(re.compile(r".*/register"))
        error_message = self.page.get_by_text("Las contraseñas no coinciden")
        expect(error_message).to_be_visible()


class LoginE2ETest(BaseE2ETest):
    """Pruebas E2E para el proceso de inicio de sesión"""

    def test_login_page_loads(self):
        """Verifica que la página de login carga correctamente"""
        self.page.goto(f"{self.live_server_url}/accounts/login/")

        # Verificar que el formulario está presente
        expect(self.page.locator("form")).to_be_visible()
        expect(self.page.locator("input[name='csrfmiddlewaretoken']")).to_be_hidden()
        expect(self.page.locator("input[name='username']")).to_be_visible()
        expect(self.page.locator("input[name='password']")).to_be_visible()
        expect(self.page.locator("button[type='submit']")).to_be_visible()

    def test_successful_login(self):
        """Verifica el proceso de login exitoso"""
        user = self.create_test_user()
        self.login_user(user.username, "password123")

        self.page.wait_for_url(f"{self.live_server_url}/")

        # Verificar que el navbar muestra opciones de usuario logueado
        navbar = self.page.locator("nav")
        expect(navbar).to_contain_text("Mis Tickets")
        expect(navbar).to_contain_text("Cerrar Sesión")
        
    def test_invalid_credentials_login(self):
        """Verifica el intento de login con credenciales inválidas"""
        self.login_user("usuario_inexistente", "password_incorrecto")

        # Verificar que permanecemos en la página de login
        expect(self.page).to_have_url(re.compile(r".*/login"))
        error_message = self.page.get_by_text("Usuario o contraseña incorrectos")
        expect(error_message).to_be_visible()

    def test_wrong_password_login(self):
        """Verifica el intento de login con contraseña incorrecta"""
        # Crear un usuario para probar
        user = self.create_test_user()

        # Intentar login con contraseña incorrecta
        self.login_user(user.username, "password_incorrecto")

        # Verificar error
        expect(self.page).to_have_url(re.compile(r".*/login"))
        error_message = self.page.get_by_text("Usuario o contraseña incorrectos")
        expect(error_message).to_be_visible()
