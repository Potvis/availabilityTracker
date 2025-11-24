from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .schedule_models import SessionSchedule, SessionBooking


@admin.register(SessionSchedule)
class SessionScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'weekday_time_display', 'title', 'size_category_badge', 
        'capacity_display', 'is_active_badge', 'booking_window_display'
    ]
    list_filter = ['is_active', 'weekday', 'size_category', 'location']
    search_fields = ['title', 'description', 'location']
    
    fieldsets = (
        ('Sessie Informatie', {
            'fields': ('title', 'description', 'size_category', 'location')
        }),
        ('Planning', {
            'fields': ('weekday', 'start_time', 'duration_minutes')
        }),
        ('Capaciteit', {
            'fields': ('max_capacity',)
        }),
        ('Boekingsvenster', {
            'fields': ('booking_opens_days_before', 'booking_closes_hours_before')
        }),
        ('Geldigheid', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def weekday_time_display(self, obj):
        return format_html(
            '<strong>{}</strong><br>{}',
            obj.get_weekday_display(),
            obj.start_time.strftime('%H:%M')
        )
    weekday_time_display.short_description = 'Dag & Tijd'
    
    def size_category_badge(self, obj):
        colors = {
            'S': '#2196F3',
            'M': '#4CAF50',
            'L': '#FF9800',
            'XL': '#F44336'
        }
        color = colors.get(obj.size_category, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; '
            'border-radius: 3px; font-weight: bold;">Maat {}</span>',
            color, obj.size_category
        )
    size_category_badge.short_description = 'Schoenmaat'
    
    def capacity_display(self, obj):
        # Get next occurrence
        next_session = obj.get_next_occurrence()
        if next_session:
            available = obj.get_available_capacity(next_session)
            percentage = (available / obj.max_capacity) * 100 if obj.max_capacity > 0 else 0
            
            if percentage > 50:
                color = 'green'
            elif percentage > 20:
                color = 'orange'
            else:
                color = 'red'
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}/{} vrij</span>',
                color, available, obj.max_capacity
            )
        return format_html('<span>{} plaatsen</span>', obj.max_capacity)
    capacity_display.short_description = 'Capaciteit'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">✓ Actief</span>'
            )
        return format_html(
            '<span style="background-color: gray; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">✗ Inactief</span>'
        )
    is_active_badge.short_description = 'Status'
    
    def booking_window_display(self, obj):
        return format_html(
            'Open: {} dagen voor<br>Sluit: {} uur voor',
            obj.booking_opens_days_before,
            obj.booking_closes_hours_before
        )
    booking_window_display.short_description = 'Boekingsvenster'
    
    actions = ['activate_schedules', 'deactivate_schedules', 'duplicate_schedule']
    
    def activate_schedules(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} sessie schema(s) geactiveerd.')
    activate_schedules.short_description = 'Activeer geselecteerde schemas'
    
    def deactivate_schedules(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} sessie schema(s) gedeactiveerd.')
    deactivate_schedules.short_description = 'Deactiveer geselecteerde schemas'
    
    def duplicate_schedule(self, request, queryset):
        """Duplicate selected schedules"""
        for schedule in queryset:
            schedule.pk = None
            schedule.title = f"{schedule.title} (Kopie)"
            schedule.is_active = False
            schedule.save()
        
        count = queryset.count()
        self.message_user(
            request, 
            f'{count} sessie schema(s) gedupliceerd (gemarkeerd als inactief).'
        )
    duplicate_schedule.short_description = 'Dupliceer geselecteerde schemas'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user.username if request.user.is_authenticated else 'admin'
        super().save_model(request, obj, form, change)


@admin.register(SessionBooking)
class SessionBookingAdmin(admin.ModelAdmin):
    list_display = [
        'member_name', 'schedule_info', 'session_datetime', 
        'booked_at', 'status_badge'
    ]
    list_filter = ['cancelled_at', 'schedule__size_category', 'booked_at']
    search_fields = [
        'attendance__member__email', 
        'attendance__member__first_name', 
        'attendance__member__last_name',
        'schedule__title'
    ]
    date_hierarchy = 'session_datetime'
    
    readonly_fields = ['booked_at', 'cancelled_at']
    
    fieldsets = (
        ('Boeking Informatie', {
            'fields': ('schedule', 'session_datetime', 'attendance')
        }),
        ('Status', {
            'fields': ('booked_at', 'cancelled_at', 'cancellation_reason')
        }),
    )
    
    def member_name(self, obj):
        return obj.attendance.member.full_name
    member_name.short_description = 'Lid'
    member_name.admin_order_field = 'attendance__member__last_name'
    
    def schedule_info(self, obj):
        return format_html(
            '{}<br><span style="color: gray; font-size: 11px;">Maat {}</span>',
            obj.schedule.title,
            obj.schedule.size_category
        )
    schedule_info.short_description = 'Sessie'
    
    def status_badge(self, obj):
        if obj.is_cancelled:
            return format_html(
                '<span style="background-color: red; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">✗ Geannuleerd</span>'
            )
        
        # Check if session is in the past
        if obj.session_datetime < timezone.now():
            if obj.attendance.was_present:
                return format_html(
                    '<span style="background-color: green; color: white; padding: 3px 10px; '
                    'border-radius: 3px; font-weight: bold;">✓ Aanwezig</span>'
                )
            else:
                return format_html(
                    '<span style="background-color: orange; color: white; padding: 3px 10px; '
                    'border-radius: 3px; font-weight: bold;">○ Afwezig</span>'
                )
        
        return format_html(
            '<span style="background-color: #2196F3; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">→ Gepland</span>'
        )
    status_badge.short_description = 'Status'
    
    actions = ['cancel_bookings']
    
    def cancel_bookings(self, request, queryset):
        """Cancel selected bookings"""
        active_bookings = queryset.filter(cancelled_at__isnull=True)
        count = 0
        
        for booking in active_bookings:
            booking.cancel(reason='Geannuleerd door admin')
            count += 1
        
        self.message_user(request, f'{count} boeking(en) geannuleerd.')
    cancel_bookings.short_description = 'Annuleer geselecteerde boekingen'
