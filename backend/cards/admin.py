from django.contrib import admin
from django.utils.html import format_html
from .models import SessionCard

@admin.register(SessionCard)
class SessionCardAdmin(admin.ModelAdmin):
    list_display = ['member', 'card_type', 'sessions_progress', 'status_badge', 'purchased_date', 'expiry_date']
    list_filter = ['status', 'card_type', 'purchased_date']
    search_fields = ['member__email', 'member__first_name', 'member__last_name']
    readonly_fields = ['sessions_remaining', 'created_at', 'updated_at']
    date_hierarchy = 'purchased_date'
    
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
        ('Extra', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def sessions_progress(self, obj):
        percentage = (obj.sessions_used / obj.total_sessions) * 100 if obj.total_sessions > 0 else 0
        color = 'red' if percentage >= 90 else 'orange' if percentage >= 70 else 'green'
        
        return format_html(
            '<div style="width:100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width:{}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; line-height: 20px;">'
            '{}/{}'
            '</div></div>',
            percentage, color, obj.sessions_used, obj.total_sessions
        )
    sessions_progress.short_description = 'Voortgang'

    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'expired': 'orange',
            'completed': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    actions = ['mark_as_expired', 'mark_as_active']

    def mark_as_expired(self, request, queryset):
        updated = queryset.update(status='expired')
        self.message_user(request, f'{updated} kaart(en) gemarkeerd als verlopen.')
    mark_as_expired.short_description = 'Markeer als verlopen'

    def mark_as_active(self, request, queryset):
        updated = queryset.filter(sessions_used__lt=models.F('total_sessions')).update(status='active')
        self.message_user(request, f'{updated} kaart(en) gemarkeerd als actief.')
    mark_as_active.short_description = 'Markeer als actief'