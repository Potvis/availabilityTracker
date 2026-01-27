from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


def root_redirect(request):
    """Redirect root URL to dashboard if authenticated, otherwise to login."""
    if request.user.is_authenticated:
        return redirect('accounts:client_dashboard')
    return redirect('accounts:login')


urlpatterns = [
    path('accounts/', include('accounts.urls')),  # Account management
    path('admin/', admin.site.urls),
    path('beheer/', include('bookings.urls')),  # Admin stats dashboard
    path('', root_redirect, name='root'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Jump4Fun Beheer"
admin.site.site_title = "Kangoo Admin"
admin.site.index_title = "Welkom bij Jump4Fun Beheer"