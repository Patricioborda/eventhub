from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid

# ------------------- Usuario -------------------
class User(AbstractUser):
    is_organizer = models.BooleanField("¿Es organizador?", default=False)

    @classmethod
    def validate_new_user(cls, email, username, password, password_confirm):
        errors = {}

        if email is None:
            errors["email"] = "El email es requerido"
        elif User.objects.filter(email=email).exists():
            errors["email"] = "Ya existe un usuario con este email"

        if username is None:
            errors["username"] = "El username es requerido"
        elif User.objects.filter(username=username).exists():
            errors["username"] = "Ya existe un usuario con este nombre de usuario"

        if password is None or password_confirm is None:
            errors["password"] = "Las contraseñas son requeridas"
        elif password != password_confirm:
            errors["password"] = "Las contraseñas no coinciden"

        return errors

# ------------------- Evento -------------------
class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_at = models.DateTimeField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organized_events")
    categories = models.ManyToManyField('Category', related_name='events')  # vinculado con Category
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @classmethod
    def validate(cls, title, description, scheduled_at, categories):
        errors = {}

        if not title:
            errors["title"] = "Por favor ingrese un título"

        if not description:
            errors["description"] = "Por favor ingrese una descripción"

        if not categories or len(categories) == 0:
            errors["categories"] = "Por favor seleccione al menos una categoría"

        return errors

    @classmethod
    def new(cls, title, description, scheduled_at, organizer, categories):
        errors = Event.validate(title, description, scheduled_at, categories)

        if len(errors.keys()) > 0:
            return False, errors

        event = Event.objects.create(
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            organizer=organizer,
        )
        event.categories.set(categories)
        return True, None

    def update(self, title, description, scheduled_at, organizer, categories):
        self.title = title or self.title
        self.description = description or self.description
        self.scheduled_at = scheduled_at or self.scheduled_at
        self.organizer = organizer or self.organizer

        if categories:
            self.categories.set(categories)

        self.save()

# ------------------- Refund -------------------
class RefundRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refund_requests")
    ticket_code = models.CharField(max_length=100)
    reason = models.TextField()
    approved = models.BooleanField(null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def validate(cls, ticket_code, reason):
        errors = {}

        if not ticket_code or ticket_code.strip() == "":
            errors["ticket_code"] = "El código del ticket es obligatorio"

        if not reason or reason.strip() == "":
            errors["reason"] = "Debe indicar un motivo para el reembolso"

        return errors

    def approve(self):
        self.approved = True
        self.approval_date = timezone.now()
        self.save()

    def reject(self):
        self.approved = False
        self.approval_date = timezone.now()
        self.save()

    def __str__(self):
        return f"RefundRequest {self.id} by {self.user.username}"  # type: ignore

    @property
    def ticket(self):
        """
        Devuelve el objeto Ticket asociado a este ticket_code
        o None si no existe.
        """
        try:
            return Ticket.objects.get(ticket_code=self.ticket_code)
        except Ticket.DoesNotExist:
            return None

    @property
    def event_title(self):
        """
        Saca el título del evento a través del Ticket.
        """
        t = self.ticket
        return t.event.title if t else "—"
# ------------------- Ticket -------------------
class Ticket(models.Model):
    TICKETS_TYPES = [
        ('GENERAL', 'General'),
        ('VIP', 'Vip'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name="Evento"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name="Comprador"
    )
    buy_date = models.DateField(
        auto_now_add=True,
        verbose_name="Fecha de compra"
    )
    ticket_code = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name="Código del ticket"
    )
    quantity = models.PositiveIntegerField(
        verbose_name="Cantidad de entradas"
    )
    type = models.CharField(
        max_length=10,
        choices=TICKETS_TYPES,
        default='GENERAL',
        verbose_name="Tipo de entrada"
    )

    def __str__(self):
        return f"{self.ticket_code} - {self.type} - {self.event.title}"

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            self.ticket_code = str(uuid.uuid4()).replace('-', '')[:10].upper()
        super().save(*args, **kwargs)

# ------------------- Notificación -------------------
class Notification(models.Model):
    PRIORITY_CHOICES = [
        ("HIGH", "Alta"),
        ("MEDIUM", "Media"),
        ("LOW", "Baja"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Destinatario",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField("Título", max_length=60)
    message = models.TextField("Mensaje", max_length=280)
    created_at = models.DateTimeField("Creado", auto_now_add=True)
    priority = models.CharField(
        "Prioridad", max_length=6, choices=PRIORITY_CHOICES, default="LOW"
    )
    is_read = models.BooleanField("Leída", default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return f"{self.title} → {self.user.username}"

# ------------------- Categoría -------------------
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @classmethod
    def validate(cls, name, description):
        errors = {}

        if name == "":
            errors["name"] = "Por favor ingrese nombre de categoría."

        if description == "":
            errors["description"] = "Por favor ingrese una descripción"

        return errors

######### feature/rating #########    
class Rating(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    title = models.CharField(max_length=100)
    text = models.TextField(blank=True)
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')  # Un usuario solo puede calificar una vez
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}★ - {self.title} ({self.user.username})"
