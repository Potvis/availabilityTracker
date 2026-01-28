import logging
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone

from .schedule_models import BusinessEvent, BusinessEventBooking
from .forms import BusinessEventBookingForm
from equipment.assignment import get_size_category_from_shoe_size
from members.models import Member

logger = logging.getLogger(__name__)


def _build_ical(event, booking):
    """Build an iCalendar (.ics) string for the event booking."""
    start_dt = event.event_datetime
    end_dt = start_dt + timedelta(minutes=event.duration_minutes)

    # Format datetimes as iCal UTC strings (YYYYMMDDTHHMMSSZ)
    def fmt(dt):
        utc_dt = dt.astimezone(timezone.utc)
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

            # Compute size category
            size_category = get_size_category_from_shoe_size(
                form.cleaned_data['shoe_size']
            )

            # Check size-specific equipment availability
            if not size_category or not event.can_book_for_size(size_category):
                messages.error(
                    request,
                    'Er is geen apparatuur meer beschikbaar voor uw schoenmaat. '
                    'Neem contact op met de organisator.'
                )
                return render(request, 'events/event_booking.html', {
                    'event': event,
                    'form': form,
                })

            # Create the booking
            booking = form.save(commit=False)
            booking.event = event
            booking.size_category = size_category or ''

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
