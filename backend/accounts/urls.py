
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Client Dashboard
    path('dashboard/', views.client_dashboard, name='client_dashboard'),
    path('book/<int:schedule_id>/', views.book_session, name='book_session'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('request-card/', views.request_session_card, name='request_card'),
    
    # Profile management
    path('profile/', views.profile_view, name='profile'),
    path('profile/complete/', views.profile_complete, name='profile_complete'),
    path('profile/quick-update/', views.profile_quick_update, name='profile_quick_update'),
    
    # Password reset & change
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password/change/', views.change_password, name='change_password'),
]