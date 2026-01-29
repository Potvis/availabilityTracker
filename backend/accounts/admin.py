from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'member_email', 'profile_complete_badge', 
        'weight', 'shoe_size', 'created_at'
    ]
    list_filter = ['profile_complete', 'receive_notifications', 'created_at']
    search_fields = [
        'user__username', 'user__email', 'member__email', 
        'member__first_name', 'member__last_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'profile_complete_status']
    
    fieldsets = (
        ('Account Informatie', {
            'fields': ('user', 'member')
        }),
        ('Fysieke Gegevens', {
            'fields': ('weight',)
        }),
        ('Voorkeuren', {
            'fields': ('receive_notifications', 'newsletter_subscription')
        }),
        ('Status', {
            'fields': ('profile_complete_status', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def member_email(self, obj):
        return obj.member.email
    member_email.short_description = 'Lid Email'
    member_email.admin_order_field = 'member__email'
    
    def shoe_size(self, obj):
        return obj.member.shoe_size or '-'
    shoe_size.short_description = 'Schoenmaat'
    
    def profile_complete_badge(self, obj):
        obj.check_profile_complete()  # Ensure it's up to date
        
        if obj.profile_complete:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">✓ Compleet</span>'
            )
        else:
            missing = len(obj.missing_fields)
            return format_html(
                '<span style="background-color: orange; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">⚠ {} veld(en) ontbreken</span>',
                missing
            )
    profile_complete_badge.short_description = 'Profiel Status'
    
    def profile_complete_status(self, obj):
        obj.check_profile_complete()
        
        if obj.profile_complete:
            return format_html(
                '<div style="background: #d4edda; padding: 15px; border-radius: 5px;">'
                '<strong style="color: #155724;">✓ Profiel is compleet</strong>'
                '</div>'
            )
        else:
            missing_list = '<br>'.join(f'• {field}' for field in obj.missing_fields)
            return format_html(
                '<div style="background: #fff3cd; padding: 15px; border-radius: 5px;">'
                '<strong style="color: #856404;">⚠ Ontbrekende velden:</strong><br><br>{}'
                '</div>',
                missing_list
            )
    profile_complete_status.short_description = 'Profiel Compleetheid'
    
    actions = ['send_profile_completion_reminder', 'trigger_password_reset']

    def send_profile_completion_reminder(self, request, queryset):
        """Send email reminder to complete profile"""
        incomplete_profiles = queryset.filter(profile_complete=False)
        count = incomplete_profiles.count()

        # TODO: Implement email sending
        self.message_user(
            request,
            f'{count} gebruiker(s) geselecteerd voor herinnering (email functionaliteit nog te implementeren).'
        )
    send_profile_completion_reminder.short_description = 'Verstuur profiel voltooiing herinnering'

    def trigger_password_reset(self, request, queryset):
        """Admin triggers password reset for selected users"""
        from .views import _send_password_reset_email
        count = 0
        for profile in queryset:
            _send_password_reset_email(profile.user)
            count += 1
        self.message_user(
            request,
            f'Wachtwoord reset e-mail verstuurd naar {count} gebruiker(s).'
        )
    trigger_password_reset.short_description = 'Wachtwoord reset triggeren'
