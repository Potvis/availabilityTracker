from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from .models import SessionCard, CardType

# Import SessionAttendance for inline
from bookings.models import SessionAttendance


@admin.register(CardType)
class CardTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'sessions', 'price_display', 'category_badge', 'is_active', 'sort_order']
    list_filter = ['is_active', 'category']
    list_editable = ['sort_order', 'is_active']
    search_fields = ['name']

    def price_display(self, obj):
        return format_html('<strong>{} EUR</strong>', obj.price)
    price_display.short_description = 'Prijs'

    def category_badge(self, obj):
        if obj.category == 'trial':
            return format_html(
                '<span style="background-color: #FF9800; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">Oefenbeurt</span>'
            )
        return format_html(
            '<span style="background-color: #2196F3; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">Normaal</span>'
        )
    category_badge.short_description = 'Categorie'


class SessionAttendanceInline(admin.TabularInline):
    """Show sessions that used this card"""
    model = SessionAttendance
    extra = 0
    fields = ['session_date', 'title', 'location', 'card_session_used', 'is_past']
    readonly_fields = ['session_date', 'title', 'location', 'card_session_used', 'is_past']
    can_delete = True  # Allow deleting to return session to card
    verbose_name = 'Gebruikte Sessie'
    verbose_name_plural = 'Gebruikte Sessies'

    def is_past(self, obj):
        if obj.is_in_past:
            return format_html('<span style="color: green;">✓ Verleden</span>')
        return format_html('<span style="color: orange;">○ Toekomst</span>')
    is_past.short_description = 'Tijdstip'

    def has_add_permission(self, request, obj=None):
        return False  # Don't allow adding sessions here


@admin.register(SessionCard)
class SessionCardAdmin(admin.ModelAdmin):
    list_display = ['member', 'category_badge', 'card_type', 'sessions_progress', 'status_badge', 'purchased_date', 'expiry_date']
    list_filter = ['status', 'card_type__category', 'card_type', 'purchased_date']
    search_fields = ['member__email', 'member__first_name', 'member__last_name']
    readonly_fields = ['sessions_remaining', 'created_at', 'updated_at', 'usage_summary']
    date_hierarchy = 'purchased_date'
    inlines = [SessionAttendanceInline]

    fieldsets = (
        ('Lid', {
            'fields': ('member',)
        }),
        ('Kaart Details', {
            'fields': ('card_type', 'total_sessions', 'sessions_used', 'sessions_remaining', 'status')
        }),
        ('Data & Geldigheid', {
            'fields': ('purchased_date', 'expiry_date', 'price_paid')
        }),
        ('Gebruik', {
            'fields': ('usage_summary',),
        }),
        ('Extra', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def category_badge(self, obj):
        """Show if card is a trial"""
        if obj.card_type.category == 'trial':
            return format_html(
                '<span style="background-color: #FF9800; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">Oefenbeurt</span>'
            )
        return format_html(
            '<span style="background-color: #2196F3; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">Normale Kaart</span>'
        )
    category_badge.short_description = 'Type'

    def sessions_progress(self, obj):
        """Visual progress bar for session usage"""
        percentage = (obj.sessions_used / obj.total_sessions) * 100 if obj.total_sessions > 0 else 0
        color = 'red' if percentage >= 90 else 'orange' if percentage >= 70 else 'green'

        return format_html(
            '<div style="width:100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width:{}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; line-height: 20px; font-weight: bold;">'
            '{}/{}'
            '</div></div>',
            percentage, color, obj.sessions_used, obj.total_sessions
        )
    sessions_progress.short_description = 'Voortgang'

    def status_badge(self, obj):
        """Colored badge for card status"""
        colors = {
            'active': 'green',
            'expired': 'orange',
            'completed': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def usage_summary(self, obj):
        """Show summary of how card has been used"""
        used_sessions = obj.usages.filter(card_session_used=True).count()
        pending_sessions = obj.usages.filter(card_session_used=False).count()

        trial_note = ""
        if obj.is_trial:
            trial_note = '<div style="background: #FF9800; color: white; padding: 5px; margin-bottom: 10px; border-radius: 3px; text-align: center; font-weight: bold;">DIT IS EEN OEFENBEURT</div>'

        html = f"""
        {trial_note}
        <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
            <strong>Sessie Gebruik:</strong><br/>
            <span style="color: green;">Verbruikt: {used_sessions} sessie(s)</span><br/>
            <span style="color: orange;">Gekoppeld maar niet verbruikt: {pending_sessions} sessie(s)</span><br/>
            <span style="color: gray;">Resterend: {obj.sessions_remaining} sessie(s)</span>
        </div>
        """
        return format_html(html)
    usage_summary.short_description = 'Gebruik Samenvatting'

    actions = ['mark_as_expired', 'mark_as_active']

    def mark_as_expired(self, request, queryset):
        """Manually mark cards as expired"""
        updated = queryset.update(status='expired')
        self.message_user(request, f'{updated} kaart(en) gemarkeerd als verlopen.')
    mark_as_expired.short_description = 'Markeer als verlopen'

    def mark_as_active(self, request, queryset):
        """Reactivate cards that have remaining sessions"""
        updated = queryset.filter(sessions_used__lt=models.F('total_sessions')).update(status='active')
        self.message_user(request, f'{updated} kaart(en) gemarkeerd als actief.')
    mark_as_active.short_description = 'Markeer als actief'
