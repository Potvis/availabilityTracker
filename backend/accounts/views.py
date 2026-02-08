from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from .forms import UserRegistrationForm, UserLoginForm, ProfileCompletionForm, QuickProfileUpdateForm
from .models import UserProfile
from equipment.assignment import get_equipment_requirements_display
from django.utils import timezone
from datetime import timedelta, date
import calendar
from bookings.schedule_models import SessionSchedule, BusinessEventBooking, SessionBooking
from bookings.models import SessionAttendance
from cards.models import CardType

def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('accounts:client_dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account succesvol aangemaakt! Vul nu uw profiel aan.')
            return redirect('accounts:profile_complete')
    else:
        form = UserRegistrationForm()
    
    context = {
        'form': form,
        'title': 'Registreren'
    }
    
    return render(request, 'accounts/register.html', context)


def user_login(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('accounts:client_dashboard')
    
    if request.method == 'POST':
        # Get email and password
        email = request.POST.get('username')  # Form field is named 'username' but contains email
        password = request.POST.get('password')
        
        # Try to find user by email
        try:
            user = User.objects.get(email=email)
            username = user.username
        except User.DoesNotExist:
            username = email
        
        # Authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Check if profile is complete
            if hasattr(user, 'profile') and not user.profile.profile_complete:
                messages.info(request, 'Vul eerst uw profiel aan om te kunnen boeken.')
                return redirect('accounts:profile_complete')
            
            # Redirect to next or dashboard
            next_url = request.GET.get('next', 'accounts:client_dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Ongeldige inloggegevens.')
    
    form = UserLoginForm()
    
    context = {
        'form': form,
        'title': 'Inloggen'
    }
    
    return render(request, 'accounts/login.html', context)


@login_required
def user_logout(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'U bent uitgelogd.')
    return redirect('accounts:login')


@login_required
def profile_complete(request):
    """
    Profile completion view - required before booking.
    This is shown to users on first login if profile is incomplete.
    """
    profile = request.user.profile
    
    # Check if already complete
    if profile.profile_complete:
        messages.info(request, 'Uw profiel is al compleet.')
        return redirect('accounts:client_dashboard')
    
    if request.method == 'POST':
        form = ProfileCompletionForm(
            request.POST, 
            instance=profile,
            member=profile.member
        )
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Profiel succesvol aangevuld! U kunt nu sessies boeken.'
            )
            return redirect('accounts:client_dashboard')
        else:
            messages.error(request, 'Corrigeer de fouten hieronder.')
    else:
        form = ProfileCompletionForm(
            instance=profile,
            member=profile.member
        )
    
    context = {
        'form': form,
        'profile': profile,
        'missing_fields': profile.missing_fields,
        'title': 'Profiel Aanvullen'
    }
    
    return render(request, 'accounts/profile_complete.html', context)


@login_required
def profile_view(request):
    """View and edit user profile"""
    profile = request.user.profile
    member = profile.member

    if request.method == 'POST':
        form = ProfileCompletionForm(
            request.POST,
            instance=profile,
            member=member
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Profiel bijgewerkt.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Corrigeer de fouten hieronder.')

        # For POST with errors, use submitted values so user sees what they typed
        field_values = {
            'first_name': request.POST.get('first_name', ''),
            'last_name': request.POST.get('last_name', ''),
            'phone': request.POST.get('phone', ''),
            'date_of_birth': request.POST.get('date_of_birth', ''),
            'shoe_size': request.POST.get('shoe_size', ''),
            'weight': request.POST.get('weight', ''),
        }
    else:
        # Try to pre-populate weight from last known source if not set
        initial_data = {}
        weight_value = profile.weight
        if weight_value is None:
            last_event_booking = BusinessEventBooking.objects.filter(
                member=member, weight__isnull=False
            ).order_by('-booked_at').first()
            if last_event_booking:
                weight_value = last_event_booking.weight
                initial_data['weight'] = weight_value

        form = ProfileCompletionForm(
            instance=profile,
            member=member,
            initial=initial_data,
        )

        # Pre-format values for HTML5 inputs (bypasses Django L10N issues)
        field_values = {
            'first_name': member.first_name or '',
            'last_name': member.last_name or '',
            'phone': member.phone or '',
            'date_of_birth': member.date_of_birth.isoformat() if member.date_of_birth else '',
            'shoe_size': member.shoe_size or '',
            'weight': str(weight_value) if weight_value is not None else '',
        }

    # Get equipment requirements
    equipment_req = get_equipment_requirements_display(member)

    # Get user's active cards
    active_cards = member.active_cards()

    # Get upcoming bookings
    upcoming_bookings = SessionBooking.objects.filter(
        attendance__member=member,
        session_datetime__gte=timezone.now(),
        cancelled_at__isnull=True
    ).select_related('schedule', 'attendance').order_by('session_datetime')[:5]

    context = {
        'form': form,
        'profile': profile,
        'field_values': field_values,
        'equipment_requirements': equipment_req,
        'active_cards': active_cards,
        'upcoming_bookings': upcoming_bookings,
        'title': 'Mijn Profiel'
    }

    return render(request, 'accounts/profile.html', context)


@login_required
def profile_quick_update(request):
    """Quick profile update endpoint for AJAX requests"""
    profile = request.user.profile
    
    if request.method == 'POST':
        form = QuickProfileUpdateForm(
            request.POST,
            instance=profile
        )
        if form.is_valid():
            # Update member fields
            if 'phone' in form.cleaned_data:
                profile.member.phone = form.cleaned_data['phone']
            if 'shoe_size' in form.cleaned_data:
                profile.member.shoe_size = form.cleaned_data['shoe_size']
            profile.member.save()
            
            # Save profile
            form.save()
            
            return render(request, 'accounts/profile_quick_update_success.html', {
                'profile': profile
            })
        else:
            return render(request, 'accounts/profile_quick_update_form.html', {
                'form': form,
                'profile': profile
            })
    else:
        form = QuickProfileUpdateForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile
    }
    
    return render(request, 'accounts/profile_quick_update_form.html', context)


def password_reset_request(request):
    """Password reset request view - sends reset email"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            try:
                user = User.objects.get(email=email)
                _send_password_reset_email(user, request)
                messages.success(
                    request,
                    'Als dit e-mailadres bij ons bekend is, ontvangt u een e-mail met instructies.'
                )
            except User.DoesNotExist:
                # Don't reveal whether email exists
                messages.success(
                    request,
                    'Als dit e-mailadres bij ons bekend is, ontvangt u een e-mail met instructies.'
                )
        return redirect('accounts:login')

    return render(request, 'accounts/password_reset.html', {'title': 'Wachtwoord Resetten'})


def _send_password_reset_email(user, request=None):
    """Generate a temporary password and send it via email."""
    import secrets
    new_password = secrets.token_urlsafe(10)
    user.set_password(new_password)
    user.save()

    subject = 'Wachtwoord Reset - Jump4Fun'
    message = (
        f'Beste {user.first_name or user.email},\n\n'
        f'Uw wachtwoord is gereset. Hieronder vindt u uw tijdelijk wachtwoord:\n\n'
        f'  Tijdelijk wachtwoord: {new_password}\n\n'
        f'Log in met dit wachtwoord en wijzig het daarna via uw profiel.\n\n'
        f'Als u deze reset niet heeft aangevraagd, neem dan contact op met de beheerder.\n\n'
        f'Met vriendelijke groeten,\n'
        f'Jump4Fun'
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        pass  # Fail silently to not reveal email info


@login_required
def change_password(request):
    """Allow authenticated users to change their password"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not request.user.check_password(current_password):
            messages.error(request, 'Huidig wachtwoord is onjuist.')
        elif len(new_password) < 8:
            messages.error(request, 'Nieuw wachtwoord moet minimaal 8 tekens bevatten.')
        elif new_password != confirm_password:
            messages.error(request, 'Nieuwe wachtwoorden komen niet overeen.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Wachtwoord succesvol gewijzigd.')
            return redirect('accounts:profile')

    return render(request, 'accounts/change_password.html', {
        'title': 'Wachtwoord Wijzigen'
    })


@login_required
def client_dashboard(request):
    """
    Main dashboard for logged-in clients
    Shows their profile, available sessions, and upcoming bookings
    """
    profile = request.user.profile
    member = profile.member
    
    # Check if profile is complete
    if not profile.profile_complete:
        messages.warning(request, 'Vul eerst uw profiel aan om sessies te kunnen boeken.')
        return redirect('accounts:profile_complete')
    
    # Get member's size category for filtering sessions
    from equipment.assignment import get_size_category_from_shoe_size
    size_category = get_size_category_from_shoe_size(member.shoe_size)

    # Get active session schedules that have capacity for their size
    all_active_schedules = SessionSchedule.objects.filter(
        is_active=True
    ).order_by('weekday', 'start_time')

    # Filter to schedules that have capacity for this size
    available_schedules = [
        s for s in all_active_schedules
        if s.has_capacity_for_size(size_category)
    ]

    # Build set of already-booked session datetimes for this member
    booked_datetimes = set(
        SessionAttendance.objects.filter(
            member=member,
            session_date__gte=timezone.now()
        ).values_list('session_date', flat=True)
    )

    # Get upcoming sessions
    # For calendar view, cover the full displayed month; for list view, 4 weeks
    upcoming_sessions = []
    now = timezone.now()
    view_mode_param = request.GET.get('view', 'list')
    if view_mode_param == 'calendar':
        try:
            cal_y = int(request.GET.get('year', now.year))
            cal_m = int(request.GET.get('month', now.month))
        except (ValueError, TypeError):
            cal_y, cal_m = now.year, now.month
        num_weeks = 6  # cover full month grid
    else:
        num_weeks = 4

    for schedule in available_schedules:
        current_date = now.date()
        for i in range(num_weeks):
            next_occurrence = schedule.get_next_occurrence(current_date)
            if next_occurrence and schedule.is_booking_open(next_occurrence):
                available_capacity = schedule.get_available_capacity_for_size(
                    next_occurrence, size_category
                )
                already_booked = next_occurrence in booked_datetimes
                upcoming_sessions.append({
                    'schedule': schedule,
                    'datetime': next_occurrence,
                    'available_capacity': available_capacity,
                    'can_book': available_capacity > 0 and not already_booked,
                    'already_booked': already_booked,
                })
            current_date = current_date + timedelta(days=7)
    
    # Sort by datetime
    upcoming_sessions.sort(key=lambda x: x['datetime'])
    
    # Get member's upcoming bookings
    my_bookings = SessionAttendance.objects.filter(
        member=member,
        session_date__gte=now
    ).select_related('session_card').order_by('session_date')[:5]
    
    # Get member's past sessions
    past_sessions = SessionAttendance.objects.filter(
        member=member,
        session_date__lt=now
    ).select_related('session_card').order_by('-session_date')[:10]
    
    # Get active cards
    active_cards = member.active_cards()
    
    # Equipment requirements
    equipment_req = get_equipment_requirements_display(member)

    # Get business event bookings for this member
    upcoming_event_bookings = BusinessEventBooking.objects.filter(
        member=member,
        event__event_datetime__gte=now
    ).select_related('event').order_by('event__event_datetime')

    past_event_bookings = BusinessEventBooking.objects.filter(
        member=member,
        event__event_datetime__lt=now
    ).select_related('event').order_by('-event__event_datetime')[:10]

    # Get available card types for card request
    available_card_types = CardType.objects.filter(is_active=True)

    view_mode = request.GET.get('view', 'list')

    # Build full month calendar for calendar view
    calendar_weeks = []
    calendar_month_label = ''
    calendar_prev_month = ''
    calendar_next_month = ''
    if view_mode == 'calendar':
        # Determine which month to show
        try:
            cal_year = int(request.GET.get('year', now.year))
            cal_month = int(request.GET.get('month', now.month))
        except (ValueError, TypeError):
            cal_year, cal_month = now.year, now.month

        calendar_month_label = date(cal_year, cal_month, 1).strftime('%B %Y')

        # Previous/next month links
        if cal_month == 1:
            calendar_prev_month = f'?view=calendar&year={cal_year - 1}&month=12'
        else:
            calendar_prev_month = f'?view=calendar&year={cal_year}&month={cal_month - 1}'
        if cal_month == 12:
            calendar_next_month = f'?view=calendar&year={cal_year + 1}&month=1'
        else:
            calendar_next_month = f'?view=calendar&year={cal_year}&month={cal_month + 1}'

        # Build index of sessions by date from upcoming_sessions
        sessions_by_date = {}
        for s in upcoming_sessions:
            d = s['datetime'].date() if hasattr(s['datetime'], 'date') else s['datetime']
            sessions_by_date.setdefault(d, []).append(s)

        # Build calendar weeks (Monday=0)
        cal = calendar.Calendar(firstweekday=0)
        today = now.date()
        for week in cal.monthdatescalendar(cal_year, cal_month):
            week_data = []
            for day in week:
                week_data.append({
                    'date': day,
                    'in_month': day.month == cal_month,
                    'is_today': day == today,
                    'sessions': sessions_by_date.get(day, []),
                })
            calendar_weeks.append(week_data)

    context = {
        'profile': profile,
        'member': member,
        'upcoming_sessions': upcoming_sessions[:10],  # Limit to 10
        'my_bookings': my_bookings,
        'past_sessions': past_sessions,
        'active_cards': active_cards,
        'equipment_requirements': equipment_req,
        'size_category': size_category,
        'upcoming_event_bookings': upcoming_event_bookings,
        'past_event_bookings': past_event_bookings,
        'available_card_types': available_card_types,
        'insurance_status': member.get_insurance_status_display(),
        'view_mode': view_mode,
        'calendar_weeks': calendar_weeks,
        'calendar_month_label': calendar_month_label,
        'calendar_prev_month': calendar_prev_month,
        'calendar_next_month': calendar_next_month,
    }

    return render(request, 'client/dashboard.html', context)


@login_required
def book_session(request, schedule_id):
    """
    Book a session for the logged-in user.
    A session card is optional - clients can book with or without one.
    """
    if request.method != 'POST':
        return redirect('accounts:client_dashboard')

    profile = request.user.profile
    member = profile.member

    # Check profile is complete
    if not profile.profile_complete:
        messages.error(request, 'Vul eerst uw profiel aan om te kunnen boeken.')
        return redirect('accounts:profile_complete')

    try:
        schedule = SessionSchedule.objects.get(id=schedule_id)
        session_datetime_str = request.POST.get('session_datetime')
        session_datetime = timezone.datetime.fromisoformat(session_datetime_str)

        # Get member's size category
        from equipment.assignment import get_size_category_from_shoe_size
        size_category = get_size_category_from_shoe_size(member.shoe_size)

        # Check if booking is open
        if not schedule.is_booking_open(session_datetime):
            messages.error(request, 'Deze sessie is niet meer beschikbaar voor boeking.')
            return redirect('accounts:client_dashboard')

        # Check capacity for this size
        if schedule.get_available_capacity_for_size(session_datetime, size_category) <= 0:
            messages.error(request, 'Deze sessie is vol voor uw schoenmaat.')
            return redirect('accounts:client_dashboard')

        # Check if already booked
        existing = SessionAttendance.objects.filter(
            member=member,
            session_date=session_datetime,
            title=schedule.title
        ).exists()

        if existing:
            messages.warning(request, 'U bent al ingeschreven voor deze sessie.')
            return redirect('accounts:client_dashboard')

        # Check if client wants to use a session card
        use_card = request.POST.get('use_card') == '1'
        card = None
        if use_card:
            active_cards = member.active_cards()
            if active_cards.exists():
                card = active_cards.first()

        # Create attendance record with size category
        attendance = SessionAttendance.objects.create(
            member=member,
            session_card=card,
            session_date=session_datetime,
            title=schedule.title,
            description=schedule.description,
            location=schedule.location,
            capacity=schedule.total_capacity,
            size_category=size_category,
            created_by=request.user.username
        )

        # Create booking
        booking = SessionBooking.objects.create(
            schedule=schedule,
            session_datetime=session_datetime,
            attendance=attendance
        )

        card_msg = ' (sessiekaart wordt gebruikt)' if card else ' (zonder sessiekaart)'
        messages.success(
            request,
            f'Succesvol ingeschreven voor {schedule.title} op {session_datetime.strftime("%d-%m-%Y om %H:%M")}!{card_msg}'
        )

    except Exception as e:
        messages.error(request, f'Fout bij boeking: {str(e)}')

    return redirect('accounts:client_dashboard')


@login_required
def cancel_booking(request, booking_id):
    """
    Cancel a booking
    """
    if request.method != 'POST':
        return redirect('accounts:client_dashboard')

    profile = request.user.profile
    member = profile.member
    
    try:
        attendance = SessionAttendance.objects.get(
            id=booking_id,
            member=member
        )
        
        # Check if session is in the future
        if attendance.session_date <= timezone.now():
            messages.error(request, 'Kan geen sessie annuleren die al is geweest.')
            return redirect('accounts:client_dashboard')
        
        session_info = f"{attendance.title} op {attendance.session_date.strftime('%d-%m-%Y om %H:%M')}"
        attendance.delete()
        
        messages.success(request, f'Boeking geannuleerd: {session_info}')
        
    except SessionAttendance.DoesNotExist:
        messages.error(request, 'Boeking niet gevonden.')
    except Exception as e:
        messages.error(request, f'Fout bij annulering: {str(e)}')

    return redirect('accounts:client_dashboard')


@login_required
def request_session_card(request):
    """
    Allow clients to request a session card.
    Sends an email notification to all admin (staff) users.
    """
    if request.method != 'POST':
        return redirect('accounts:client_dashboard')

    profile = request.user.profile
    member = profile.member

    # Get selected card type
    card_type_id = request.POST.get('card_type')
    card_type_info = 'Niet gespecificeerd'
    if card_type_id:
        try:
            ct = CardType.objects.get(id=card_type_id, is_active=True)
            card_type_info = f'{ct.name} ({ct.sessions} beurten - {ct.price} EUR)'
        except CardType.DoesNotExist:
            pass

    # Get all admin email addresses
    admin_emails = list(
        User.objects.filter(is_staff=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )

    if admin_emails:
        subject = f'Sessiekaart Aanvraag - {member.full_name}'
        message = (
            f'Beste beheerder,\n\n'
            f'{member.full_name} ({member.email}) heeft een sessiekaart aangevraagd.\n\n'
            f'Gewenste kaartsoort: {card_type_info}\n\n'
            f'Gegevens:\n'
            f'  Naam: {member.full_name}\n'
            f'  E-mail: {member.email}\n'
            f'  Telefoon: {member.phone or "Niet opgegeven"}\n'
            f'  Schoenmaat: {member.shoe_size or "Niet opgegeven"}\n\n'
            f'Gelieve deze aanvraag te verwerken in het admin paneel.\n\n'
            f'Met vriendelijke groeten,\n'
            f'Jump4Fun Systeem'
        )

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=False,
            )
            messages.success(
                request,
                'Uw aanvraag voor een sessiekaart is verstuurd. '
                'De beheerders zijn per e-mail op de hoogte gebracht.'
            )
        except Exception as e:
            messages.warning(
                request,
                'Uw aanvraag is geregistreerd, maar de e-mail kon niet worden verzonden. '
                'Neem eventueel rechtstreeks contact op met de beheerder.'
            )
    else:
        messages.warning(
            request,
            'Er zijn geen beheerders geconfigureerd om de aanvraag te ontvangen. '
            'Neem rechtstreeks contact op.'
        )

    return redirect('accounts:client_dashboard')