from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class ProfileCompletionMiddleware:
    """Redirect users with incomplete profiles to completion page"""
    
    EXEMPT_URLS = [
        '/accounts/profile/complete/',
        '/accounts/logout/',
        '/accounts/password-reset/',
        '/admin/',
        '/static/',
        '/media/',
        '/evenement/',
        '/bedrijf/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if user is authenticated and has profile
        if request.user.is_authenticated and hasattr(request, 'user'):
            # Skip check for exempt URLs
            if any(request.path.startswith(url) for url in self.EXEMPT_URLS):
                return self.get_response(request)
            
            # Check if profile exists and is incomplete
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                if not profile.profile_complete:
                    # Don't redirect if already on completion page
                    if request.path != reverse('accounts:profile_complete'):
                        messages.warning(
                            request,
                            'Vul eerst uw profiel aan om de volledige functionaliteit te gebruiken.'
                        )
                        return redirect('accounts:profile_complete')
        
        response = self.get_response(request)
        return response