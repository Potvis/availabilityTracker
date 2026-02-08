from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Equipment, MaintenanceLog, SpringType, ShellType, SizeType


@admin.register(SizeType)
class SizeTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'min_shoe_size', 'max_shoe_size', 'equipment_count', 'description', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']

    def equipment_count(self, obj):
        count = obj.equipment_set.count()
        return format_html('<strong>{}</strong> schoenen', count)
    equipment_count.short_description = 'Gebruikt bij'


@admin.register(SpringType)
class SpringTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_weight_display', 'equipment_count', 'description', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']

    def max_weight_display(self, obj):
        if obj.max_weight:
            return format_html('{}&#8239;kg', obj.max_weight)
        return format_html('<span style="color: gray;">-</span>')
    max_weight_display.short_description = 'Max gewicht'

    def equipment_count(self, obj):
        count = obj.equipment_set.count()
        return format_html('<strong>{}</strong> schoenen', count)
    equipment_count.short_description = 'Gebruikt bij'


@admin.register(ShellType)
class ShellTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'equipment_count', 'description', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']

    def equipment_count(self, obj):
        count = obj.equipment_set.count()
        return format_html('<strong>{}</strong> schoenen', count)
    equipment_count.short_description = 'Gebruikt bij'


class MaintenanceLogInline(admin.TabularInline):
    model = MaintenanceLog
    extra = 0
    fields = ['date', 'description', 'performed_by', 'cost']

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = [
        'equipment_id', 'name', 'size', 'size_type', 'spring_type_badge',
        'shell_type_display', 'status_badge', 'last_maintenance', 'next_maintenance'
    ]
    list_filter = ['status', 'size', 'size_type', 'spring_type', 'shell_type', 'last_maintenance']
    search_fields = ['equipment_id', 'name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [MaintenanceLogInline]

    fieldsets = (
        ('Basis Informatie', {
            'fields': ('equipment_id', 'name', 'size', 'size_type', 'status')
        }),
        ('Schoen Variaties', {
            'fields': ('spring_type', 'shell_type'),
            'description': 'Elke schoen heeft 3 variaties: schoenmaat, soort veer en soort schelp.'
        }),
        ('Onderhoud', {
            'fields': ('purchase_date', 'last_maintenance', 'next_maintenance')
        }),
        ('Extra', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def shell_type_display(self, obj):
        if obj.shell_type:
            return format_html(
                '<span style="background-color: #9C27B0; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">{}</span>',
                obj.shell_type.name
            )
        return format_html('<span style="color: gray;">-</span>')
    shell_type_display.short_description = 'Schelp'

    def spring_type_badge(self, obj):
        if obj.spring_type:
            name_lower = obj.spring_type.name.lower()
            if 'hd' in name_lower:
                color = '#FF9800'
            else:
                color = '#2196F3'
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
                color, obj.spring_type.name
            )
        return format_html('<span style="color: gray;">-</span>')
    spring_type_badge.short_description = 'Veer Type'

    def status_badge(self, obj):
        colors = {
            'available': 'green',
            'maintenance': 'orange',
            'broken': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    actions = ['mark_available', 'mark_maintenance', 'mark_broken']

    def mark_available(self, request, queryset):
        updated = queryset.update(status='available')
        self.message_user(request, f'{updated} item(s) gemarkeerd als beschikbaar.')
    mark_available.short_description = 'Markeer als beschikbaar'

    def mark_maintenance(self, request, queryset):
        updated = queryset.update(status='maintenance')
        self.message_user(request, f'{updated} item(s) gemarkeerd voor onderhoud.')
    mark_maintenance.short_description = 'Markeer voor onderhoud'

    def mark_broken(self, request, queryset):
        updated = queryset.update(status='broken')
        self.message_user(request, f'{updated} item(s) gemarkeerd als defect.')
    mark_broken.short_description = 'Markeer als defect'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        summary = Equipment.objects.values('status').annotate(count=Count('id'))
        extra_context['summary'] = {item['status']: item['count'] for item in summary}
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'date', 'performed_by', 'cost', 'description_short']
    list_filter = ['date', 'equipment__status']
    search_fields = ['equipment__equipment_id', 'equipment__name', 'performed_by', 'description']
    date_hierarchy = 'date'

    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Beschrijving'
