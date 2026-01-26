from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .schedule_models import SessionSchedule, SessionBooking, SessionSizeCapacity


class SessionSizeCapacityInline(admin.TabularInline):
    """Inline admin for setting capacity per shoe size"""
    model = SessionSizeCapacity
    extra = 4  # Show 4 rows by default (S, M, L, XL)
    max_num = 4
    min_num = 0
    verbose_name = 'Maat Capaciteit'
    verbose_name_plural = 'Capaciteit per Schoenmaat'

    def get_extra(self, request, obj=None, **kwargs):
        """Show empty rows only for new sessions"""
        if obj:
            existing = obj.size_capacities.count()
            return max(0, 4 - existing)
        return 4


@admin.register(SessionSchedule)
class SessionScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'weekday_time_display', 'title', 'size_capacities_display',
        'total_capacity_display', 'is_active_badge', 'booking_window_display'
    ]
    list_filter = ['is_active', 'weekday', 'location']
    search_fields = ['title', 'description', 'location']
    inlines = [SessionSizeCapacityInline]

    fieldsets = (
        ('Sessie Informatie', {
            'fields': ('title', 'description', 'location')
        }),
        ('Planning', {
            'fields': ('weekday', 'start_time', 'duration_minutes')
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

    def size_capacities_display(self, obj):
        """Display capacity per size with color badges"""
        capacities = obj.size_capacities.all()
        if not capacities:
            return format_html('<span style="color: gray;">Geen maten ingesteld</span>')

        colors = {
            'S': '#2196F3',
            'M': '#4CAF50',
            'L': '#FF9800',
            'XL': '#F44336'
        }

        badges = []
        for sc in capacities:
            if sc.capacity > 0:
                color = colors.get(sc.size_category, 'gray')
                badges.append(
                    f'<span style="background-color: {color}; color: white; '
                    f'padding: 2px 8px; border-radius: 3px; font-size: 11px; '
                    f'margin-right: 4px;">{sc.size_category}: {sc.capacity}</span>'
                )

        return format_html(' '.join(badges)) if badges else format_html(
            '<span style="color: gray;">Geen capaciteit</span>'
        )
    size_capacities_display.short_description = 'Maten'

    def total_capacity_display(self, obj):
        """Display total capacity across all sizes"""
        total = obj.total_capacity
        if total == 0:
            return format_html('<span style="color: gray;">0</span>')

        # Get next occurrence to show availability
        next_session = obj.get_next_occurrence()
        if next_session:
            available = obj.get_available_capacity(next_session)
            percentage = (available / total) * 100 if total > 0 else 0

            if percentage > 50:
                color = 'green'
            elif percentage > 20:
                color = 'orange'
            else:
                color = 'red'

            return format_html(
                '<span style="color: {}; font-weight: bold;">{}/{} vrij</span>',
                color, available, total
            )
        return format_html('<span>{} totaal</span>', total)
    total_capacity_display.short_description = 'Capaciteit'
    
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
    list_filter = ['cancelled_at', 'booked_at', 'schedule__weekday']
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
        size_info = ''
        if obj.attendance.size_category:
            size_info = f'<br><span style="color: gray; font-size: 11px;">Maat {obj.attendance.size_category}</span>'
        return format_html(
            '{}{}',
            obj.schedule.title,
            size_info
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
