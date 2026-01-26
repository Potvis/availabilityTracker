from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import UserRegistrationForm, UserLoginForm, ProfileCompletionForm, QuickProfileUpdateForm
from .models import UserProfile
from equipment.assignment import get_equipment_requirements_display
from django.utils import timezone
from datetime import timedelta
from bookings.schedule_models import SessionSchedule
from bookings.models import SessionAttendance

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
    
    if request.method == 'POST':
        form = ProfileCompletionForm(
            request.POST,
            instance=profile,
            member=profile.member
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Profiel bijgewerkt.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Corrigeer de fouten hieronder.')
    else:
        form = ProfileCompletionForm(
            instance=profile,
            member=profile.member
        )
    
    # Get equipment requirements
    equipment_req = get_equipment_requirements_display(profile.member)
    
    # Get user's active cards
    active_cards = profile.member.active_cards()
    
    # Get upcoming bookings
    from bookings.schedule_models import SessionBooking
    from django.utils import timezone
    
    upcoming_bookings = SessionBooking.objects.filter(
        attendance__member=profile.member,
        session_datetime__gte=timezone.now(),
        cancelled_at__isnull=True
    ).select_related('schedule', 'attendance').order_by('session_datetime')[:5]
    
    context = {
        'form': form,
        'profile': profile,
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
    """Password reset request view"""
    # TODO: Implement password reset via email
    messages.info(request, 'Wachtwoord reset functie komt binnenkort beschikbaar.')
    return redirect('accounts:login')

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
    
    # Get active session schedules for their size
    available_schedules = SessionSchedule.objects.filter(
        is_active=True,
        size_category=size_category
    ).order_by('weekday', 'start_time')
    
    # Get upcoming sessions (next 2 weeks)
    upcoming_sessions = []
    now = timezone.now()
    for schedule in available_schedules:
        # Get next 4 occurrences
        current_date = now.date()
        for i in range(4):
            next_occurrence = schedule.get_next_occurrence(current_date)
            if next_occurrence and schedule.is_booking_open(next_occurrence):
                available_capacity = schedule.get_available_capacity(next_occurrence)
                upcoming_sessions.append({
                    'schedule': schedule,
                    'datetime': next_occurrence,
                    'available_capacity': available_capacity,
                    'can_book': available_capacity > 0
                })
            # Move to next week
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
    
    context = {
        'profile': profile,
        'member': member,
        'upcoming_sessions': upcoming_sessions[:10],  # Limit to 10
        'my_bookings': my_bookings,
        'past_sessions': past_sessions,
        'active_cards': active_cards,
        'equipment_requirements': equipment_req,
        'size_category': size_category,
    }
    
    return render(request, 'client/dashboard.html', context)


@login_required
def book_session(request, schedule_id):
    """
    Book a session for the logged-in user
    """
    from bookings.schedule_models import SessionSchedule, SessionBooking
    from bookings.models import SessionAttendance
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return redirect('accounts:client_dashboard')
    
    profile = request.user.profile
    member = profile.member
    
    # Check profile is complete
    if not profile.profile_complete:
        messages.error(request, 'Vul eerst uw profiel aan om te kunnen boeken.')
        return redirect('accounts:profile_complete')
    
    # Check member has active card
    active_cards = member.active_cards()
    if not active_cards.exists():
        messages.error(request, 'U heeft geen actieve sessiekaart. Koop eerst een kaart.')
        return redirect('accounts:client_dashboard')
    
    try:
        schedule = SessionSchedule.objects.get(id=schedule_id)
        session_datetime_str = request.POST.get('session_datetime')
        session_datetime = timezone.datetime.fromisoformat(session_datetime_str)
        
        # Check if booking is open
        if not schedule.is_booking_open(session_datetime):
            messages.error(request, 'Deze sessie is niet meer beschikbaar voor boeking.')
            return redirect('accounts:client_dashboard')
        
        # Check capacity
        if schedule.get_available_capacity(session_datetime) <= 0:
            messages.error(request, 'Deze sessie is vol.')
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
        
        # Create attendance record
        card = active_cards.first()
        attendance = SessionAttendance.objects.create(
            member=member,
            session_card=card,
            session_date=session_datetime,
            title=schedule.title,
            description=schedule.description,
            location=schedule.location,
            capacity=schedule.max_capacity,
            created_by=request.user.username
        )
        
        # Create booking
        booking = SessionBooking.objects.create(
            schedule=schedule,
            session_datetime=session_datetime,
            attendance=attendance
        )
        
        messages.success(
            request, 
            f'Succesvol ingeschreven voor {schedule.title} op {session_datetime.strftime("%d-%m-%Y om %H:%M")}!'
        )
        
    except Exception as e:
        messages.error(request, f'Fout bij boeking: {str(e)}')
    
    return redirect('accounts:client_dashboard')


@login_required
def cancel_booking(request, booking_id):
    """
    Cancel a booking
    """
    from bookings.models import SessionAttendance
    
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