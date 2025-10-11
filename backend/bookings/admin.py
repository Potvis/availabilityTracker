from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import SessionAttendance, CSVImport
from .forms import CSVImportForm
from .utils import process_csv_import

@admin.register(SessionAttendance)
class SessionAttendanceAdmin(admin.ModelAdmin):
    list_display = ['member', 'title', 'session_date', 'location', 'card_used', 'import_date']
    list_filter = ['session_date', 'location', 'title']
    search_fields = ['member__email', 'member__first_name', 'member__last_name', 'title', 'location']
    date_hierarchy = 'session_date'
    readonly_fields = ['import_date']
    
    fieldsets = (
        ('Lid & Kaart', {
            'fields': ('member', 'session_card')
        }),
        ('Sessie Details', {
            'fields': ('session_date', 'title', 'description', 'location')
        }),
        ('Capaciteit', {
            'fields': ('capacity', 'total_attendees', 'waiting_list')
        }),
        ('Tracking', {
            'fields': ('created_by', 'modified_by', 'import_date', 'notes'),
            'classes': ('collapse',)
        }),
    )

    def card_used(self, obj):
        if obj.session_card:
            return format_html(
                '<span style="color: green;">✓ {}</span>',
                obj.session_card.card_type
            )
        return format_html('<span style="color: gray;">Geen kaart</span>')
    card_used.short_description = 'Kaart Gebruikt'


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
            'site_header': 'Kangoo Jumping Beheer',
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