from django.contrib import admin
from django.utils.html import format_html
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'full_name', 'date_of_birth', 'shoe_size',
        'insurance_status_badge', 'total_sessions', 'active_cards_count', 'created_at'
    ]
    list_filter = ['insurance_status', 'created_at', 'shoe_size']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'total_sessions', 'cards_info']

    fieldsets = (
        ('Persoonlijke Informatie', {
            'fields': ('email', 'first_name', 'last_name', 'date_of_birth', 'shoe_size', 'phone')
        }),
        ('Verzekering', {
            'fields': ('insurance_status',),
            'description': 'Geboortedatum is vereist voor de verzekering.'
        }),
        ('Extra', {
            'fields': ('notes',)
        }),
        ('Statistieken', {
            'fields': ('total_sessions', 'cards_info', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

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

    def total_sessions(self, obj):
        count = obj.total_sessions_attended()
        return format_html('<strong>{}</strong> sessies', count)
    total_sessions.short_description = 'Totaal Sessies'

    def active_cards_count(self, obj):
        count = obj.active_cards().count()
        if count > 0:
            return format_html('<span style="color: green;">✓ {} actieve kaart(en)</span>', count)
        return format_html('<span style="color: gray;">Geen actieve kaarten</span>')
    active_cards_count.short_description = 'Actieve Kaarten'

    def cards_info(self, obj):
        cards = obj.active_cards()
        if not cards:
            return "Geen actieve kaarten"

        html = "<ul>"
        for card in cards:
            html += f"<li>{card.card_type.name} - {card.sessions_remaining} sessies over</li>"
        html += "</ul>"
        return format_html(html)
    cards_info.short_description = 'Kaarten Details'

    actions = ['set_insurance_requested', 'set_insurance_processing', 'set_insurance_approved', 'set_insurance_refused']

    def set_insurance_requested(self, request, queryset):
        updated = queryset.update(insurance_status='requested')
        self.message_user(request, f'{updated} lid/leden: verzekering aangevraagd.')
    set_insurance_requested.short_description = 'Verzekering → Aangevraagd'

    def set_insurance_processing(self, request, queryset):
        updated = queryset.update(insurance_status='processing')
        self.message_user(request, f'{updated} lid/leden: verzekering in verwerking.')
    set_insurance_processing.short_description = 'Verzekering → In verwerking'

    def set_insurance_approved(self, request, queryset):
        updated = queryset.update(insurance_status='approved')
        self.message_user(request, f'{updated} lid/leden: verzekering in orde.')
    set_insurance_approved.short_description = 'Verzekering → In orde'

    def set_insurance_refused(self, request, queryset):
        updated = queryset.update(insurance_status='refused')
        self.message_user(request, f'{updated} lid/leden: verzekering geweigerd.')
    set_insurance_refused.short_description = 'Verzekering → Geweigerd'
