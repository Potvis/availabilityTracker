from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import SessionAttendance, CSVImport
from .forms import CSVImportForm
from .utils import process_csv_import

@admin.register(SessionAttendance)
class SessionAttendanceAdmin(admin.ModelAdmin):
    list_display = ['member_name_with_size', 'title', 'session_date', 'location', 'card_used', 'card_status', 'was_present_badge', 'import_date']
    list_filter = ['session_date', 'location', 'title', 'card_session_used', 'was_present']
    search_fields = ['member__email', 'member__first_name', 'member__last_name', 'title', 'location']
    date_hierarchy = 'session_date'
    readonly_fields = ['import_date', 'card_session_used', 'is_past_session']
    
    fieldsets = (
        ('Lid & Kaart', {
            'fields': ('member', 'session_card', 'card_session_used', 'was_present')
        }),
        ('Sessie Details', {
            'fields': ('session_date', 'is_past_session', 'title', 'description', 'location')
        }),
        ('Capaciteit', {
            'fields': ('capacity', 'total_attendees', 'waiting_list')
        }),
        ('Tracking', {
            'fields': ('created_by', 'modified_by', 'import_date', 'notes'),
            'classes': ('collapse',)
        }),
    )

    def member_name_with_size(self, obj):
        """Display member name with shoe size"""
        # Use name if available, otherwise email
        if obj.member.first_name and obj.member.last_name:
            name = f"{obj.member.last_name}, {obj.member.first_name}"
        elif obj.member.last_name:
            name = obj.member.last_name
        else:
            name = obj.member.email
            
        size = obj.member.shoe_size or "?"
        return f"{name} (maat {size})"
    member_name_with_size.short_description = 'Lid (Schoenmaat)'
    member_name_with_size.admin_order_field = 'member__last_name'

    def card_used(self, obj):
        """Display which card was used with visual indicator"""
        if obj.session_card:
            is_trial = obj.session_card.card_category == 'trial'
            trial_icon = '🎓' if is_trial else ''
            color = 'green' if obj.card_session_used else 'orange'
            symbol = '✓' if obj.card_session_used else '○'
            return format_html(
                '<span style="color: {};">{} {}{}</span>',
                color, symbol, trial_icon, obj.session_card.card_type
            )
        return format_html('<span style="color: gray;">Geen kaart</span>')
    card_used.short_description = 'Kaart'
    
    def card_status(self, obj):
        """Show if card session was consumed"""
        if obj.session_card:
            if obj.card_session_used:
                return format_html(
                    '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">✓ Verbruikt</span>'
                )
            else:
                past = " (niet verleden)" if not obj.is_in_past else ""
                return format_html(
                    '<span style="background-color: orange; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">○ Gekoppeld{}</span>',
                    past
                )
        return format_html('<span style="color: gray;">-</span>')
    card_status.short_description = 'Status'
    
    def was_present_badge(self, obj):
        """Show attendance status"""
        if obj.was_present:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Ja</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Nee</span>'
        )
    was_present_badge.short_description = 'Aanwezig'
    
    def is_past_session(self, obj):
        """Show if session is in the past"""
        if obj.is_in_past:
            return format_html('<span style="color: green;">✓ Verleden</span>')
        return format_html('<span style="color: orange;">○ Toekomst</span>')
    is_past_session.short_description = 'Tijdstip'

    actions = ['print_attendance_list']

    def print_attendance_list(self, request, queryset):
        """Generate printable attendance list"""
        # Get attendances with related member data
        attendances = list(queryset.select_related('member'))
        
        # Sort alphabetically using Python
        def get_sort_key(attendance):
            member = attendance.member
            # If member has both names, use "lastname, firstname"
            if member.last_name and member.first_name:
                return f"{member.last_name.lower()}, {member.first_name.lower()}"
            # If only last name
            elif member.last_name:
                return member.last_name.lower()
            # Otherwise use email
            else:
                return member.email.lower()
        
        attendances.sort(key=get_sort_key)
        
        context = {
            'attendances': attendances,
            'session_title': attendances[0].title if attendances else 'Sessie',
            'session_date': attendances[0].session_date if attendances else '',
            'total_count': len(attendances),
        }
        
        html = render_to_string('admin/bookings/attendance_print.html', context)
        return HttpResponse(html)
    
    print_attendance_list.short_description = 'Print aanwezigheidslijst'


@admin.register(CSVImport)
class CSVImportAdmin(admin.ModelAdmin):
    list_display = ['filename', 'imported_at', 'imported_by', 'rows_processed', 'rows_created', 'rows_skipped', 'status_badge']
    list_filter = ['imported_at']
    search_fields = ['filename', 'imported_by']
    readonly_fields = ['imported_at', 'rows_processed', 'rows_created', 'rows_skipped', 'errors']
    
    # Disable the default add form - we have a custom import view instead
    def has_add_permission(self, request):
        return False
    
    fieldsets = (
        ('Bestand Informatie', {
            'fields': ('filename', 'file', 'imported_by')
        }),
        ('Import Resultaten', {
            'fields': ('imported_at', 'rows_processed', 'rows_created', 'rows_skipped')
        }),
        ('Fouten', {
            'fields': ('errors',),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        if obj.errors:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 3px 10px; border-radius: 3px;">Waarschuwingen</span>'
            )
        return format_html(
            '<span style="background-color: green; color: white; padding: 3px 10px; border-radius: 3px;">Succesvol</span>'
        )
    status_badge.short_description = 'Status'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.admin_site.admin_view(self.import_csv_view), 
                 name='bookings_csvimport_import'),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        """Custom CSV import view"""
        if request.method == 'POST':
            form = CSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES['file']
                auto_assign_cards = form.cleaned_data['auto_assign_cards']
                
                try:
                    result = process_csv_import(
                        csv_file, 
                        imported_by=request.user.username if request.user.is_authenticated else 'admin', 
                        auto_assign_cards=auto_assign_cards
                    )
                    
                    if result['errors']:
                        messages.warning(
                            request, 
                            f"Import voltooid met waarschuwingen. {result['created']} rijen toegevoegd, "
                            f"{result['skipped']} overgeslagen. Zie import record voor details."
                        )
                    else:
                        messages.success(
                            request, 
                            f"Import succesvol! {result['created']} rijen toegevoegd, {result['skipped']} overgeslagen."
                        )
                    
                    return redirect('admin:bookings_csvimport_changelist')
                except Exception as e:
                    messages.error(request, f"Fout tijdens import: {str(e)}")
        else:
            form = CSVImportForm()
        
        context = {
            'form': form,
            'title': 'CSV Bestand Importeren',
            'site_header': 'Jump4Fun Beheer',
            'site_title': 'CSV Import',
            'opts': self.model._meta,
        }
        return render(request, 'admin/bookings/csvimport/import_form.html', context)

    def changelist_view(self, request, extra_context=None):
        """Add custom button to changelist view"""
        extra_context = extra_context or {}
        extra_context['has_add_permission'] = False
        extra_context['import_url'] = 'admin:bookings_csvimport_import'
        return super().changelist_view(request, extra_context=extra_context)