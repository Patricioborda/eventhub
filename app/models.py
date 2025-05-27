import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, User  # type: ignore
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


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

class Venue(models.Model):
    name = models.TextField(max_length=200)
    address = models.TextField()
    city = models.TextField(max_length=100)
    capacity = models.IntegerField()
    contact = models.TextField(max_length=100)

    def __str__(self):
        return f"{self.name} - {self.city}"

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_at = models.DateTimeField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organized_events")
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="events", null=True)  # Relación con Venue
    categories = models.ManyToManyField('Category', related_name='events')  # vinculado con Category
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @classmethod
    def validate(cls, title, description, venue, scheduled_at, categories):
        errors = {}

        # Validar título
        if not title or title.strip() == "":
            errors["title"] = "Por favor ingrese un título"

        # Validar descripción
        if not description or description.strip() == "":
            errors["description"] = "Por favor ingrese una descripción"

        # Validar fecha y hora futura
        if not scheduled_at:
            errors["scheduled_at"] = "Debe ingresar una fecha y hora para el evento"
        elif scheduled_at < timezone.now():
            errors["scheduled_at"] = "La fecha y hora del evento deben ser futuras"

        # Validar venue
        if not venue:
            errors["venue"] = "Debe seleccionar un lugar (venue) para el evento"

        # Validar categorías
        if not categories or len(categories) == 0:
            errors["categories"] = "Por favor seleccione al menos una categoría"

        return errors

    @classmethod
    def new(cls, title, description, venue, scheduled_at, organizer, categories):
        errors = Event.validate(title, description, venue, scheduled_at, categories)

        if len(errors.keys()) > 0:
            return False, errors

        event = Event.objects.create(
            title=title,
            description=description,
            venue=venue,
            scheduled_at=scheduled_at,
            organizer=organizer,
        )
        event.categories.set(categories)
        return True, None

    def update(self, title, description, venue, scheduled_at, organizer, categories):
        self.title = title or self.title
        self.description = description or self.description
        self.venue = venue or self.venue
        self.scheduled_at = scheduled_at or self.scheduled_at
        self.organizer = organizer or self.organizer

        if categories:
            self.categories.set(categories)

        self.save()

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)  # ← CAMPO NUEVO

    def __str__(self):
        return f"{self.title} - {self.user.username}"
# ------------------- Refund -------------------
class RefundRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refund_requests")
    ticket_code = models.CharField(max_length=100)
    reason = models.TextField()
    approved = models.BooleanField(null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    refund_percentage = models.FloatField(null=True, blank=True)

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
    # Destinatario específico (opcional)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications_received')
    # Evento para notificación masiva (opcional)
    event = models.ForeignKey('Event', null=True, blank=True, on_delete=models.CASCADE, related_name='notifications_event')
    # Indicador de notificación a todos los asistentes del evento
    to_all_event_attendees = models.BooleanField(default=False)
    # Contenido de la notificación
    title = models.CharField(max_length=100)
    message = models.TextField()
    # Prioridad de la notificación (por simplicidad, como texto o entero con choices)
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('normal', 'Normal'),
        ('high', 'Alta'),
    ]
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    # Fecha de creación (para registro)
    created_at = models.DateTimeField(auto_now_add=True)
    # (Opcional) campo para rastrear el creador de la notificación
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='notifications_created')
    is_read = models.BooleanField("Leída", default=False)
    def clean(self):
        """Validación para asegurar que solo un tipo de destino esté seleccionado."""
        super().clean()  # Llama a validaciones básicas primero
        # Caso 1: Notificación masiva a evento
        if self.to_all_event_attendees:
            if not self.event:
                raise ValidationError({'event': "Debe seleccionar un evento cuando 'a todos los asistentes' está marcado."})
            if self.user:
                raise ValidationError({'user': "No seleccione un usuario específico cuando la notificación es para todos los asistentes de un evento."})
        # Caso 2: Notificación a usuario específico
        else:
            if not self.user:
                raise ValidationError({'user': "Debe seleccionar un usuario destinatario o marcar la opción de notificar a todos los asistentes de un evento."})
            if self.event:
                # Opcional: impedir que se asocie un evento si no es notificación masiva
                raise ValidationError({'event': "No seleccione un evento al enviar una notificación a un usuario específico."})

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="notification_valid_target",
                check=(
                    models.Q(to_all_event_attendees=True, event__isnull=False, user__isnull=True) | 
                    models.Q(to_all_event_attendees=False, user__isnull=False, event__isnull=True)
                )
            )
        ]
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

from django.core.exceptions import ValidationError
from django.utils import timezone

class DiscountCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('fixed', 'Monto fijo ($)'),
        ('percent', 'Porcentaje (%)'),
    ]
    created_at = models.DateTimeField(default=timezone.now)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    valid_from = models.DateField()
    valid_until = models.DateField(blank=True, null=True)
    max_uses = models.PositiveIntegerField(blank=True, null=True)
    uses = models.PositiveIntegerField(default=0)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    event = models.ForeignKey('Event', on_delete=models.SET_NULL, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    apply_to_all = models.BooleanField(default=False)

    def clean(self):
        # Validar fechas
        if self.valid_until and self.valid_from > self.valid_until:
            raise ValidationError({'valid_until': 'La fecha de finalización debe ser mayor o igual a la fecha de inicio.'})

        if self.valid_from < timezone.now().date():
            raise ValidationError({'valid_from': 'La fecha de inicio no puede ser en el pasado.'})
            # Validar longitud de descripción
        if self.description and len(self.description) > MAX_DESCRIPTION_LENGTH:
            raise ValidationError({'description': f'La descripción no puede tener más de {MAX_DESCRIPTION_LENGTH} caracteres.'})

        # Validar valor del descuento
        if self.discount_value <= 0:
            raise ValidationError({'discount_value': 'El valor del descuento debe ser mayor que cero.'})

        if self.discount_type == 'percent' and (self.discount_value > 100 or self.discount_value <= 0):
            raise ValidationError({'discount_value': 'El porcentaje debe estar entre 1 y 100.'})

        # Validar usos
        if self.max_uses is not None and self.uses > self.max_uses:
            raise ValidationError({'uses': 'Las veces usadas no pueden superar el máximo de usos permitidos.'})

        # Validar evento y apply_to_all
        if self.apply_to_all and self.event is not None:
            raise ValidationError({'event': 'No se puede asignar un evento si aplica a todos los eventos.'})

        if not self.apply_to_all and self.event is None:
            raise ValidationError({'event': 'Debe seleccionar un evento o marcar que aplica a todos.'})

    def __str__(self):
        return self.code

