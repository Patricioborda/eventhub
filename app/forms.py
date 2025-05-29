from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Category, Comment, Event, Notification, Rating, RefundRequest, Ticket, Venue, SatisfactionSurvey


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['title', 'content']  # Incluye 'title'
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Escribe un título para tu comentario...'}),
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escribe tu comentario aquí...'}),
        }


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ['name', 'address', 'city', 'capacity', 'contact']




User = get_user_model()
# --- Formulario de Refunds ---
class RefundRequestForm(forms.ModelForm):
    MOTIVO_CHOICES = [
        ('', 'Seleccione un motivo…'),
        ('enfermedad', 'Enfermedad comprobable'),
        ('fuerza_mayor', 'Fuerza mayor (accidente, urgencia familiar)'),
        ('clima_extremo', 'Clima extremo o fenómenos naturales'),
        ('covid', 'Restricciones o contagio de COVID-19'),
        ('problema_transporte', 'Problema de transporte terrestre'),
        ('agenda_conflicto', 'Conflicto de agenda o cambio de planes'),
        ('otro', 'Otro'),
    ]

    motivo = forms.ChoiceField(
        choices=MOTIVO_CHOICES,
        label="Motivo de reembolso",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={'required': 'Debes seleccionar un motivo.'}
    )
    detalles = forms.CharField(
        label="Detalles adicionales",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control"})
    )
    acepta_politicas = forms.BooleanField(
        label="He leído y acepto las políticas de reembolso",
        required=True,
        error_messages={'required': 'Debes aceptar las políticas para continuar.'},
    )

    class Meta:
        model = RefundRequest
        fields = ["ticket_code"]
        widgets = {
            "ticket_code": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Al editar, no mostramos el checkbox de políticas
        if self.instance and self.instance.pk:
            self.fields.pop('acepta_politicas')
            # descomponer reason en motivo + detalles
            reason = self.instance.reason or ""
            motivo_text, detalles_text = (reason.split(": ", 1) + [""])[:2]
            key = next((k for k, v in self.MOTIVO_CHOICES if v == motivo_text), 'otro')
            self.initial.update({'motivo': key, 'detalles': detalles_text})

    def clean_ticket_code(self):
        code = self.cleaned_data.get("ticket_code", "").strip()
        if not code:
            raise ValidationError("El código de ticket es obligatorio.")

        # 1) Verificamos que exista el Ticket
        try:
            ticket = Ticket.objects.get(ticket_code=code)
        except Ticket.DoesNotExist:
            raise ValidationError("Código de ticket inválido: no existe ese Ticket.")

        # 2) Calculamos cuántos días faltan para el evento
        event_date = ticket.event.scheduled_at.date()
        today = timezone.localdate()
        dias_para_evento = (event_date - today).days

        # 3) Aplicamos la política de reembolso
        if dias_para_evento < 2:
            # Menos de 48h → no hay reembolso
            raise ValidationError(
                "Sin reembolso: faltan menos de 48 horas para el evento."
            )
        elif dias_para_evento < 7:
            # Entre 2 y 7 días → reembolso 50%
            # Guardamos el porcentaje para usarlo luego (por ejemplo, en la vista)
            self.cleaned_data['refund_percentage'] = 0.5
        else:
            # 7 días o más → reembolso 100%
            self.cleaned_data['refund_percentage'] = 1.0

        # 4) Guardamos el ticket por si lo necesitas más tarde
        self.cleaned_data['ticket_obj'] = ticket

        return code

    def clean_detalles(self):
        text = self.cleaned_data.get('detalles', '').strip()
        if len(text) > 500:
            raise ValidationError("Detalles demasiado largos (máx. 500 caracteres).")
        return text

    def clean(self):
        cleaned = super().clean()
        ticket_code = cleaned.get('ticket_code')

        # Validación de duplicados solo al crear
        if ticket_code and self.user and self.instance.pk is None:
            existe = RefundRequest.objects.filter(
                user=self.user,
                ticket_code=ticket_code,
                approved__isnull=True
            ).exists()
            if existe:
                self.add_error(None, "Ya tenés una solicitud pendiente para ese ticket.")
        return cleaned

    def save(self, commit=True):
        # reconstruir el campo reason
        motivo_label = dict(self.MOTIVO_CHOICES)[self.cleaned_data['motivo']]
        detalles = self.cleaned_data.get('detalles', '').strip()
        razon = motivo_label + (f": {detalles}" if detalles else "")

        instance = super().save(commit=False)
        instance.reason = razon
        if commit:
            instance.save()
        return instance

# --- Formulario de Tickets ---
class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['quantity', 'type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # INPUT de cantidad
        self.fields['quantity'].widget.attrs.update({
            'class': 'form-control text-center',
            'min': '1',
            'id': 'id_quantity',
            'inputmode': 'numeric',
            # 'max' y 'data-max' los ponemos dinámicos en la vista
        })
        self.fields['quantity'].initial = 1

        # SELECT de tipo
        self.fields['type'].widget.attrs.update({
            'class': 'form-select',
            'id': 'id_type',           
        })
        self.fields['type'].initial = 'GENERAL'

class TicketOrganizerEditForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['type', 'quantity']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
# --- Formulario de Notificaciones ---
class NotificationForm(forms.ModelForm):
    TARGET_CHOICES = [
        ('event', 'Todos los asistentes de un evento'),
        ('user', 'Un usuario específico')
    ]
    # Campo auxiliar para el tipo de destinatario (radio buttons)
    target = forms.ChoiceField(choices=TARGET_CHOICES, widget=forms.RadioSelect, label='Destino')
    # Campos de destino condicionales
    event = forms.ModelChoiceField(queryset=Event.objects.none(), required=False, label='Evento')
    user = forms.ModelChoiceField(queryset=User.objects.none(), required=False, label='Usuario')
    
    class Meta:
        model = Notification
        fields = ['target', 'event', 'user', 'title', 'message', 'priority', 'to_all_event_attendees']
        widgets = {
            'to_all_event_attendees': forms.HiddenInput()  # ocultamos el checkbox real
        }
        labels = {
            'title': 'Título',
            'message': 'Mensaje',
            'priority': 'Prioridad',
        }
    
    def __init__(self, *args, **kwargs):
        # Recibimos el usuario actual para filtrar opciones
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Ajustar el queryset de eventos y usuarios según el usuario logueado
        if user:
            # Mostrar solo eventos organizados por el usuario (asumiendo Event.organizer relaciona al organizador)
            self.fields['event'].queryset = Event.objects.filter(organizer=user) # type: ignore
            # Mostrar solo usuarios que tengan tickets en eventos del organizador (asistentes de cualquiera de sus eventos)
            self.fields['user'].queryset = User.objects.filter(tickets__event__organizer=user).distinct() # type: ignore
        # Inicializar selección por defecto: ninguno (se fuerza al usuario a elegir)
        self.fields['target'].initial = None
        # Ocultar el campo booleano en el formulario (lo controlaremos manualmente)
        self.fields['to_all_event_attendees'].initial = False

    def clean(self):
        cleaned_data = super().clean()
        target_choice = cleaned_data.get('target')
        event = cleaned_data.get('event')
        user = cleaned_data.get('user')
        # Validar según la opción de destino elegida
        if target_choice == 'event':
            # Debe haber un evento y marcar checkbox de "todos asistentes"
            if not event:
                raise forms.ValidationError("Por favor, seleccioná un evento para enviar la notificación.")
            # Forzamos to_all_event_attendees a True porque el usuario eligió evento
            cleaned_data['to_all_event_attendees'] = True
            cleaned_data['user'] = None  # Asegurarse de no usar campo de usuario
        elif target_choice == 'user':
            # Debe haber un usuario
            if not user:
                raise forms.ValidationError("Por favor, seleccioná un usuario específico para enviar la notificación.")
            cleaned_data['to_all_event_attendees'] = False
            cleaned_data['event'] = None  # No debe usarse el evento en este caso
        else:
            # Si no se eligió ninguna opción (no debería ocurrir si el campo es requerido)
            raise forms.ValidationError("Debés elegir un tipo de destino (evento o usuario).")
        return cleaned_data
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Nombre',
            'description': 'Descripción',
            'is_active': 'Activo',
        }

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['title', 'rating', 'text']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Gran experiencia'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Comparte tu experiencia...', 'rows': 3}),
        }
        labels = {
            'title': 'Título de tu reseña *',
            'rating': 'Tu calificación *',
            'text': 'Tu reseña (opcional)',
        }

# --- Formulario de Encuesta de Satisfacción ---
class SatisfactionSurveyForm(forms.ModelForm):
    class Meta:
        model = SatisfactionSurvey
        fields = ['rating', 'observations']
        widgets = {
            'rating': forms.RadioSelect(
                attrs={'class': 'star-rating'},
                choices=SatisfactionSurvey.RATING_CHOICES
            ),
            'observations': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Comparte tu experiencia con la compra de tickets (opcional)',
                    'maxlength': '500'
                }
            )
        }
        labels = {
            'rating': '¿Cómo calificarías tu experiencia usando nuestros servicios? *',
            'observations': 'Observaciones (opcional)'
        }

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        self.ticket = kwargs.pop('ticket', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Agregar clases Bootstrap y validación HTML5
        for field in self.fields.values():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.update({'class': 'form-control'})
            if field.required:
                field.widget.attrs.update({'required': 'required'})

    def clean(self):
        cleaned_data = super().clean()
        # Validar que el rating esté presente
        if not cleaned_data.get('rating'):
            self.add_error('rating', 'Por favor, selecciona una calificación')
        # Validar que no exista una encuesta previa para este ticket
        if self.ticket and self.user:
            if SatisfactionSurvey.objects.filter(ticket=self.ticket, user=self.user).exists():
                raise ValidationError('Ya has realizado una encuesta para este ticket')
            # Validar que el usuario no sea organizador
            if self.user.is_organizer:
                raise ValidationError('Los organizadores no pueden realizar encuestas de satisfacción')
            # Validar que el ticket pertenezca al usuario
            if self.ticket.user != self.user:
                raise ValidationError('Solo puedes realizar encuestas para tickets que hayas comprado')
            # Validar que el ticket pertenezca al evento
            if self.event and self.ticket.event != self.event:
                raise ValidationError('El ticket debe pertenecer al evento especificado')
        return cleaned_data
