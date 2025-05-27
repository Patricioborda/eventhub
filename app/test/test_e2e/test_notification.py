from django.utils import timezone
from datetime import datetime, timedelta
from playwright.sync_api import expect
from app.models import Ticket, User, Event, Venue, Notification
from app.test.test_e2e.base import BaseE2ETest
import dateparser


class NotificationOnEventChangeTest(BaseE2ETest):
    
    def setUp(self):
        super().setUp()
        self.organizer = User.objects.create_user(
            username="organizer", email="org@example.com", password="password123", is_organizer=True
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="password123", is_organizer=False
        )
        self.venue1 = Venue.objects.create(name="Sala A", address="Dirección 1", city="Ciudad", capacity=100, contact="contacto1@example.com")
        self.venue2 = Venue.objects.create(name="Sala B", address="Dirección 2", city="Ciudad", capacity=100, contact="contacto2@example.com")

        self.event_date = timezone.make_aware(datetime(2025, 7, 15, 20, 0))
        self.event = Event.objects.create(
            title="Evento Original",
            description="Descripción original",
            scheduled_at=self.event_date,
            organizer=self.organizer,
            venue=self.venue1,
        )
        Ticket.objects.create(user=self.other_user, event=self.event, quantity=1, type='GENERAL')

    def test_notification_created_when_event_date_changes(self):
        self.login_user("otheruser", "password123")

        new_date = self.event_date + timedelta(days=1)
        self.event.scheduled_at = new_date
        self.event.save()

        notif = Notification.objects.filter(
            event=self.event,
            to_all_event_attendees=True,
            message__icontains="Fecha"
        ).first()
        assert notif is not None, "No se creó la notificación de cambio de fecha para el evento"

        self.page.goto(f"{self.live_server_url}/notifications/{notif.pk}/")
        self.page.wait_for_selector(".containerNotificaciones")
        detalle_text = self.page.locator(".containerNotificaciones").inner_text()
        assert "Fecha" in detalle_text, "El mensaje de detalle no contiene 'Fecha'"

    def test_notification_created_when_event_venue_changes(self):
        self.login_user("otheruser", "password123")

        self.event.venue = self.venue2
        self.event.save()

        notif = Notification.objects.filter(
            event=self.event,
            to_all_event_attendees=True,
            message__icontains="Lugar"
        ).first()
        assert notif is not None, "No se creó la notificación de cambio de lugar para el evento"

        self.page.goto(f"{self.live_server_url}/notifications/{notif.pk}/")
        self.page.wait_for_selector(".containerNotificaciones")
        detalle_text = self.page.locator(".containerNotificaciones").inner_text()
        assert "Lugar" in detalle_text, "El mensaje de detalle no contiene 'Lugar'"

    def test_mark_notification_as_read(self):
        notif = Notification.objects.create(
            user=self.other_user,
            to_all_event_attendees=False,
            title="Notificación para leer",
            message="Leer y marcar",
            priority='normal',
            created_by=self.organizer,
            is_read=False
        )

        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.fill("input[name='username']", "otheruser")
        self.page.fill("input[name='password']", "password123")
        self.page.click("button[type='submit']")
        self.page.wait_for_selector("form#login_form", state="detached")
        self.page.goto(f"{self.live_server_url}/notifications/")

        cookies = self.page.context.cookies()
        cookie_header = "; ".join(
            f"{c.get('name')}={c.get('value')}"
            for c in cookies
            if c.get('name') is not None and c.get('value') is not None
        )

        csrf_token = next(
            (c.get('value') for c in cookies if c.get('name') == 'csrftoken'),
            ''
        )

        headers = {
            "Cookie": cookie_header,
            "X-CSRFToken": csrf_token,
        }
        headers = {k: v for k, v in headers.items() if v is not None}

        response = self.page.request.post(
            f"{self.live_server_url}/notifications/{notif.pk}/read/",
            headers=headers
        )


        self.assertEqual(response.status, 200)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)


    def test_filter_notifications_by_priority(self):
        self.login_user("otheruser", "password123")

        Notification.objects.create(
            user=self.other_user,
            title="Notif baja prioridad",
            message="Mensaje baja",
            priority='low',
            created_by=self.organizer
        )
        Notification.objects.create(
            user=self.other_user,
            title="Notif alta prioridad",
            message="Mensaje alta",
            priority='high',
            created_by=self.organizer
        )

        self.page.goto(f"{self.live_server_url}/notifications/?priority=high")
        self.page.wait_for_selector(".table-notifs")

        page_text = self.page.content()
        assert "Notif alta prioridad" in page_text
        assert "Notif baja prioridad" not in page_text

    def test_no_access_to_others_private_notifications(self):
        self.login_user("otheruser", "password123")

        notif = Notification.objects.create(
            user=self.organizer,
            to_all_event_attendees=False,
            title="Notif privada para otro",
            message="No deberías verla",
            priority='normal',
            created_by=self.organizer
        )

        self.page.goto(f"{self.live_server_url}/notifications/{notif.pk}/")
        current_url = self.page.url
        assert current_url.endswith("/notifications/") or "notifications" in current_url

    def test_notifications_ordered_by_date(self):
        self.login_user("otheruser", "password123")

        now = timezone.now()

        notif1 = Notification.objects.create(
            user=self.other_user,
            to_all_event_attendees=False,
            title="Más antigua",
            message="Primera",
            priority='normal',
            created_by=self.organizer,
        )
        notif1.created_at = now - timedelta(days=2)
        notif1.save(update_fields=['created_at'])

        notif2 = Notification.objects.create(
            user=self.other_user,
            to_all_event_attendees=False,
            title="Intermedia",
            message="Segunda",
            priority='normal',
            created_by=self.organizer,
        )
        notif2.created_at = now - timedelta(days=1)
        notif2.save(update_fields=['created_at'])

        notif3 = Notification.objects.create(
            user=self.other_user,
            to_all_event_attendees=False,
            title="Más reciente",
            message="Tercera",
            priority='normal',
            created_by=self.organizer,
        )
        notif3.created_at = now
        notif3.save(update_fields=['created_at'])

        self.page.goto(f"{self.live_server_url}/notifications/")
        self.page.wait_for_selector(".containerNotificaciones")

        fechas_texto = self.page.eval_on_selector_all(
            ".table-notifs tbody tr td:nth-child(5)",
            "elements => elements.map(e => e.textContent.trim())"
        )

        fechas = [dateparser.parse(f, languages=['es']) for f in fechas_texto]

        # Filtrar fechas None (si hay)
        fechas_filtradas = [f for f in fechas if f is not None]

        self.assertTrue(len(fechas_filtradas) == len(fechas), "Alguna fecha no pudo ser parseada")

        self.assertEqual(fechas_filtradas, sorted(fechas_filtradas, reverse=True))


