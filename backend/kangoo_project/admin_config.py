"""
Custom admin layout configuration for Jump4Fun.

Reorganizes the default Django admin sidebar into logical groups:
- Leden (Members)
- Sessies & Boekingen (Sessions & Bookings + Session Cards)
- Kangoo Boots (Equipment + Maintenance)
- Bedrijven (Companies, Business Events, Business Event Bookings)
- Instellingen (Settings: Categories, Sizes, Spring/Shell Types, Card Types, CSV Imports, Auth)
"""
from django.contrib import admin


# Define the desired admin layout as ordered groups.
# Each group maps a display name to a list of (app_label, model_name) tuples.
ADMIN_GROUPS = [
    ('Leden', [
        ('members', 'member'),
    ]),
    ('Sessies & Boekingen', [
        ('bookings', 'sessionschedule'),
        ('bookings', 'sessionattendance'),
        ('cards', 'sessioncard'),
    ]),
    ('Kangoo Boots', [
        ('equipment', 'equipment'),
        ('equipment', 'maintenancelog'),
    ]),
    ('Bedrijven', [
        ('bookings', 'company'),
        ('bookings', 'businessevent'),
        ('bookings', 'businesseventbooking'),
    ]),
    ('Instellingen', [
        ('equipment', 'equipmentcategory'),
        ('equipment', 'sizetype'),
        ('equipment', 'springtype'),
        ('equipment', 'shelltype'),
        ('cards', 'cardtype'),
        ('bookings', 'csvimport'),
        ('auth', 'user'),
        ('auth', 'group'),
    ]),
]


_original_get_app_list = admin.AdminSite.get_app_list


def _custom_get_app_list(self, request, app_label=None):
    """Override get_app_list to reorganize models into custom groups."""
    original_app_list = _original_get_app_list(self, request, app_label)

    # If viewing a specific app (e.g. clicking into a model), return as-is
    if app_label:
        return original_app_list

    # Build a lookup: (app_label, model_name_lower) -> model_dict
    model_lookup = {}
    for app in original_app_list:
        for model in app['models']:
            key = (app['app_label'], model['object_name'].lower())
            model_lookup[key] = model

    # Build custom grouped app list
    custom_app_list = []
    for group_name, model_keys in ADMIN_GROUPS:
        models = []
        for app_lbl, model_name in model_keys:
            model_dict = model_lookup.pop((app_lbl, model_name), None)
            if model_dict:
                models.append(model_dict)

        if models:
            custom_app_list.append({
                'name': group_name,
                'app_label': group_name.lower().replace(' & ', '_').replace(' ', '_'),
                'app_url': '#',
                'has_module_perms': True,
                'models': models,
            })

    # Append any remaining models that weren't explicitly grouped
    for app in original_app_list:
        remaining = []
        for model in app['models']:
            key = (app['app_label'], model['object_name'].lower())
            if key in model_lookup:
                remaining.append(model)
        if remaining:
            custom_app_list.append({
                'name': app['name'],
                'app_label': app['app_label'],
                'app_url': app.get('app_url', '#'),
                'has_module_perms': app.get('has_module_perms', True),
                'models': remaining,
            })

    return custom_app_list


def configure_admin():
    """Apply custom admin configuration."""
    admin.AdminSite.get_app_list = _custom_get_app_list
    admin.site.site_header = "Jump4Fun Beheer"
    admin.site.site_title = "Jump4Fun Admin"
    admin.site.index_title = "Welkom bij Jump4Fun Beheer"
