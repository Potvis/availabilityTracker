"""
Equipment assignment utilities
Automatically assigns appropriate equipment based on member shoe size and weight.
Supports admin overrides and dynamic SizeType / SpringType configuration.
"""
from equipment.models import Equipment, SizeType, SpringType
from decimal import Decimal


def get_size_category_from_shoe_size(shoe_size_str):
    """
    Convert shoe size string to equipment size category.
    First tries to match against admin-managed SizeType records,
    then falls back to hardcoded ranges.

    Args:
        shoe_size_str: Shoe size as string (e.g., "38", "42", etc.)

    Returns:
        Size category name (e.g. 'S', 'M', 'L', 'XL') or None
    """
    if not shoe_size_str:
        return None

    try:
        size = int(shoe_size_str)
    except (ValueError, TypeError):
        return None

    # Try dynamic SizeType lookup first
    size_type = SizeType.objects.filter(
        is_active=True,
        min_shoe_size__isnull=False,
        max_shoe_size__isnull=False,
        min_shoe_size__lte=size,
        max_shoe_size__gte=size,
    ).first()

    if size_type:
        return size_type.name

    # Fallback to hardcoded mapping
    if size <= 36:
        return 'S'  # Small (32-36)
    elif size <= 41:
        return 'M'  # Medium (37-41)
    elif size <= 46:
        return 'L'  # Large (42-46)
    else:
        return 'XL'  # Extra Large (47+)


def get_spring_type_from_weight(weight):
    """
    Determine required spring type based on weight.
    Uses admin-configured max_weight on SpringType records when available,
    falls back to hardcoded threshold.

    Args:
        weight: Weight in kg (Decimal or float)

    Returns:
        Spring type key: 'standard' or 'hd' (or SpringType name if configured)
    """
    if not weight:
        return 'standard'  # Default to standard if no weight provided

    # Convert to Decimal for precise comparison
    if not isinstance(weight, Decimal):
        weight = Decimal(str(weight))

    # Try to find a suitable spring type using max_weight from the database.
    # Spring types with max_weight set are ordered ascending; pick the first
    # one whose max_weight >= user weight.
    suitable = SpringType.objects.filter(
        is_active=True,
        max_weight__isnull=False,
        max_weight__gte=weight,
    ).order_by('max_weight').first()

    if suitable:
        return suitable.name.lower()

    # If no spring type covers this weight, pick the one without max_weight
    # (heaviest-duty), or the one with the highest max_weight.
    heaviest = SpringType.objects.filter(
        is_active=True,
        max_weight__isnull=True,
    ).first()
    if heaviest:
        return heaviest.name.lower()

    highest = SpringType.objects.filter(
        is_active=True,
    ).order_by('-max_weight').first()
    if highest:
        return highest.name.lower()

    # Fallback to hardcoded threshold
    WEIGHT_THRESHOLD = Decimal('80.00')
    return 'hd' if weight >= WEIGHT_THRESHOLD else 'standard'


# Map internal spring type keys to SpringType record names.
# This is the single source of truth linking weight-based logic to the
# admin-managed SpringType records.
SPRING_TYPE_NAMES = {
    'standard': 'Standaard',
    'standaard': 'Standaard',
    'hd': 'HD',
}


def _resolve_spring_type_name(spring_type_key):
    """Resolve a spring type key to the canonical SpringType name."""
    return SPRING_TYPE_NAMES.get(spring_type_key.lower(), spring_type_key)


def _spring_filter(spring_type_key):
    """Return a Q-compatible dict to filter Equipment by spring type name."""
    name = _resolve_spring_type_name(spring_type_key)
    return {'spring_type__name__iexact': name}


def get_member_equipment_requirements(member):
    """
    Get the effective size category and spring type for a member,
    taking admin overrides into account.

    Returns:
        (size_category, spring_type_key) tuple
    """
    # Size: admin override takes priority
    if member.override_size_type:
        size_category = member.override_size_type.name
    else:
        size_category = get_size_category_from_shoe_size(member.shoe_size)

    # Spring type: admin override takes priority
    if member.override_spring_type:
        spring_type = member.override_spring_type.name.lower()
    else:
        weight = None
        if hasattr(member, 'user_profile') and member.user_profile:
            weight = member.user_profile.weight
        spring_type = get_spring_type_from_weight(weight)

    return size_category, spring_type


def find_available_equipment(shoe_size_str, weight, session_datetime=None, member=None):
    """
    Find available equipment matching the member's requirements.

    Args:
        shoe_size_str: Member's shoe size
        weight: Member's weight in kg
        session_datetime: Optional datetime to check availability
        member: Optional Member object (used for admin overrides)

    Returns:
        QuerySet of available Equipment objects, or None if requirements can't be determined
    """
    if member:
        size_category, spring_type = get_member_equipment_requirements(member)
    else:
        size_category = get_size_category_from_shoe_size(shoe_size_str)
        if not size_category:
            return None
        spring_type = get_spring_type_from_weight(weight)

    if not size_category:
        return None

    # Find available equipment matching criteria
    # Include equipment without spring_type (not yet configured)
    from django.db.models import Q
    base_q = Q(size=size_category, status='available')
    spring_q = Q(**_spring_filter(spring_type)) | Q(spring_type__isnull=True)
    available_equipment = Equipment.objects.filter(base_q & spring_q)

    return available_equipment


def assign_equipment(member, session_datetime=None):
    """
    Assign appropriate equipment to a member based on their profile.

    Args:
        member: Member object
        session_datetime: Optional datetime for the session

    Returns:
        dict with:
            - success: bool
            - equipment: Equipment object if successful, None otherwise
            - size_category: str
            - spring_type: str
            - message: str describing result
    """
    # Check if member has required info
    if not member.shoe_size and not member.override_size_type:
        return {
            'success': False,
            'equipment': None,
            'size_category': None,
            'spring_type': None,
            'message': 'Schoenmaat ontbreekt in profiel'
        }

    size_category, spring_type = get_member_equipment_requirements(member)

    if not size_category:
        return {
            'success': False,
            'equipment': None,
            'size_category': None,
            'spring_type': spring_type,
            'message': f'Ongeldige schoenmaat: {member.shoe_size}'
        }

    # Find available equipment
    available = find_available_equipment(member.shoe_size, None, session_datetime, member=member)

    if not available or not available.exists():
        spring_desc = _resolve_spring_type_name(spring_type)
        return {
            'success': False,
            'equipment': None,
            'size_category': size_category,
            'spring_type': spring_type,
            'message': f'Geen beschikbare Kangoo Boots voor maat {size_category} met {spring_desc} veer'
        }

    # Return first available equipment
    equipment = available.first()

    return {
        'success': True,
        'equipment': equipment,
        'size_category': size_category,
        'spring_type': spring_type,
        'message': f'Kangoo Boots toegewezen: {equipment.equipment_id}'
    }


def get_member_category(member):
    """
    Find the EquipmentCategory matching a member's size and spring type requirements.

    Args:
        member: Member object

    Returns:
        EquipmentCategory instance or None
    """
    from equipment.models import EquipmentCategory

    size_category, spring_type_key = get_member_equipment_requirements(member)
    if not size_category:
        return None

    # Resolve SizeType object
    if member.override_size_type:
        size_type_obj = member.override_size_type
    else:
        size_type_obj = SizeType.objects.filter(
            is_active=True,
            name=size_category,
        ).first()

    if not size_type_obj:
        return None

    # Resolve SpringType object
    spring_name = _resolve_spring_type_name(spring_type_key)
    if member.override_spring_type:
        spring_type_obj = member.override_spring_type
    else:
        spring_type_obj = SpringType.objects.filter(
            is_active=True,
            name__iexact=spring_name,
        ).first()

    if not spring_type_obj:
        return None

    return EquipmentCategory.objects.filter(
        is_active=True,
        size_type=size_type_obj,
        spring_type=spring_type_obj,
    ).first()


def get_category_for_size_and_spring(size_category, spring_type_key):
    """
    Find the EquipmentCategory matching a given size category and spring type key.
    Used for bookings/print views where we don't have a member object.

    Args:
        size_category: e.g. 'S', 'M', 'L', 'XL'
        spring_type_key: e.g. 'standard', 'hd'

    Returns:
        EquipmentCategory instance or None
    """
    from equipment.models import EquipmentCategory

    if not size_category:
        return None

    size_type_obj = SizeType.objects.filter(
        is_active=True,
        name=size_category,
    ).first()
    if not size_type_obj:
        return None

    spring_name = _resolve_spring_type_name(spring_type_key)
    spring_type_obj = SpringType.objects.filter(
        is_active=True,
        name__iexact=spring_name,
    ).first()
    if not spring_type_obj:
        return None

    return EquipmentCategory.objects.filter(
        is_active=True,
        size_type=size_type_obj,
        spring_type=spring_type_obj,
    ).first()


def get_equipment_requirements_display(member):
    """
    Get a human-readable description of member's equipment requirements.
    Shows the EquipmentCategory name when available.

    Args:
        member: Member object

    Returns:
        dict with 'text' description and detailed components
    """
    if not member.shoe_size and not member.override_size_type:
        return {
            'text': "Schoenmaat onbekend",
            'category': None,
            'size_category': None,
            'spring_type': None,
            'shoe_size': None,
        }

    size_category, spring_type = get_member_equipment_requirements(member)

    # Try to find matching EquipmentCategory
    category = get_member_category(member)

    if category:
        text = category.name
    else:
        # Fallback if no category matches
        spring_desc = _resolve_spring_type_name(spring_type)
        text = f"Maat {size_category} - {spring_desc} veer"

    # Mark if admin overrides are active
    overrides = []
    if member.override_size_type:
        overrides.append('maat')
    if member.override_spring_type:
        overrides.append('veer')
    if overrides:
        text += f" [handmatig: {', '.join(overrides)}]"

    return {
        'text': text,
        'category': category,
        'size_category': size_category,
        'spring_type': spring_type,
        'shoe_size': member.shoe_size,
    }


def check_equipment_availability(size_category, spring_type, count=1):
    """
    Check if sufficient equipment is available for given requirements.

    Args:
        size_category: Equipment size category ('S', 'M', 'L', 'XL')
        spring_type: Spring type key ('standard', 'hd')
        count: Number of equipment items needed

    Returns:
        dict with:
            - available: bool
            - count: int (number available)
            - message: str
    """
    from django.db.models import Q
    base_q = Q(size=size_category, status='available')
    spring_q = Q(**_spring_filter(spring_type)) | Q(spring_type__isnull=True)
    available_equipment = Equipment.objects.filter(base_q & spring_q)

    available_count = available_equipment.count()

    return {
        'available': available_count >= count,
        'count': available_count,
        'message': f'{available_count} van {count} benodigd beschikbaar'
    }
