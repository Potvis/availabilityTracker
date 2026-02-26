from collections import Counter

from django.contrib import admin
from django.shortcuts import render
from django.utils.html import format_html
from django.utils import timezone
from .schedule_models import SessionSchedule, BusinessEvent, BusinessEventBooking, Company
from equipment.assignment import get_category_from_shoe_size_and_weight


@admin.register(SessionSchedule)
class SessionScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'weekday_time_display', 'title', 'start_date_display', 'end_date_display',
        'max_capacity_display', 'equipment_capacities_display',
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
        ('Capaciteit & Geldigheid', {
            'fields': ('max_capacity', 'start_date', 'end_date', 'is_active')
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
    weekday_time_display.admin_order_field = 'weekday'

    def start_date_display(self, obj):
        return obj.start_date.strftime('%d-%m-%Y')
    start_date_display.short_description = 'Startdatum'
    start_date_display.admin_order_field = 'start_date'

    def end_date_display(self, obj):
        if obj.end_date:
            return obj.end_date.strftime('%d-%m-%Y')
        return format_html('<span style="color: gray;">Onbeperkt</span>')
    end_date_display.short_description = 'Einddatum'
    end_date_display.admin_order_field = 'end_date'

    def max_capacity_display(self, obj):
        if obj.max_capacity is not None:
            return format_html(
                '<span style="font-weight: bold;">{}</span>',
                obj.max_capacity
            )
        return format_html('<span style="color: gray;">Auto</span>')
    max_capacity_display.short_description = 'Max'

    def equipment_capacities_display(self, obj):
        capacities = SessionSchedule.get_equipment_capacities()

        if not capacities or sum(capacities.values()) == 0:
            return format_html('<span style="color: gray;">Geen Kangoo Boots beschikbaar</span>')

        badges = []
        for cat_name, count in sorted(capacities.items()):
            if count > 0:
                badges.append(
                    f'<span style="background-color: #4CAF50; color: white; '
                    f'padding: 2px 8px; border-radius: 3px; font-size: 11px; '
                    f'margin-right: 4px;">{cat_name}: {count}</span>'
                )

        return format_html(' '.join(badges)) if badges else format_html(
            '<span style="color: gray;">Geen capaciteit</span>'
        )
    equipment_capacities_display.short_description = 'Kangoo Boots'

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
            '<a href="/bedrijf/{}/" target="_blank" style="background: #667eea; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px; text-decoration: none;">'
            '/bedrijf/{}/</a>',
            obj.token, obj.token
        )
    shareable_link_display.short_description = 'Link'

    def shareable_link_readonly(self, obj):
        if obj.pk:
            # Get active events for this company
            events = obj.get_active_events()
            events_html = ''
            for event in events:
                event_date = event.event_datetime.strftime('%d/%m/%Y %H:%M') if event.event_datetime else ''
                events_html += (
                    f'<div style="background: #f9fafb; padding: 8px 12px; border-radius: 6px; '
                    f'margin-bottom: 5px; font-size: 13px;">'
                    f'<strong>{event.title}</strong> - {event_date}'
                    f'</div>'
                )

            return format_html(
                '<div style="margin-bottom: 10px;">'
                '<a href="/bedrijf/{}/" target="_blank" '
                'style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
                'color: white; padding: 12px 24px; border-radius: 10px; '
                'font-size: 16px; font-weight: 600; display: inline-block; text-decoration: none; '
                'box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);">'
                'Inschrijven Kangoo Jumps {}</a>'
                '</div>'
                '<div style="margin-top: 8px; margin-bottom: 10px;">'
                '<input type="text" value="/bedrijf/{}/" readonly '
                'style="padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 6px; '
                'font-size: 13px; width: 100%; max-width: 500px; color: #4b5563;" '
                'onclick="this.select(); document.execCommand(\'copy\');">'
                '<span style="font-size: 12px; color: #6b7280; margin-left: 5px;">'
                'Klik om te kopieren (plak het domein ervoor)</span>'
                '</div>'
                '{}',
                obj.token, obj.name, obj.token,
                events_html
            )
        return '-'
    shareable_link_readonly.short_description = 'Deelbare Link'

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
    readonly_fields = ['booked_at']
    fields = [
        'first_name', 'last_name', 'email',
        'shoe_size', 'weight', 'equipment_category', 'member', 'booked_at'
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
        # Use localtime to ensure the displayed time matches the configured time
        local_dt = timezone.localtime(obj.event_datetime)
        color = '#667eea' if obj.is_in_future else '#6b7280'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, local_dt.strftime('%d-%m-%Y %H:%M')
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
            '<a href="/evenement/{}/" target="_blank" style="background: #667eea; color: white; '
            'padding: 2px 8px; border-radius: 4px; font-size: 11px; text-decoration: none;">'
            '/evenement/{}/</a>',
            obj.token, obj.token
        )
    shareable_link_display.short_description = 'Link'

    def shareable_link_readonly(self, obj):
        if obj.pk:
            event_date = obj.event_datetime.strftime('%d/%m/%Y') if obj.event_datetime else ''
            company_name = obj.company.name if obj.company else ''
            button_text = f'Inschrijven Kangoo Jumps {company_name} {event_date}'.strip()
            return format_html(
                '<div style="margin-bottom: 10px;">'
                '<a href="/evenement/{}/" target="_blank" '
                'style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
                'color: white; padding: 12px 24px; border-radius: 10px; '
                'font-size: 16px; font-weight: 600; display: inline-block; text-decoration: none; '
                'box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);">'
                '{}</a>'
                '</div>'
                '<div style="margin-top: 8px;">'
                '<input type="text" value="/evenement/{}/" readonly '
                'style="padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 6px; '
                'font-size: 13px; width: 100%; max-width: 500px; color: #4b5563;" '
                'onclick="this.select(); document.execCommand(\'copy\');">'
                '<span style="font-size: 12px; color: #6b7280; margin-left: 5px;">'
                'Klik om te kopieren (plak het domein ervoor)</span>'
                '</div>',
                obj.token, button_text, obj.token
            )
        return '-'
    shareable_link_readonly.short_description = 'Deelbare Link'

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
        'guest_name', 'event_title', 'email',
        'shoe_size', 'weight', 'category_display', 'has_account_badge', 'booked_at'
    ]
    list_filter = ['event', 'event__company', 'equipment_category', 'booked_at']
    search_fields = [
        'first_name', 'last_name', 'email',
        'event__title', 'event__company__name'
    ]
    readonly_fields = ['booked_at']
    date_hierarchy = 'booked_at'

    fieldsets = (
        ('Evenement', {
            'fields': ('event',)
        }),
        ('Gast Informatie', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Kangoo Boots', {
            'fields': ('shoe_size', 'weight', 'equipment_category')
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

    def category_display(self, obj):
        if obj.equipment_category:
            return format_html(
                '<span style="background-color: #4CAF50; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
                obj.equipment_category.name
            )
        # Fall back to computing from shoe_size/weight
        category = get_category_from_shoe_size_and_weight(obj.shoe_size, obj.weight)
        if category:
            return format_html(
                '<span style="background-color: #2196F3; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 11px;">{}</span>',
                category.name
            )
        return format_html('<span style="color: gray;">-</span>')
    category_display.short_description = 'Categorie'

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

    actions = ['print_attendance_list']

    def print_attendance_list(self, request, queryset):
        """Print attendance list with category overview for selected business event bookings."""
        bookings = queryset.select_related('event', 'member', 'equipment_category').order_by('last_name', 'first_name')

        # Build booking data with category info
        booking_data = []
        category_counter = Counter()

        for booking in bookings:
            category = booking.equipment_category
            if not category:
                category = get_category_from_shoe_size_and_weight(booking.shoe_size, booking.weight)
            category_name = category.name if category else "Onbekend"

            category_counter[category_name] += 1

            booking_data.append({
                'booking': booking,
                'category_name': category_name,
            })

        # Build category summary sorted alphabetically
        category_summary = sorted(category_counter.items(), key=lambda x: x[0])

        # Determine event info from first booking
        event = bookings.first().event if bookings.exists() else None

        return render(request, 'admin/bookings/business_event_print.html', {
            'bookings': booking_data,
            'category_summary': category_summary,
            'event': event,
            'total_count': bookings.count(),
        })
    print_attendance_list.short_description = 'Aanwezigheidslijst afdrukken'
