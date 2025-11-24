from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import UserRegistrationForm, UserLoginForm, ProfileCompletionForm, QuickProfileUpdateForm
from .models import UserProfile
from equipment.assignment import get_equipment_requirements_display


def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('bookings:dashboard')
    
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
        return redirect('bookings:dashboard')
    
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
            next_url = request.GET.get('next', 'bookings:dashboard')
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
        return redirect('bookings:dashboard')
    
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
            return redirect('bookings:dashboard')
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
