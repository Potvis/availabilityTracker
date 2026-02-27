import logging
import datetime
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone

from .schedule_models import BusinessEvent, BusinessEventBooking, Company
from .forms import BusinessEventBookingForm
from equipment.assignment import get_category_from_shoe_size_and_weight
from members.models import Member

logger = logging.getLogger(__name__)


def _build_ical(event, booking):
    """Build an iCalendar (.ics) string for the event booking."""
    start_dt = event.event_datetime
    end_dt = start_dt + timedelta(minutes=event.duration_minutes)

    # Format datetimes as iCal UTC strings (YYYYMMDDTHHMMSSZ)
    def fmt(dt):
        utc_dt = dt.astimezone(datetime.timezone.utc)
        return utc_dt.strftime('%Y%m%dT%H%M%SZ')

    now_stamp = fmt(timezone.now())
    uid = f"event-{event.token}-booking-{booking.pk}@jump4fun.be"

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Jump4Fun//Business Event//NL',
        'CALSCALE:GREGORIAN',
        'METHOD:REQUEST',
        'BEGIN:VEVENT',
        f'UID:{uid}',
        f'DTSTAMP:{now_stamp}',
        f'DTSTART:{fmt(start_dt)}',
        f'DTEND:{fmt(end_dt)}',
        f'SUMMARY:{event.title}',
        f'LOCATION:{event.location}',
        f'DESCRIPTION:{event.description}' if event.description else f'DESCRIPTION:{event.title}',
        f'ORGANIZER;CN=Jump4Fun:mailto:{settings.DEFAULT_FROM_EMAIL}',
        f'ATTENDEE;CN={booking.full_name};RSVP=TRUE:mailto:{booking.email}',
        'STATUS:CONFIRMED',
        'END:VEVENT',
        'END:VCALENDAR',
    ]
    return '\r\n'.join(lines)


def _send_booking_confirmation_email(event, booking):
    """Send a confirmation email with iCal invite attachment."""
    subject = f'Bevestiging: {event.title}'
    body = (
        f'Beste {booking.first_name},\n\n'
        f'U bent ingeschreven voor het volgende evenement:\n\n'
        f'  Evenement: {event.title}\n'
        f'  Datum: {event.event_datetime.strftime("%A %d %B %Y")}\n'
        f'  Tijd: {event.event_datetime.strftime("%H:%M")} ({event.duration_minutes} min)\n'
        f'  Locatie: {event.location}\n\n'
        f'In bijlage vindt u een agenda-uitnodiging die u kunt toevoegen aan uw kalender.\n\n'
        f'Tot dan!\n'
        f'Jump4Fun'
    )

    ical_content = _build_ical(event, booking)

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[booking.email],
    )
    email.attach('evenement.ics', ical_content, 'text/calendar')

    try:
        email.send(fail_silently=False)
    except Exception as e:
        logger.warning(f'Failed to send booking confirmation email to {booking.email}: {e}')


def event_booking_page(request, token):
    """
    Public page for a business event, accessible via the unique token link.
    Shows event info and a booking form for guests.
    """
    event = get_object_or_404(BusinessEvent, token=token)

    # Check if event is bookable
    if not event.is_in_future:
        return render(request, 'events/event_closed.html', {
            'event': event,
            'reason': 'past',
        })

    if not event.is_active:
        return render(request, 'events/event_closed.html', {
            'event': event,
            'reason': 'inactive',
        })

    if not event.can_book():
        return render(request, 'events/event_closed.html', {
            'event': event,
            'reason': 'full',
        })

    if request.method == 'POST':
        form = BusinessEventBookingForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Check if this email already booked this event
            if BusinessEventBooking.objects.filter(event=event, email=email).exists():
                messages.error(
                    request,
                    'Dit e-mailadres is al ingeschreven voor dit evenement.'
                )
                return render(request, 'events/event_booking.html', {
                    'event': event,
                    'form': form,
                })

            # Find the matching equipment category
            category = get_category_from_shoe_size_and_weight(
                form.cleaned_data['shoe_size'],
                form.cleaned_data.get('weight'),
            )

            # Check category-specific equipment availability
            if not category or not event.can_book_for_category(category):
                return render(request, 'events/event_no_equipment.html', {
                    'event': event,
                    'guest_name': f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}",
                    'guest_email': form.cleaned_data['email'],
                    'shoe_size': form.cleaned_data['shoe_size'],
                    'weight': form.cleaned_data['weight'],
                })

            # Create the booking
            booking = form.save(commit=False)
            booking.event = event
            booking.equipment_category = category

            # Handle optional account creation
            create_account = form.cleaned_data.get('create_account')
            if create_account:
                password = form.cleaned_data['password1']
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                )
                # The signal will create a Member and UserProfile automatically.
                # Update member fields that the signal doesn't set.
                member = user.profile.member
                member.phone = form.cleaned_data.get('phone', '')
                member.shoe_size = form.cleaned_data['shoe_size']
                member.save()

                # Set weight on profile
                user.profile.weight = form.cleaned_data['weight']
                user.profile.save()
                user.profile.check_profile_complete()

                booking.member = member
                booking.save()

                # Log the user in
                login(request, user)

                # Send confirmation email with iCal
                _send_booking_confirmation_email(event, booking)

                return redirect('event_confirmation', token=token, booking_id=booking.pk)

            # Guest booking (no account)
            booking.save()
            # Store booking id in session so confirmation page can show it
            request.session['event_booking_id'] = booking.pk

            # Send confirmation email with iCal
            _send_booking_confirmation_email(event, booking)

            return redirect('event_confirmation', token=token, booking_id=booking.pk)
    else:
        form = BusinessEventBookingForm()

    return render(request, 'events/event_booking.html', {
        'event': event,
        'form': form,
    })


def event_confirmation(request, token, booking_id):
    """
    Confirmation page shown after a successful business event booking.
    """
    event = get_object_or_404(BusinessEvent, token=token)
    booking = get_object_or_404(BusinessEventBooking, pk=booking_id, event=event)

    # Verify the viewer is the one who booked (via session or logged-in member)
    session_booking_id = request.session.get('event_booking_id')
    is_owner = False
    if session_booking_id == booking.pk:
        is_owner = True
    if request.user.is_authenticated and booking.member:
        if hasattr(request.user, 'profile') and request.user.profile.member == booking.member:
            is_owner = True
    if request.user.is_staff:
        is_owner = True

    if not is_owner:
        messages.error(request, 'U heeft geen toegang tot deze pagina.')
        return redirect('event_booking', token=token)

    return render(request, 'events/event_confirmation.html', {
        'event': event,
        'booking': booking,
    })


def company_events_page(request, token):
    """
    Public page for a company, showing all available events.
    Users pick which event(s) to book from one company link.
    """
    company = get_object_or_404(Company, token=token)

    if not company.is_active:
        return render(request, 'events/event_closed.html', {
            'event': None,
            'company': company,
            'reason': 'inactive',
        })

    active_events = company.get_active_events()

    if not active_events.exists():
        return render(request, 'events/event_closed.html', {
            'event': None,
            'company': company,
            'reason': 'no_events',
        })

    # Check which events the user already booked (by email from session or form)
    user_email = request.session.get('company_booking_email', '')
    booked_event_ids = set()
    if user_email:
        booked_event_ids = set(
            BusinessEventBooking.objects.filter(
                event__company=company,
                email=user_email
            ).values_list('event_id', flat=True)
        )

    # If user selected a specific event, show the booking form
    selected_event_id = request.GET.get('event') or request.POST.get('event_id')
    selected_event = None
    form = None

    if selected_event_id:
        try:
            selected_event = active_events.get(pk=selected_event_id)
        except BusinessEvent.DoesNotExist:
            selected_event = None

    if selected_event and request.method == 'POST':
        form = BusinessEventBookingForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Check if already booked for this event
            if BusinessEventBooking.objects.filter(event=selected_event, email=email).exists():
                # Check if company allows multiple bookings for different events
                if not company.allow_multiple_bookings or selected_event.pk in booked_event_ids:
                    messages.error(
                        request,
                        'U bent al ingeschreven voor dit evenement.'
                    )
                    return render(request, 'events/company_events.html', {
                        'company': company,
                        'events': active_events,
                        'selected_event': selected_event,
                        'form': form,
                        'booked_event_ids': booked_event_ids,
                    })

            # If company doesn't allow multiple bookings, check across all events
            if not company.allow_multiple_bookings and booked_event_ids:
                messages.error(
                    request,
                    'U bent al ingeschreven voor een evenement van dit bedrijf. '
                    'Meerdere inschrijvingen zijn niet toegestaan.'
                )
                return render(request, 'events/company_events.html', {
                    'company': company,
                    'events': active_events,
                    'selected_event': selected_event,
                    'form': form,
                    'booked_event_ids': booked_event_ids,
                })

            category = get_category_from_shoe_size_and_weight(
                form.cleaned_data['shoe_size'],
                form.cleaned_data.get('weight'),
            )

            if not category or not selected_event.can_book_for_category(category):
                return render(request, 'events/event_no_equipment.html', {
                    'event': selected_event,
                    'company': company,
                    'guest_name': f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}",
                    'guest_email': form.cleaned_data['email'],
                    'shoe_size': form.cleaned_data['shoe_size'],
                    'weight': form.cleaned_data['weight'],
                })

            booking = form.save(commit=False)
            booking.event = selected_event
            booking.equipment_category = category

            create_account = form.cleaned_data.get('create_account')
            if create_account:
                password = form.cleaned_data['password1']
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                )
                member = user.profile.member
                member.phone = form.cleaned_data.get('phone', '')
                member.shoe_size = form.cleaned_data['shoe_size']
                member.save()

                user.profile.weight = form.cleaned_data['weight']
                user.profile.save()
                user.profile.check_profile_complete()

                booking.member = member
                booking.save()
                login(request, user)
            else:
                booking.save()
                request.session['event_booking_id'] = booking.pk

            # Remember email for multi-booking
            request.session['company_booking_email'] = email

            _send_booking_confirmation_email(selected_event, booking)

            return redirect('event_confirmation', token=selected_event.token, booking_id=booking.pk)

    elif selected_event:
        form = BusinessEventBookingForm()

    # Build event list with availability info
    events_with_info = []
    for event in active_events:
        available = event.get_available_spots()
        events_with_info.append({
            'event': event,
            'available_spots': available,
            'can_book': event.is_active and event.is_in_future and available > 0,
            'already_booked': event.pk in booked_event_ids,
        })

    return render(request, 'events/company_events.html', {
        'company': company,
        'events_with_info': events_with_info,
        'selected_event': selected_event,
        'form': form,
        'booked_event_ids': booked_event_ids,
        'allow_multiple': company.allow_multiple_bookings,
    })


def contact_no_equipment(request):
    """
    Handle 'contact Jump4Fun' button when no Kangoo Boots are available.
    Sends an email to admin with the guest's info so they can follow up.
    """
    if request.method != 'POST':
        return redirect('root')

    guest_name = request.POST.get('guest_name', '')
    guest_email = request.POST.get('guest_email', '')
    shoe_size = request.POST.get('shoe_size', '')
    weight = request.POST.get('weight', '')
    event_title = request.POST.get('event_title', '')

    subject = f'Kangoo Boots aanvraag: {guest_name}'
    body = (
        f'Er is een aanvraag binnengekomen van iemand waarvoor er momenteel '
        f'geen Kangoo Boots beschikbaar zijn.\n\n'
        f'Naam: {guest_name}\n'
        f'E-mail: {guest_email}\n'
        f'Schoenmaat: {shoe_size}\n'
        f'Gewicht: {weight} kg\n'
        f'Evenement: {event_title}\n\n'
        f'Neem contact op met deze persoon om een oplossing te zoeken.'
    )

    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.DEFAULT_FROM_EMAIL],  # Send to admin
        )
        email.send(fail_silently=False)
    except Exception as e:
        logger.warning(f'Failed to send equipment contact email: {e}')

    return render(request, 'events/contact_sent.html', {
        'guest_name': guest_name,
        'event_title': event_title,
    })
