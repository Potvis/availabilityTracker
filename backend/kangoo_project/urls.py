from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('accounts/', include('accounts.urls')),  # Account management
    path('admin/', admin.site.urls),
    path('', include('bookings.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Jump4Fun Beheer"
admin.site.site_title = "Kangoo Admin"
admin.site.index_title = "Welkom bij Jump4Fun Beheer"