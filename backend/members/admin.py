from django.contrib import admin
from django.utils.html import format_html
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'shoe_size', 'total_sessions', 'active_cards_count', 'created_at']
    list_filter = ['created_at', 'shoe_size']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'total_sessions', 'cards_info']
    
    fieldsets = (
        ('Persoonlijke Informatie', {
            'fields': ('email', 'first_name', 'last_name', 'shoe_size', 'phone')
        }),
        ('Extra', {
            'fields': ('notes',)
        }),
        ('Statistieken', {
            'fields': ('total_sessions', 'cards_info', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

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
            html += f"<li>{card.card_type} - {card.sessions_remaining} sessies over</li>"
        html += "</ul>"
        return format_html(html)
    cards_info.short_description = 'Kaarten Details'