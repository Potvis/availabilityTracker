from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from bookings.event_views import event_booking_page, event_confirmation


def root_redirect(request):
    """Redirect root URL to dashboard if authenticated, otherwise to login."""
    if request.user.is_authenticated:
        return redirect('accounts:client_dashboard')
    return redirect('accounts:login')


urlpatterns = [
    path('accounts/', include('accounts.urls')),  # Account management
    path('admin/', admin.site.urls),
    path('beheer/', include('bookings.urls')),  # Admin stats dashboard

    # Business events (public, no login required)
    path('evenement/<uuid:token>/', event_booking_page, name='event_booking'),
    path('evenement/<uuid:token>/bevestiging/<int:booking_id>/', event_confirmation, name='event_confirmation'),

    path('', root_redirect, name='root'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Jump4Fun Beheer"
admin.site.site_title = "Kangoo Admin"
admin.site.index_title = "Welkom bij Jump4Fun Beheer"