import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Count
from django.views import generic, View
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View, generic
from django.db import transaction
from django.db.models import Q
from collections import defaultdict
from django.contrib import messages
from django.utils.timezone import now


from django.views.decorators.http import require_POST, require_GET

from datetime import datetime
from django.db import models


from .forms import (
    CategoryForm,
    CommentForm,
    NotificationForm,
    RatingForm,
    RefundRequestForm,
    TicketForm,
    VenueForm,
    SatisfactionSurveyForm,
    DiscountCodeForm,
    DiscountCodeEditForm,
)
from .models import (
    Category,
    Comment,
    Event,
    Favorite,
    Notification,
    Rating,
    RefundRequest,
    Ticket,
    User,
    Venue,
    SatisfactionSurvey,
    DiscountCode,
)
from .utils import format_datetime_es
from .models import Rating
from django.shortcuts import resolve_url
from django.conf import settings


# ------------------- Registro y login -------------------
def register(request):
    if request.method == "POST":
        email = request.POST.get("email")
        username = request.POST.get("username")
        is_organizer = request.POST.get("is-organizer") is not None
        password = request.POST.get("password")
        password_confirm = request.POST.get("password-confirm")

        errors = User.validate_new_user(email, username, password, password_confirm)

        if len(errors) > 0:
            return render(
                request,
                "accounts/register.html",
                {
                    "errors": errors,
                    "data": request.POST,
                },
            )
        else:
            user = User.objects.create_user(
                email=email, username=username, password=password, is_organizer=is_organizer
            )
            login(request, user)
            return redirect("events")

    return render(request, "accounts/register.html", {})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(
                request, "accounts/login.html", {"error": "Usuario o contraseña incorrectos"}
            )

        login(request, user)
        return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))  # 👈 Esto usa el valor de settings.py

    return render(request, "accounts/login.html")


def home(request):
    if request.user.is_authenticated:
        if request.user.is_organizer:
            return render(request, "home_organizer.html")
        return render(request, "home_user.html")
    return render(request, "home_guest.html")

@login_required
def home_user(request):
    return render(request, "home_user.html")

@login_required
def home_organizer(request):
    return render(request, "home_organizer.html")

# ------------------- Terminos y condiciones -------------------
def terms_and_conditions(request):
    return render(request, "accounts/terms_and_conditions.html")

def privacy_policy(request):
    return render(request, "accounts/privacy_policy.html")


# ------------------- Eventos -------------------
@login_required
def events(request):
    # Obtiene los eventos, base para ambos casos (usuario y organizador)
    all_events_ordered = Event.objects.all().order_by("scheduled_at")

    # Determina si el usuario es organizador
    if request.user.is_organizer:
        # Si es organizador, mostrar todos los eventos
        events_to_display = all_events_ordered
        no_future_events_message = None # No necesita el mensaje para organizadores
    else:
        # Si no es organizador, filtrar para mostrar solo eventos futuros
        events_to_display = []
        for event in all_events_ordered:
            # consume `has_passed` para cada evento
            if not event.has_passed:
                events_to_display.append(event)

        # Lógica para el mensaje de "no hay eventos próximos" para usuarios no organizadores
        no_future_events_message = None
        if not events_to_display: # Verifica si la lista de eventos futuros está vacía
            no_future_events_message = "Actualmente no hay eventos próximos visibles."

    # Obtener lista de favoritos del usuario (esto aplica para ambos roles)
    favoritos_ids = request.user.favorites.values_list("event_id", flat=True)

    return render(
        request,
        "app/events.html",
        {
            "events": events_to_display, # Pasa la lista de eventos que corresponda al usuario
            "user_is_organizer": request.user.is_organizer,
            "favoritos_ids": list(favoritos_ids),
            "no_future_events_message": no_future_events_message, # Pasa el mensaje condicionalmente
        },
    )


@login_required
def event_detail(request, id):
    event = get_object_or_404(Event, pk=id)

    countdown_seconds = event.countdown_seconds()

    user = request.user if request.user.is_authenticated else None
    
    # Calcular user_is_organizer correctamente incluso para guest
    user_is_organizer = user == event.organizer if user else False

    user_has_max_tickets = False
    if user and not user_is_organizer:
        disponibles = Ticket.entradas_disponibles_para_usuario(user, event)
        user_has_max_tickets = disponibles <= 0


    # ---------- Flags de edición ----------
    edit_id   = request.GET.get("edit_rating")       # p.e. "17" ó None
    edit_mode = bool(edit_id)

    # ---------- Rating del usuario ----------
    my_rating = Rating.objects.filter(
        event=event, user=request.user
    ).first()

    # ---------- POST: crear o actualizar ----------
    if request.method == "POST":
        # Si existe y estamos editando  ➜  instancia
        if my_rating and edit_mode:
            form = RatingForm(request.POST, instance=my_rating)
        else:  # crear nuevo
            form = RatingForm(request.POST)

        if form.is_valid():
            r = form.save(commit=False)
            r.user, r.event = request.user, event
            r.save()
            return redirect("event_detail", id=event.id) # type: ignore

    # ---------- GET: preparar formulario ----------
    else:
        if edit_mode and my_rating:
            form = RatingForm(instance=my_rating)
        else:
            form = RatingForm()

    # ---------- Lista de calificaciones ----------
    ratings = list(event.ratings.all().order_by("-created_at")) # type: ignore
    if my_rating in ratings:
        ratings.remove(my_rating)
        ratings.insert(0, my_rating)

    # ---------- Comentarios ----------
    comments = Comment.objects.filter(
        event=event, is_deleted=False
    ).order_by("-created_at")

   # ---------- Renderizar ----------
    return render(request, "app/event_detail.html", {
        "event":            event,
        "countdown_seconds": countdown_seconds,
        "ratings":          ratings,
        "edit_mode":        edit_mode,
        "edit_rating_id":   int(edit_id) if edit_id else 0,
        "rating":           my_rating,
        "form":             form,
        "comments":         comments,
        "user_is_organizer": user_is_organizer,
        "user_has_max_tickets": user_has_max_tickets,
    })

@login_required
def event_delete(request, id):
    user = request.user
    if not user.is_organizer:
        return redirect("events")

    if request.method == "POST":
        event = get_object_or_404(Event, pk=id)
        event.delete()
        return redirect("events")

    return redirect("events")




@login_required
def event_form(request, id=None):
    user = request.user

    if not user.is_organizer:
        return redirect("events")

    # Si se proporciona un ID, se intenta obtener el evento existente
    event = get_object_or_404(Event, pk=id) if id else None
    categories = Category.objects.filter(is_active=True)
    selected_categories = event.categories.values_list('id', flat=True) if event else []


    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        date = request.POST.get("date")
        time = request.POST.get("time")
        venue_id = request.POST.get("venue")

        category_ids = request.POST.getlist("categories")

        # Convertir fecha y hora
        [year, month, day] = date.split("-")
        [hour, minutes] = time.split(":")
        scheduled_at = timezone.make_aware(
            datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        )

        venue = get_object_or_404(Venue, pk=venue_id) if venue_id else None
        selected_categories = Category.objects.filter(id__in=category_ids)


        if id is None:
            success, errors = Event.new(title, description, venue, scheduled_at, user, selected_categories)

            if not success:
                venues = Venue.objects.all()
                return  render(request, "app/event_form.html", {
                        "event": {},
                        "categories": categories,
                        "selected_categories": category_ids,
                        "venues": venues,
                        "venue_form": VenueForm(),
                        "errors": errors,
                        "user_is_organizer": user.is_organizer,
                    },
                )
        else:
            event = get_object_or_404(Event, pk=id)
            event.update(title, description, venue, scheduled_at, user, selected_categories)


        return redirect("events")
    else:
        venues = Venue.objects.all()
        venue_form = VenueForm()
        return render(
            request,
            "app/event_form.html",
            {
                "event": event,  # Pasar el evento existente (si lo hay) al formulario
                "categories": categories,
                "selected_categories": selected_categories,
                "venues": venues,
                "venue_form": venue_form,
                "user_is_organizer": user.is_organizer,
            },
        )

# ------------------- Venue -------------------
@login_required
def venue_list(request):
    if not request.user.is_organizer:
        return redirect("events")  # Redirigir a la lista de eventos si no es organizador
    venues = Venue.objects.all()
    return render(request, "app/venue/venue.html", {"venues": venues})  # Actualizado

@login_required
def venue_form(request, id=None):
    if not request.user.is_organizer:
        return redirect("events")  # Redirigir a la lista de eventos si no es organizador

    if id:
        venue = get_object_or_404(Venue, pk=id)
    else:
        venue = None

    if request.method == "POST":
        form = VenueForm(request.POST, instance=venue)
        if form.is_valid():
            form.save()  # Guardar la nueva ubicación o actualizar la existente
            return redirect("venue_list")
    else:
        form = VenueForm(instance=venue)

    return render(request, "app/venue/venue_form.html", {"form": form, "venue": venue})  # Actualizado

@login_required
def venue_detail(request, id):
    if not request.user.is_organizer:
        return redirect("events")  # Redirigir a la lista de eventos si no es organizador
    venue = get_object_or_404(Venue, pk=id)
    return render(request, "app/venue/venue_detail.html", {"venue": venue})  # Actualizado

@login_required
def venue_delete(request, id):
    if not request.user.is_organizer:
        return redirect("events")

    venue = get_object_or_404(Venue, pk=id)
    print(f"Venue to delete: {venue.name}")  # Depuración

    if request.method == "POST":
        venue.delete()
        return redirect("venue_list")

    return render(request, "app/venue/venue_confirm_delete.html", {"venue": venue})

# ------------------- Refund -------------------
def my_refund_requests(request):
    refunds = RefundRequest.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "app/refund/my_refund_requests.html", {"refunds": refunds})


@login_required
def refund_request_form(request, id=None):
    if id:
        refund = get_object_or_404(RefundRequest, pk=id, user=request.user)
    else:
        refund = None

    if request.method == "POST":
        form = RefundRequestForm(request.POST, instance=refund)
        if form.is_valid():
            refund_request = form.save(commit=False)
            refund_request.user = request.user
            refund_request.save()
            return redirect("my_refund_requests")
    else:
        form = RefundRequestForm(instance=refund)

    return render(request, "app/refund/my_refund_requests.html", {"form": form, "refund": refund})


@login_required
def refund_request_delete(request, id):
    refund = get_object_or_404(RefundRequest, pk=id, user=request.user)
    if request.method == "POST":
        refund.delete()
    return redirect("my_refund_requests")


@login_required
def manage_refund_requests(request):
    if not request.user.is_organizer:
        return redirect("events")

    refunds = RefundRequest.objects.all().order_by("-created_at")
    return render(request, "app/refund/manage_refund_requests.html", {"refunds": refunds})


@login_required
def approve_refund_request(request, id):
    if not request.user.is_organizer:
        return redirect("events")

    refund = get_object_or_404(RefundRequest, pk=id)
    refund.approve()
    return redirect("manage_refund_requests")


@login_required
def reject_refund_request(request, id):
    user = request.user
    if not user.is_organizer:
        return redirect("events")

    refund_request = get_object_or_404(RefundRequest, pk=id)
    refund_request.reject()
    return redirect("manage_refund_requests")

@login_required
def new_refund_request(request):
    if request.method == "POST":
        form = RefundRequestForm(request.POST, user=request.user)
        if form.is_valid():
            refund = form.save(commit=False)
            refund.user = request.user
            # Asignar el porcentaje calculado
            refund.refund_percentage = form.cleaned_data['refund_percentage']
            refund.save()
            messages.success(request,
                f"Solicitud creada. Tu reembolso será del {int(refund.refund_percentage*100)}%.")
            return redirect("my_refund_requests")
    else:
        form = RefundRequestForm(user=request.user)

    return render(request, "app/refund/create_refund_request.html", {
        "form": form
    })


@login_required
def refund_detail(request, id):
    # Solo organizadores pueden ver cualquier detalle, los usuarios solo los suyos
    refund = get_object_or_404(RefundRequest, pk=id)
    if not request.user.is_organizer and refund.user != request.user:
        return redirect("events")  # o donde quieras  

    return render(
        request,
        "app/refund/refund_detail.html",
        {"refund": refund}
    )
# 🟢 Vista para listar todos los comentarios de un evento
def comment_list(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    comments = Comment.objects.filter(event=event)
    return render(request, 'comments/comment_list.html', {'event': event, 'comments': comments})

@login_required
def comment_create(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.event = event
            comment.save()
    return redirect('event_detail', id=event.pk)

@login_required
def comment_update(request, pk):
    comment = get_object_or_404(Comment, pk=pk)

    if comment.user != request.user:
        return redirect('event_detail', id=comment.event.pk)

    if request.method == "POST":
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('event_detail', id=comment.event.pk)
    else:
        form = CommentForm(instance=comment)  # renderiza el formulario con datos actuales

    return render(request, 'comments/comment_edit.html', {
    'form': form,
    'event': comment.event,
    'original_comment': comment
})



# Eliminar un comentario (lógico, solo POST)
@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    event = comment.event

    is_author = request.user == comment.user
    is_event_organizer = request.user == event.organizer

    if not (is_author or is_event_organizer):
        return redirect('event_detail', id=event.pk)

    if request.method == 'POST':
        comment.is_deleted = True
        comment.save()

        if is_event_organizer and not is_author:
            return redirect('organizer_comments')  # vista que vos definas
        else:
            return redirect('event_detail', id=event.pk)

    # Si alguien accede por GET, redirigir (no permitir)
    return redirect('event_detail', id=event.pk)
@login_required
def organizer_comments(request):
    # 1️⃣ Solo los organizadores pueden entrar
    if not request.user.is_organizer:
        return redirect("events")  # redirige al listado de eventos

    # 2️⃣ Traer todos los eventos creados por este organizador
    eventos = Event.objects.filter(organizer=request.user)

    # 3️⃣ Filtrar todos los comentarios de esos eventos
    comentarios = Comment.objects.filter(
        event__in=eventos
    ).select_related("event", "user").order_by("-created_at")

    # 4️⃣ Renderizar el template con la lista de comentarios
    return render(request, "comments/organizer_comments.html", {
        "comentarios": comentarios
    })

@login_required
def comment_hard_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)

    # Solo el organizador del evento puede eliminar completamente
    if request.user != comment.event.organizer:
        return redirect('events')

    if request.method == 'POST':
        comment.delete()  # Borrado total
        return redirect('organizer_comments')

    return redirect('organizer_comments')



@login_required
def edit_refund_request(request, id):
    refund = get_object_or_404(RefundRequest, pk=id, user=request.user)
    # Solo se edita si está pendiente
    if refund.approved is not None:
        return redirect("my_refund_requests")

    if request.method == "POST":
        form = RefundRequestForm(request.POST, instance=refund, user=request.user)
        if form.is_valid():
            form.save()
            return redirect("my_refund_requests")
    else:
        form = RefundRequestForm(instance=refund, user=request.user)

    return render(request, "app/refund/edit_refund_request.html", {
        "form": form,
        "refund": refund
    })




# ------------------- Tickets -------------------
@login_required
def ticket_list(request):
    tickets = Ticket.objects.filter(user=request.user)
    return render(request, 'app/ticket/ticket_list.html', {'tickets': tickets})

@login_required
def ticket_list_organizer(request):
    events = Event.objects.filter(organizer=request.user)
    tickets = Ticket.objects.filter(event__in=events).select_related('event', 'user')

    # Agrupar tickets por evento
    grouped = defaultdict(list)
    for ticket in tickets:
        grouped[ticket.event].append(ticket)

    # Convertir a lista de tuplas para usar en el template
    grouped_tickets = list(grouped.items())

    # Agregar la variable `is_organizer` al contexto
    is_organizer = request.path.startswith('/organizer')

    return render(request, 'app/ticket/ticket_list_organizer.html', {
        'grouped_tickets': grouped_tickets,
        'is_organizer': is_organizer,  # Pasa la variable `is_organizer`
    })
@require_GET
def validar_cupon(request):
    codigo = request.GET.get('codigo', '').strip()
    event_id = request.GET.get('event_id')
    
    if not codigo:
        return JsonResponse({'status': 'no_code', 'message': 'No se introdujo un cupón'})

    # Validar evento si se pasó un ID
    event = None
    if event_id:
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Evento no encontrado'})
    
    try:
        cupon = DiscountCode.objects.get(code__iexact=codigo)

        if not cupon.is_valid():
            return JsonResponse({
                'status': 'invalid',
                'message': 'El cupón ha expirado o ya no tiene usos disponibles'
            })

        if event and not cupon.applies_to_event(event):
            return JsonResponse({
                'status': 'invalid_event',
                'message': 'El cupón no existe.'
            })

        return JsonResponse({
            'status': 'ok',
            'message': 'Se aplicó un descuento',
            'discount_value': float(cupon.discount_value),
            'discount_type': cupon.discount_type,
            'descripcion': cupon.description or '',
        })

    except DiscountCode.DoesNotExist:
        return JsonResponse({'status': 'not_found', 'message': 'No se encontró el cupón'})


@login_required
def ticket_create(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    # Calculamos siempre cuántas entradas le quedan al usuario
    disponibles = Ticket.entradas_disponibles_para_usuario(request.user, event)
    existentes = 4 - disponibles

    if request.method == 'POST':
        form = TicketForm(request.POST)

        # *** Aquí fijamos max y data-max dinamicamente ***
        form.fields['quantity'].widget.attrs.update({
            'max': str(disponibles),
            'data-max': str(disponibles),
        })

        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.event = event
            ticket.user = request.user

            # Verificar cantidad permitida
            if ticket.quantity > disponibles:
                messages.error(
                    request,
                    f"No puedes comprar más de 4 entradas por evento. Ya compraste {existentes}."
                )
                return render(request, 'app/ticket/ticket_form.html', {
                    'form': form,
                    'event': event,
                    'entradas_existentes': existentes,
                    'entradas_disponibles': disponibles,
                })

            if 'apply_discount' in request.POST:  # Asumiendo que el botón para aplicar código se llama así
                code_str = form.cleaned_data.get('discount_code', '').strip()
                if code_str:
                    try:
                        discount = DiscountCode.objects.get(
                            code__iexact=code_str,
                            valid_from__lte=timezone.now().date(),
                            valid_until__gte=timezone.now().date(),
                        )
                        if discount.event is None or discount.event == event:
                            ticket.discount_code = discount
                        else:
                            ticket.discount_code = None
                            messages.warning(request, "Código de descuento inválido o no encontrado.")  # Mensaje genérico
                    except DiscountCode.DoesNotExist:
                        ticket.discount_code = None
                        messages.warning(request, "Código de descuento inválido o no encontrado.")
                else:
                    ticket.discount_code = None
            else:
                # No se intentó aplicar código, no mostrar mensajes
                ticket.discount_code = None

            ticket.save()
            if ticket.discount_code:
                # Incrementa en 1 cada vez que se use el cupón
                DiscountCode.objects.filter(
                    pk=ticket.discount_code.pk
                ).update(uses=F('uses') + 1)
            print(f"Descuento aplicado: {ticket.discount_code}")
            # Guardar el ticket_id en la sesión
            request.session['last_ticket_id'] = ticket.id
            return redirect('survey_create', ticket_id=ticket.id)
    else:
        form = TicketForm()
        # *** También fijamos max/data-max en GET para que el botón + esté limitado ***
        form.fields['quantity'].widget.attrs.update({
            'max': str(disponibles),
            'data-max': str(disponibles),
        })

    return render(request, 'app/ticket/ticket_form.html', {
        'form': form,
        'event': event,
        'entradas_existentes': existentes,
        'entradas_disponibles': disponibles,
    })



@login_required
def ticket_update(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    event = ticket.event

    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            entradas_actuales = Ticket.objects.filter(
                user=request.user,
                event=event
            ).exclude(pk=ticket.pk).aggregate(total=models.Sum('quantity'))['total'] or 0

            nuevas = form.cleaned_data['quantity']
            total = entradas_actuales + nuevas

            if total > 4:
                disponibles = 4 - entradas_actuales
                messages.error(
                    request,
                    f"No puedes tener más de 4 entradas por evento. Ya compraste {entradas_actuales}, puedes modificar hasta {disponibles} entradas."
                )
                return render(request, 'app/ticket/ticket_form.html', {
                    'form': form,
                    'event': event,
                    'entradas_existentes': entradas_actuales,
                    'entradas_disponibles': disponibles,
                })

            form.save()
            return redirect('ticket_list')
    else:
        form = TicketForm(instance=ticket)

        entradas_actuales = Ticket.objects.filter(
            user=request.user,
            event=ticket.event
        ).exclude(pk=ticket.pk).aggregate(total=models.Sum('quantity'))['total'] or 0

        disponibles = 4 - entradas_actuales
        form.fields['quantity'].widget.attrs['data-max'] = disponibles

    return render(request, 'app/ticket/ticket_form.html', {
        'form': form,
        'event': ticket.event,
        'entradas_existentes': entradas_actuales,
        'entradas_disponibles': disponibles,
    })


@login_required
def ticket_delete(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    # Verifica si el usuario es organizador o un usuario normal
    if request.method == 'POST':
        ticket.delete()

        # Redirige según el contexto
        if '/organizer/ticket' in request.path:
            return redirect('ticket_list_organizer')  # Lista de tickets del organizador
        return redirect('ticket_list')  # Lista de tickets del usuario normal

    return render(request, 'app/ticket/ticket_confirm_delete.html', {'ticket': ticket})
# ------------------- Categorías -------------------
@login_required
def categories(request):
    if request.user.is_organizer:
        # Si el usuario es organizador, mostramos todas las categorías
        categories = Category.objects.annotate(event_count=Count('events')).order_by("name")
    else:
        # Si el usuario es común, mostramos solo las categorías activas
        categories = Category.objects.filter(is_active=True).annotate(event_count=Count('events')).order_by("name")

    return render(
        request,
        "category/categories.html",
        {
            "categories": categories,
            "user_is_organizer": request.user.is_organizer,
        })

@login_required
def category_detail(request, id):
    category = get_object_or_404(Category, pk=id)
    return render(request, "category/category_detail.html", {
        "category": category,
        "user_is_organizer": request.user.is_organizer,
    })


@login_required
def category_delete(request, id):
    user = request.user
    if not user.is_organizer:
        return redirect("categories")

    if request.method == "POST":
        category = get_object_or_404(Category, pk=id)
        category.delete()
        return redirect("categories")

    return redirect("categories")


@login_required
def category_form(request, id=None):
    user = request.user
    if not user.is_organizer:
        return redirect("categories")

    category = get_object_or_404(Category, pk=id) if id else None

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect("categories")
    else:
        form = CategoryForm(instance=category)

    return render(request, "category/category_form.html", {
        "form": form,
        "category": category,
        "user_is_organizer": request.user.is_organizer,
    })


# ------------------- Notificaciones -------------------
class OrganizerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_organizer # type: ignore


@login_required
def notifications_list(request):
    query = request.GET.get("q", "")
    filter_event = request.GET.get("event")
    filter_priority = request.GET.get("priority")
    order_by = request.GET.get("order_by", "-created_at")  # Orden por defecto descendente fecha de envío

    # Campos permitidos para ordenar
    allowed_orders = ['title', '-title', 'event__title', '-event__title', 'created_at', '-created_at']
    if order_by not in allowed_orders:
        order_by = "-created_at"

    tickets_user_events = Event.objects.filter(tickets__user=request.user).distinct()

    received_notifications = Notification.objects.filter(
        Q(user=request.user) |
        Q(to_all_event_attendees=True, event__in=tickets_user_events)
    ).distinct()

    if query:
        received_notifications = received_notifications.filter(title__icontains=query)
    if filter_event:
        received_notifications = received_notifications.filter(event__id=filter_event)
    if filter_priority:
        received_notifications = received_notifications.filter(priority=filter_priority)

    # Aplicar ordenamiento
    received_notifications = received_notifications.order_by(order_by)

    # Agregar fecha formateada
    for notif in received_notifications:
        notif.formatted_date = format_datetime_es(notif.created_at)  # type: ignore

    sent_notifications = None
    if hasattr(request.user, 'is_organizer') and request.user.is_organizer:
        sent_notifications = Notification.objects.filter(created_by=request.user)

        if query:
            sent_notifications = sent_notifications.filter(title__icontains=query)
        if filter_event:
            sent_notifications = sent_notifications.filter(event__id=filter_event)
        if filter_priority:
            sent_notifications = sent_notifications.filter(priority=filter_priority)

        # Aplicar mismo ordenamiento
        sent_notifications = sent_notifications.order_by(order_by)

        for notif in sent_notifications:
            notif.formatted_date = format_datetime_es(notif.created_at)  # type: ignore

    all_events = tickets_user_events

    return render(request, "notifications/notifications_list.html", {
        "received_notifications": received_notifications,
        "sent_notifications": sent_notifications,
        "all_events": all_events,
        "filter_event": filter_event,
        "filter_priority": filter_priority,
        "query": query,
        "order_by": order_by,
    })

@login_required
def create_notification(request):
    if not request.user.is_organizer:
        return redirect('home')

    if request.method == 'POST':
        form = NotificationForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    target = form.cleaned_data['target']
                    title = form.cleaned_data['title']
                    message = form.cleaned_data['message']
                    priority = form.cleaned_data['priority']
                    to_all = form.cleaned_data['to_all_event_attendees']
                    event = form.cleaned_data.get('event')
                    user = form.cleaned_data.get('user')

                    if target == 'event' and event:
                        Notification.objects.create(
                            event=event,
                            to_all_event_attendees=True,
                            title=title,
                            message=message,
                            priority=priority,
                            created_by=request.user
                        )
                    elif target == 'user' and user:
                        Notification.objects.create(
                            user=user,
                            to_all_event_attendees=False,
                            title=title,
                            message=message,
                            priority=priority,
                            created_by=request.user
                        )
                    else:
                        raise Exception("Destino no válido en el formulario.")
            except Exception as e:
                form.add_error(None, f"Ocurrió un error al crear notificaciones: {e}")
            else:
                return redirect('notifications_list')
    else:
        form = NotificationForm(user=request.user)

    return render(request, 'notifications/create_notification.html', {'form': form})

@login_required
def notification_detail(request, pk):
    notification = get_object_or_404(Notification, pk=pk)

    # El usuario tiene acceso si:
    # - es el destinatario directo
    # - o es el creador (organizador)
    # - o es destinatario masivo y tiene ticket para ese evento
    user = request.user
    tiene_ticket = notification.event and notification.event.tickets.filter(user=user).exists()

    if not (
        notification.user == user or
        notification.created_by == user or
        (notification.to_all_event_attendees and tiene_ticket)
    ):
        return redirect("notifications_list")

    # Formatear fecha en español
    notification.formatted_date = format_datetime_es(notification.created_at) # type: ignore

    return render(request, "notifications/notifications_detail.html", {
        "notification": notification
    })

class NotificationUpdate(OrganizerRequiredMixin, generic.UpdateView):
    model = Notification
    form_class = NotificationForm
    template_name = "notifications/form.html"
    success_url = reverse_lazy("notifications_list")


class NotificationDelete(OrganizerRequiredMixin, generic.DeleteView):
    model = Notification
    template_name = "notifications/confirm_delete.html"
    success_url = reverse_lazy("notifications_list")


class NotificationMarkRead(LoginRequiredMixin, View):
    def post(self, request, pk):
        # Obtener eventos del usuario
        user_events = Event.objects.filter(tickets__user=request.user)

        notif = get_object_or_404(
            Notification,
            Q(user=request.user) | Q(to_all_event_attendees=True, event__in=user_events),
            pk=pk
        )
        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return redirect("notifications_list")


class NotificationDropdown(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        events = Event.objects.filter(tickets__user=user).distinct()

        notifs = Notification.objects.filter(
            Q(user=user) |
            Q(to_all_event_attendees=True, event__in=events)
        ).order_by("-created_at").distinct()[:5]

        html = render_to_string(
            "notifications/_dropdown_items.html",
            {"notifs": notifs},
            request=request,
        )
        return JsonResponse({"html": html})
      
################### feature/rating ################### 
@login_required
def rating_delete(request, rating_id):
    rating = get_object_or_404(Rating, pk=rating_id)
    user = request.user
    event = rating.event

    # Solo el autor o el organizador del evento puede eliminar
    if user == rating.user or (user.is_organizer and event.organizer == user):
        event_id = event.id # type: ignore
        rating.delete()
        return redirect(reverse("event_detail", kwargs={"id": event_id}))

    return redirect("events")


@login_required
def favorites_list(request):
    favoritos = Event.objects.filter(favorited_by__user=request.user).order_by("scheduled_at")
    return render(request, "favorites/list.html", {"events": favoritos})

@require_POST
@login_required
def toggle_favorite(request, event_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    event = get_object_or_404(Event, id=event_id)

    if not event:
        return JsonResponse({"error": "Evento no encontrado"}, status=404)

    favorite, created = Favorite.objects.get_or_create(user=request.user, event=event)

    if not created:
        favorite.delete()
        return JsonResponse({"favorito": False})
    else:
        return JsonResponse({"favorito": True})

################### feature/satisfaction-survey ################### 
@login_required
def survey_create(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    # Permitir acceso solo si el ticket_id está en la sesión
    last_ticket_id = request.session.get('last_ticket_id')
    if last_ticket_id != ticket.id:
        messages.error(request, 'No tienes permiso para acceder a esta encuesta.')
        return redirect('ticket_list')

    # Verificar que el usuario sea el dueño del ticket
    if ticket.user != request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'No tienes permiso para realizar esta acción'
            }, status=403)
        messages.error(request, 'No tienes permiso para realizar esta acción')
        return redirect('events')
    
    # Verificar que no exista una encuesta previa
    if SatisfactionSurvey.objects.filter(ticket=ticket, user=request.user).exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Ya has realizado una encuesta para este ticket'
            }, status=400)
        messages.info(request, 'Ya has realizado una encuesta para este ticket')
        return redirect('event_detail', id=ticket.event.id)

    if request.method == 'POST':
        form = SatisfactionSurveyForm(
            request.POST,
            event=ticket.event,
            ticket=ticket,
            user=request.user
        )
        if form.is_valid():
            survey = form.save(commit=False)
            survey.event = ticket.event
            survey.ticket = ticket
            survey.user = request.user
            survey.save()
            # Eliminar el ticket_id de la sesión tras POST exitoso
            if 'last_ticket_id' in request.session:
                del request.session['last_ticket_id']
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': '¡Gracias por tu opinión! Valoramos mucho tus palabras y nos ayudan a mejorar cada día.',
                    'redirect_url': reverse('ticket_list')
                })
            messages.success(request, '¡Gracias por tu opinión! Valoramos mucho tus palabras y nos ayudan a mejorar cada día.')
            return redirect('ticket_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
    else:
        form = SatisfactionSurveyForm(
            event=ticket.event,
            ticket=ticket,
            user=request.user
        )
        # (No eliminar el ticket_id de la sesión en el GET)

    return render(request, 'app/survey/survey_form.html', {
        'form': form,
        'ticket': ticket,
        'event': ticket.event
    })

@login_required
def survey_list(request):
    """
    Vista para listar todas las encuestas de satisfacción.
    Solo accesible para administradores.
    """
    if not request.user.is_staff:
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('home')

    # Obtener todas las encuestas con información relacionada
    surveys = SatisfactionSurvey.objects.select_related(
        'event', 'user', 'ticket'
    ).order_by('-created_at')

    # Calcular estadísticas
    total_surveys = surveys.count()
    avg_rating = surveys.aggregate(
        avg=models.Avg('rating')
    )['avg'] or 0

    # Distribución de calificaciones
    rating_distribution = surveys.values('rating').annotate(
        count=models.Count('id')
    ).order_by('rating')

    # Calcular porcentaje para cada rating
    distribution = []
    for dist in rating_distribution:
        percent = (dist['count'] / total_surveys * 100) if total_surveys else 0
        distribution.append({
            'rating': dist['rating'],
            'count': dist['count'],
            'percent': percent,
        })

    return render(request, 'app/survey/admin_list.html', {
        'surveys': surveys,
        'total_surveys': total_surveys,
        'avg_rating': round(avg_rating, 1),
        'rating_distribution': distribution,
    })

@login_required
def survey_detail(request, survey_id):
    """
    Vista para ver los detalles de una encuesta específica.
    Solo accesible para administradores o el usuario que la creó.
    """
    survey = get_object_or_404(SatisfactionSurvey, pk=survey_id)
    
    if not (request.user.is_staff or survey.user == request.user):
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('events')
    
    return render(request, 'app/survey_detail.html', {
        'survey': survey
    })



@login_required
def discount_list(request):
    if not request.user.is_organizer:
        return redirect('home')

    codes = DiscountCode.objects.filter(created_by=request.user)
    return render(request, 'discount/discount_list.html', {'codes': codes})

# views.py
@login_required
def discount_create(request):
    if not request.user.is_organizer:
        return redirect('home')

    if request.method == 'POST':
        form = DiscountCodeForm(request.POST, user=request.user)
        if form.is_valid():
            discount = form.save(commit=False)
            discount.created_by = request.user
            discount.save()
            return redirect('discount_list')
    else:
        form = DiscountCodeForm(user=request.user)

    return render(request, 'discount/discount_form.html', {'form': form})

def discount_edit(request, pk):
    code = get_object_or_404(DiscountCode, pk=pk)

    if request.method == 'POST':
        form = DiscountCodeEditForm(request.POST, instance=code)
        if form.is_valid():
            form.save()
            return redirect('discount_list')  # Cambia al nombre correcto de la url de la lista
    else:
        form = DiscountCodeEditForm(instance=code)

    return render(request, 'discount/discount_edit.html', {'form': form, 'code': code})

@login_required
def discount_delete(request, pk):
    code = get_object_or_404(DiscountCode, pk=pk)

    if not request.user.is_organizer or code.created_by != request.user:
        return redirect('home')

    if request.method == 'POST':
        code.delete()
        messages.success(request, "Código de descuento eliminado correctamente.")
        return redirect('discount_list')

    return render(request, "discount/discount_delete.html", context)


@login_required
def discount_detail(request, pk):
    code = get_object_or_404(DiscountCode, pk=pk)

    if not request.user.is_organizer or code.created_by != request.user:
        return redirect('home')

    context = {
        'code': code,
    }
    return render(request, "discount/discount_detail.html", context)
