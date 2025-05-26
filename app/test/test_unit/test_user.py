from django.test import TestCase

from app.models import User


class UserModelTest(TestCase):
    def setUp(self):
        # Crear un usuario para probar la validación de duplicados
        self.existing_user = User.objects.create_user(
            username="usuario_existente", email="existente@example.com", password="password123"
        )

    def test_create_user(self):
        user = User.objects.create_user(username="testuser", password="testpass123")
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff) 
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_organizer)

    def test_create_organizer(self):
        organizer = User.objects.create_user(
            username="organizeruser", password="testpass123", is_organizer=True
        )
        self.assertTrue(organizer.is_organizer)

    def test_missing_email(self):
        """Test que valida que se retorne un error cuando el email es None"""
        errors = User.validate_new_user(
            email=None,
            username="nuevo_usuario",
            password="password123",
            password_confirm="password123",
        )
        self.assertIn("email", errors)
        self.assertEqual(errors["email"], "El email es requerido")

    def test_duplicate_email(self):
        """Test que valida que se retorne un error cuando el email ya existe"""
        errors = User.validate_new_user(
            email="existente@example.com",
            username="otro_usuario",
            password="password123",
            password_confirm="password123",
        )
        self.assertIn("email", errors)
        self.assertEqual(errors["email"], "Ya existe un usuario con este email")

    def test_missing_username(self):
        """Test que valida que se retorne un error cuando el username es None"""
        errors = User.validate_new_user(
            email="nuevo@example.com",
            username=None,
            password="password123",
            password_confirm="password123",
        )
        self.assertIn("username", errors)
        self.assertEqual(errors["username"], "El username es requerido")

    def test_duplicate_username(self):
        """Test que valida que se retorne un error cuando el username ya existe"""
        errors = User.validate_new_user(
            email="nuevo@example.com",
            username="usuario_existente",
            password="password123",
            password_confirm="password123",
        )
        self.assertIn("username", errors)
        self.assertEqual(errors["username"], "Ya existe un usuario con este nombre de usuario")

    def test_missing_passwords(self):
        """Test que valida que se retorne un error cuando alguna contraseña es None"""
        # Caso 1: password is None
        errors1 = User.validate_new_user(
            email="nuevo@example.com",
            username="nuevo_usuario",
            password=None,
            password_confirm="password123",
        )
        self.assertIn("password", errors1)
        self.assertEqual(errors1["password"], "Las contraseñas son requeridas")

        # Caso 2: password_confirm is None
        errors2 = User.validate_new_user(
            email="nuevo@example.com",
            username="nuevo_usuario",
            password="password123",
            password_confirm=None,
        )
        self.assertIn("password", errors2)
        self.assertEqual(errors2["password"], "Las contraseñas son requeridas")

    def test_password_mismatch(self):
        """Test que valida que se retorne un error cuando las contraseñas no coinciden"""
        errors = User.validate_new_user(
            email="nuevo@example.com",
            username="nuevo_usuario",
            password="password123",
            password_confirm="otrapassword456",
        )
        self.assertIn("password", errors)
        self.assertEqual(errors["password"], "Las contraseñas no coinciden")

    def test_valid_user(self):
        """Test que valida que no se retornen errores cuando todos los datos son válidos"""
        errors = User.validate_new_user(
            email="nuevo@example.com",
            username="nuevo_usuario",
            password="password123",
            password_confirm="password123",
        )
        self.assertEqual(errors, {})

    def test_multiple_errors(self):
        """Test que valida que se retornen múltiples errores cuando corresponda"""
        errors = User.validate_new_user(
            email="existente@example.com",
            username="usuario_existente",
            password="password123",
            password_confirm="diferente456",
        )
        self.assertEqual(len(errors), 3)  # Debe haber errores para email, username y password
        self.assertIn("email", errors)
        self.assertIn("username", errors)
        self.assertIn("password", errors)
