from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Profile management
    path('profile/', views.profile_view, name='profile'),
    path('profile/complete/', views.profile_complete, name='profile_complete'),
    path('profile/quick-update/', views.profile_quick_update, name='profile_quick_update'),
    
    # Password reset
    path('password-reset/', views.password_reset_request, name='password_reset'),
]
