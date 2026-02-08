from django.contrib import admin
from django.utils.html import format_html
from .models import Member
from accounts.models import UserProfile
from cards.models import SessionCard


class UserProfileInline(admin.StackedInline):
    """Show user account & profile info inline on the Member page."""
    model = UserProfile
    extra = 0
    max_num = 1
    can_delete = False
    verbose_name = 'Account & Profiel'
    verbose_name_plural = 'Account & Profiel'
    fields = ('user', 'weight', 'profile_complete', 'receive_notifications', 'newsletter_subscription')
    readonly_fields = ('user', 'profile_complete')


class SessionCardInline(admin.TabularInline):
    """Show session cards inline on the Member page."""
    model = SessionCard
    extra = 0
    fields = ('card_type', 'total_sessions', 'sessions_used', 'status', 'purchased_date', 'expiry_date')
    readonly_fields = ('sessions_used',)
    verbose_name = 'Beurtenkaart'
    verbose_name_plural = 'Beurtenkaarten'


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'full_name', 'shoe_size', 'insurance_status_badge',
        'total_sessions_display', 'active_cards_count', 'created_at'
    ]
    list_filter = ['created_at', 'shoe_size', 'insurance_status']
    search_fields = ['email', 'first_name', 'last_name', 'phone', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Persoonlijke Informatie', {
            'fields': ('email', 'first_name', 'last_name', 'date_of_birth', 'phone')
        }),
        ('Schoenmaat & Verzekering', {
            'fields': ('shoe_size', 'insurance_status')
        }),
        ('Extra', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # --- list_display methods ---

    def weight_display(self, obj):
        if hasattr(obj, 'user_profile') and obj.user_profile and obj.user_profile.weight:
            w = obj.user_profile.weight
            return format_html('{}&#8239;kg', w)
        return format_html('<span style="color: gray;">-</span>')
    weight_display.short_description = 'Gewicht'
    weight_display.admin_order_field = 'user_profile__weight'

    def insurance_status_badge(self, obj):
        colors = {
            'none': 'gray',
            'requested': '#2196F3',
            'processing': '#FF9800',
            'approved': 'green',
            'refused': '#9E9E9E',
        }
        color = colors.get(obj.insurance_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color, obj.get_insurance_status_display()
        )
    insurance_status_badge.short_description = 'Verzekering'
    insurance_status_badge.admin_order_field = 'insurance_status'

    def profile_complete_badge(self, obj):
        if not hasattr(obj, 'user_profile') or not obj.user_profile:
            return format_html('<span style="color: gray;">-</span>')
        profile = obj.user_profile
        profile.check_profile_complete()
        if profile.profile_complete:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold; font-size: 11px;">Compleet</span>'
            )
        missing = len(profile.missing_fields)
        return format_html(
            '<span style="background-color: orange; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{} ontbreekt</span>',
            missing
        )
    profile_complete_badge.short_description = 'Profiel'
    profile_complete_badge.admin_order_field = 'user_profile__profile_complete'

    def total_sessions_display(self, obj):
        count = obj.total_sessions_attended()
        return format_html('<strong>{}</strong>', count)
    total_sessions_display.short_description = 'Sessies'

    def active_cards_count(self, obj):
        count = obj.active_cards().count()
        if count > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>', count
            )
        return format_html('<span style="color: gray;">0</span>')
    active_cards_count.short_description = 'Kaarten'

    def has_account_badge(self, obj):
        if hasattr(obj, 'user_profile') and obj.user_profile:
            return format_html(
                '<span style="color: green; font-weight: bold;">Ja</span>'
            )
        return format_html('<span style="color: gray;">Nee</span>')
    has_account_badge.short_description = 'Account'

    # --- actions ---

    actions = [
        'set_insurance_requested', 'set_insurance_processing',
        'set_insurance_approved', 'set_insurance_refused',
        'trigger_password_reset',
    ]

    def set_insurance_requested(self, request, queryset):
        updated = queryset.update(insurance_status='requested')
        self.message_user(request, f'{updated} lid/leden: verzekering aangevraagd.')
    set_insurance_requested.short_description = 'Verzekering -> Aangevraagd'

    def set_insurance_processing(self, request, queryset):
        updated = queryset.update(insurance_status='processing')
        self.message_user(request, f'{updated} lid/leden: verzekering in verwerking.')
    set_insurance_processing.short_description = 'Verzekering -> In verwerking'

    def set_insurance_approved(self, request, queryset):
        updated = queryset.update(insurance_status='approved')
        self.message_user(request, f'{updated} lid/leden: verzekering in orde.')
    set_insurance_approved.short_description = 'Verzekering -> In orde'

    def set_insurance_refused(self, request, queryset):
        updated = queryset.update(insurance_status='refused')
        self.message_user(request, f'{updated} lid/leden: verzekering geweigerd.')
    set_insurance_refused.short_description = 'Verzekering -> Geweigerd'

    def trigger_password_reset(self, request, queryset):
        from accounts.views import _send_password_reset_email
        count = 0
        for member in queryset:
            if hasattr(member, 'user_profile') and member.user_profile:
                _send_password_reset_email(member.user_profile.user)
                count += 1
        self.message_user(
            request,
            f'Wachtwoord reset e-mail verstuurd naar {count} gebruiker(s).'
        )
    trigger_password_reset.short_description = 'Wachtwoord reset triggeren'
