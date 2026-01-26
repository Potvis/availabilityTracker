from django.contrib import admin
from django.utils.html import format_html
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'full_name', 'shoe_size', 'insurance_badge', 
        'notes_short', 'total_sessions', 'active_cards_count', 'created_at'
    ]
    list_filter = ['created_at', 'shoe_size', 'wants_insurance', 'insurance_status']
    search_fields = ['email', 'first_name', 'last_name', 'phone', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'total_sessions', 'cards_info']
    
    fieldsets = (
        ('Persoonlijke Informatie', {
            'fields': ('email', 'first_name', 'last_name', 'shoe_size', 'phone')
        }),
        ('Verzekering', {
            'fields': ('wants_insurance', 'insurance_status')
        }),
        ('Extra', {
            'fields': ('notes',)
        }),
        ('Statistieken', {
            'fields': ('total_sessions', 'cards_info', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def insurance_badge(self, obj):
        """Display insurance status with colored badge"""
        if not obj.wants_insurance:
            return format_html(
                '<span style="background-color: #999; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">Geen</span>'
            )
        
        colors = {
            'none': '#999',
            'requested': '#FF9800',
            'pending': '#2196F3',
            'insured': '#4CAF50',
        }
        icons = {
            'none': '○',
            'requested': '⚠️',
            'pending': '⏳',
            'insured': '✓',
        }
        
        color = colors.get(obj.insurance_status, '#999')
        icon = icons.get(obj.insurance_status, '○')
        label = obj.get_insurance_status_display()
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color, icon, label
        )
    insurance_badge.short_description = 'Verzekering'
    insurance_badge.admin_order_field = 'insurance_status'

    def notes_short(self, obj):
        """Display truncated notes"""
        if not obj.notes:
            return format_html('<span style="color: #999;">-</span>')
        
        if len(obj.notes) > 50:
            return format_html(
                '<span title="{}">{}</span>',
                obj.notes,
                obj.notes[:50] + '...'
            )
        return obj.notes
    notes_short.short_description = 'Notities'

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
    
    actions = ['mark_insurance_requested', 'mark_insurance_pending', 'mark_insurance_insured']
    
    def mark_insurance_requested(self, request, queryset):
        """Mark members as insurance requested"""
        updated = queryset.update(insurance_status='requested', wants_insurance=True)
        self.message_user(request, f'{updated} lid/leden gemarkeerd als verzekering aangevraagd.')
    mark_insurance_requested.short_description = '⚠️ Markeer als Verzekering Aangevraagd'
    
    def mark_insurance_pending(self, request, queryset):
        """Mark members as insurance pending confirmation"""
        updated = queryset.update(insurance_status='pending', wants_insurance=True)
        self.message_user(request, f'{updated} lid/leden gemarkeerd als in afwachting van bevestiging.')
    mark_insurance_pending.short_description = '⏳ Markeer als In Afwachting'
    
    def mark_insurance_insured(self, request, queryset):
        """Mark members as insured"""
        updated = queryset.update(insurance_status='insured', wants_insurance=True)
        self.message_user(request, f'{updated} lid/leden gemarkeerd als verzekerd.')
    mark_insurance_insured.short_description = '✓ Markeer als Verzekerd'