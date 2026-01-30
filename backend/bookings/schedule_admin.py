from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .schedule_models import SessionSchedule, SessionBooking, BusinessEvent, BusinessEventBooking, Company


@admin.register(SessionSchedule)
class SessionScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'weekday_time_display', 'title', 'equipment_capacities_display',
        'total_capacity_display', 'is_active_badge', 'booking_window_display'
    ]
    list_filter = ['is_active', 'weekday', 'location']
    search_fields = ['title', 'description', 'location']

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

    def equipment_capacities_display(self, obj):
        capacities = SessionSchedule.get_equipment_capacities()

        if sum(capacities.values()) == 0:
            return format_html('<span style="color: gray;">Geen apparatuur beschikbaar</span>')

        colors = {
            'S': '#2196F3',
            'M': '#4CAF50',
            'L': '#FF9800',
            'XL': '#F44336'
        }

        badges = []
        for size in ['S', 'M', 'L', 'XL']:
            count = capacities.get(size, 0)
            if count > 0:
                color = colors.get(size, 'gray')
                badges.append(
                    f'<span style="background-color: {color}; color: white; '
                    f'padding: 2px 8px; border-radius: 3px; font-size: 11px; '
                    f'margin-right: 4px;">{size}: {count}</span>'
                )

        return format_html(' '.join(badges)) if badges else format_html(
            '<span style="color: gray;">Geen capaciteit</span>'
        )
    equipment_capacities_display.short_description = 'Apparatuur'

    def total_capacity_display(self, obj):
        total = obj.total_capacity
        if total == 0:
            return format_html('<span style="color: gray;">0</span>')

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
                'border-radius: 3px; font-weight: bold;">Actief</span>'
            )
        return format_html(
            '<span style="background-color: gray; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">Inactief</span>'
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
        if not change:
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
                'border-radius: 3px; font-weight: bold;">Geannuleerd</span>'
            )

        if obj.session_datetime < timezone.now():
            if obj.attendance.was_present:
                return format_html(
                    '<span style="background-color: green; color: white; padding: 3px 10px; '
                    'border-radius: 3px; font-weight: bold;">Aanwezig</span>'
                )
            else:
                return format_html(
                    '<span style="background-color: orange; color: white; padding: 3px 10px; '
                    'border-radius: 3px; font-weight: bold;">Afwezig</span>'
                )

        return format_html(
            '<span style="background-color: #2196F3; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">Gepland</span>'
        )
    status_badge.short_description = 'Status'

    actions = ['cancel_bookings']

    def cancel_bookings(self, request, queryset):
        active_bookings = queryset.filter(cancelled_at__isnull=True)
        count = 0
        for booking in active_bookings:
            booking.cancel(reason='Geannuleerd door admin')
            count += 1
        self.message_user(request, f'{count} boeking(en) geannuleerd.')
    cancel_bookings.short_description = 'Annuleer geselecteerde boekingen'


class BusinessEventInline(admin.TabularInline):
    model = BusinessEvent
    extra = 1
    fields = ['title', 'event_datetime', 'duration_minutes', 'location', 'max_capacity', 'is_active']
    readonly_fields = ['token']
    show_change_link = True


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'contact_email', 'events_count',
        'allow_multiple_bookings_badge', 'shareable_link_display', 'is_active_badge'
    ]
    list_filter = ['is_active', 'allow_multiple_bookings']
    search_fields = ['name', 'contact_email']
    readonly_fields = ['token', 'created_at', 'updated_at', 'shareable_link_readonly']
    inlines = [BusinessEventInline]

    fieldsets = (
        ('Bedrijf Informatie', {
            'fields': ('name', 'contact_email', 'contact_phone')
        }),
        ('Instellingen', {
            'fields': ('allow_multiple_bookings', 'is_active')
        }),
        ('Deelbare Link', {
            'fields': ('token', 'shareable_link_readonly'),
            'description': 'Stuur deze link naar het bedrijf. Gebruikers kiezen zelf het gewenste event.'
        }),
        ('Extra', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def events_count(self, obj):
        count = obj.events.count()
        future = obj.events.filter(event_datetime__gt=timezone.now()).count()
        return format_html(
            '<span style="font-weight: bold;">{} totaal ({} toekomstig)</span>',
            count, future
        )
    events_count.short_description = 'Events'

    def allow_multiple_bookings_badge(self, obj):
        if obj.allow_multiple_bookings:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">Ja</span>'
            )
        return format_html(
            '<span style="background-color: gray; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">Nee</span>'
        )
    allow_multiple_bookings_badge.short_description = 'Meerdere Events'

    def shareable_link_display(self, obj):
        return format_html(
            '<code style="background: #000; padding: 2px 8px; border-radius: 4px; '
            'font-size: 11px;">/bedrijf/{}/</code>',
            obj.token
        )
    shareable_link_display.short_description = 'Link'

    def shareable_link_readonly(self, obj):
        if obj.pk:
            return format_html(
                '<code style="background: #000; padding: 8px 12px; border-radius: 6px; '
                'font-size: 14px; display: inline-block;">'
                '/bedrijf/{}/</code>'
                '<p style="margin-top: 5px; color: #6b7280; font-size: 13px;">'
                'Voeg het domein toe voor de volledige URL, bijv. https://uwdomein.be/bedrijf/{}/'
                '</p>',
                obj.token, obj.token
            )
        return '-'
    shareable_link_readonly.short_description = 'Volledige Link'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">Actief</span>'
            )
        return format_html(
            '<span style="background-color: gray; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">Inactief</span>'
        )
    is_active_badge.short_description = 'Status'


class BusinessEventBookingInline(admin.TabularInline):
    model = BusinessEventBooking
    extra = 0
    readonly_fields = ['booked_at', 'size_category']
    fields = [
        'first_name', 'last_name', 'email', 'phone',
        'shoe_size', 'weight', 'size_category', 'member', 'booked_at'
    ]


@admin.register(BusinessEvent)
class BusinessEventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'company_display', 'event_datetime_display', 'location',
        'bookings_count_display', 'capacity_display',
        'shareable_link_display', 'is_active_badge'
    ]
    list_filter = ['is_active', 'company', 'event_datetime', 'location']
    search_fields = ['title', 'description', 'location', 'company__name']
    readonly_fields = ['token', 'created_at', 'updated_at', 'shareable_link_readonly']
    inlines = [BusinessEventBookingInline]

    fieldsets = (
        ('Evenement Informatie', {
            'fields': ('company', 'title', 'description', 'location')
        }),
        ('Planning', {
            'fields': ('event_datetime', 'duration_minutes')
        }),
        ('Capaciteit & Status', {
            'fields': ('max_capacity', 'is_active')
        }),
        ('Deelbare Link', {
            'fields': ('token', 'shareable_link_readonly'),
            'description': 'Stuur deze link naar gasten zodat ze zich kunnen inschrijven.'
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def company_display(self, obj):
        if obj.company:
            return format_html(
                '<span style="font-weight: bold;">{}</span>',
                obj.company.name
            )
        return format_html('<span style="color: gray;">-</span>')
    company_display.short_description = 'Bedrijf'

    def event_datetime_display(self, obj):
        color = '#667eea' if obj.is_in_future else '#6b7280'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.event_datetime.strftime('%d-%m-%Y %H:%M')
        )
    event_datetime_display.short_description = 'Datum & Tijd'
    event_datetime_display.admin_order_field = 'event_datetime'

    def bookings_count_display(self, obj):
        return format_html('<span style="font-weight: bold;">{}</span>', obj.bookings_count)
    bookings_count_display.short_description = 'Boekingen'

    def capacity_display(self, obj):
        spots = obj.get_available_spots()
        total = obj.bookings_count + spots
        if spots > 0:
            color = 'green' if spots > 3 else 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} vrij van {}</span>',
            color, spots, total
        )
    capacity_display.short_description = 'Capaciteit'

    def shareable_link_display(self, obj):
        return format_html(
            '<code style="background: #000; padding: 2px 8px; border-radius: 4px; '
            'font-size: 11px;">/evenement/{}/</code>',
            obj.token
        )
    shareable_link_display.short_description = 'Link'

    def shareable_link_readonly(self, obj):
        if obj.pk:
            return format_html(
                '<code style="background: #000; padding: 8px 12px; border-radius: 6px; '
                'font-size: 14px; display: inline-block;">'
                '/evenement/{}/</code>'
                '<p style="margin-top: 5px; color: #6b7280; font-size: 13px;">'
                'Voeg het domein toe, bijv. https://uwdomein.be/evenement/{}/'
                '</p>',
                obj.token, obj.token
            )
        return '-'
    shareable_link_readonly.short_description = 'Volledige Link'

    def is_active_badge(self, obj):
        if obj.is_active and obj.is_in_future:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">Actief</span>'
            )
        elif not obj.is_in_future:
            return format_html(
                '<span style="background-color: gray; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">Verlopen</span>'
            )
        return format_html(
            '<span style="background-color: orange; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">Inactief</span>'
        )
    is_active_badge.short_description = 'Status'

    actions = ['activate_events', 'deactivate_events']

    def activate_events(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} evenement(en) geactiveerd.')
    activate_events.short_description = 'Activeer geselecteerde evenementen'

    def deactivate_events(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} evenement(en) gedeactiveerd.')
    deactivate_events.short_description = 'Deactiveer geselecteerde evenementen'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user.username if request.user.is_authenticated else 'admin'
        super().save_model(request, obj, form, change)


@admin.register(BusinessEventBooking)
class BusinessEventBookingAdmin(admin.ModelAdmin):
    list_display = [
        'guest_name', 'event_title', 'email', 'phone',
        'shoe_size', 'weight', 'size_category', 'has_account_badge', 'booked_at'
    ]
    list_filter = ['event', 'event__company', 'size_category', 'booked_at']
    search_fields = [
        'first_name', 'last_name', 'email',
        'event__title', 'event__company__name'
    ]
    readonly_fields = ['booked_at', 'size_category']
    date_hierarchy = 'booked_at'

    fieldsets = (
        ('Evenement', {
            'fields': ('event',)
        }),
        ('Gast Informatie', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Apparatuur', {
            'fields': ('shoe_size', 'weight', 'size_category')
        }),
        ('Account', {
            'fields': ('member',),
            'description': 'Optioneel gekoppeld aan een lid.'
        }),
        ('Tracking', {
            'fields': ('booked_at',),
            'classes': ('collapse',)
        }),
    )

    def guest_name(self, obj):
        return obj.full_name
    guest_name.short_description = 'Gast'
    guest_name.admin_order_field = 'last_name'

    def event_title(self, obj):
        return obj.event.title
    event_title.short_description = 'Evenement'

    def has_account_badge(self, obj):
        if obj.member:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 11px;">Lid</span>'
            )
        return format_html(
            '<span style="background-color: gray; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">Gast</span>'
        )
    has_account_badge.short_description = 'Account'
