from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from .schedule_models import BusinessEvent, BusinessEventBooking
from .forms import BusinessEventBookingForm
from equipment.assignment import get_size_category_from_shoe_size
from members.models import Member


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

            # Re-check capacity (race condition guard)
            if not event.can_book():
                messages.error(request, 'Dit evenement is helaas vol.')
                return render(request, 'events/event_closed.html', {
                    'event': event,
                    'reason': 'full',
                })

            # Compute size category
            size_category = get_size_category_from_shoe_size(
                form.cleaned_data['shoe_size']
            )

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

                return redirect('event_confirmation', token=token, booking_id=booking.pk)

            # Guest booking (no account)
            booking.save()
            # Store booking id in session so confirmation page can show it
            request.session['event_booking_id'] = booking.pk

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
