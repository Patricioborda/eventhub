import datetime
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Count
from django.views import generic, View
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.template.loader import render_to_string
from .forms import RatingForm
from .models import Rating
from django.urls import reverse

from .models import Event, User, Ticket, Category, Notification, RefundRequest, Venue
from .forms import TicketForm, CategoryForm, NotificationForm, RefundRequestForm, VenueForm

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
        return redirect("events")

    return render(request, "accounts/login.html")


def home(request):
    # Usuario autenticado → redirigimos a su página principal (events)
    if request.user.is_authenticated:
        return redirect("events")          # o "home_organizer" / "home_user" más adelante

    # Visitante → página pública
    return render(request, "home_guest.html")

# ------------------- Eventos -------------------
@login_required
def events(request):
    events = Event.objects.all().order_by("scheduled_at")
    return render(
        request,
        "app/events.html",
        {"events": events, "user_is_organizer": request.user.is_organizer},
    )

@login_required
def event_detail(request, id):
    event = get_object_or_404(Event, pk=id)
    edit_mode = request.GET.get("edit_rating") == "1"

    try:
        rating = Rating.objects.get(event=event, user=request.user)
    except Rating.DoesNotExist:
        rating = None

    if request.method == "POST":
        if rating:
            # Verificamos que solo el usuario que creó la calificación o el organizador del evento pueda editarla
            if rating.user != request.user and not request.user.is_organizer:
                return redirect("event_detail", id=event.id)  # type: ignore # Bloquear edición ajena

            form = RatingForm(request.POST, instance=rating)
        else:
            form = RatingForm(request.POST)
        
        if form.is_valid():
            new_rating = form.save(commit=False)
            new_rating.user = request.user
            new_rating.event = event
            new_rating.save()
            return redirect("event_detail", id=event.id) # type: ignore
    else:
        if rating:
            form = RatingForm(instance=rating)
        else:
            form = RatingForm()

    # Calificaciones: mostrar la del usuario actual primero
    ratings = list(event.ratings.all()) # type: ignore
    if rating in ratings:
        ratings.remove(rating)
        ratings.insert(0, rating)

    return render(request, "app/event_detail.html", {
        "event": event,
        "form": form,
        "rating": rating,
        "edit_mode": edit_mode,
        "ratings": ratings,
        "user_is_organizer": request.user.is_organizer,  # ← Agregar esta línea
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
        venue_id = request.POST.get("venue")  # Obtener el ID de la ubicación seleccionada

        category_ids = request.POST.getlist("categories")

        # Convertir fecha y hora
        scheduled_at = timezone.make_aware(
            datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        )

        # Validar y obtener la ubicación
        venue = get_object_or_404(Venue, pk=venue_id) if venue_id else None
        selected_categories = Category.objects.filter(id__in=category_ids)

        if id is None:
            # Crear un nuevo evento
            success, errors = Event.new(title, description, venue, scheduled_at, user, selected_categories)

            if not success:
                venues = Venue.objects.all()
                return render(request, "app/event_form.html", {
                    "event": {},
                    "categories": categories,
                    "selected_categories": category_ids,
                    "venues": venues,
                    "venue_form": VenueForm(),
                    "errors": errors,
                    "user_is_organizer": user.is_organizer,
                })
        else:
            # Actualizar un evento existente
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
            refund.save()
            return redirect("my_refund_requests")
    else:
        form = RefundRequestForm(user=request.user)

    return render(request, "app/refund/create_refund_request.html", {"form": form})


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
def ticket_create(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.event = event
            ticket.user = request.user
            ticket.save()
            return redirect('ticket_list')
    else:
        form = TicketForm()

    return render(request, 'app/ticket/ticket_form.html', {
        'form': form,
        'event': event
    })


@login_required
def ticket_update(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            return redirect('ticket_list')
    else:
        form = TicketForm(instance=ticket)

    return render(request, 'app/ticket/ticket_form.html', {
        'form': form,
        'event': ticket.event
    })


@login_required
def ticket_delete(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        ticket.delete()
        return redirect('ticket_list')
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


class NotificationList(LoginRequiredMixin, generic.ListView):
    template_name = "notifications/list.html"
    paginate_by = 10

    def get_queryset(self):
        return self.request.user.notifications.all() # type: ignore

class NotificationCreate(OrganizerRequiredMixin, generic.CreateView):
    model = Notification
    form_class = NotificationForm
    template_name = "notifications/form.html"
    success_url = reverse_lazy("notifications_list")


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
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return redirect("notifications_list")


class NotificationDropdown(LoginRequiredMixin, View):
    def get(self, request):
        notifs = request.user.notifications.order_by("-created_at")[:5]
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
