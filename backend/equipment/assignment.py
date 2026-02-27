"""
Equipment assignment utilities
Automatically assigns appropriate equipment category based on member shoe size and weight.
Supports admin overrides via Member.override_category.
"""
from equipment.models import Equipment, EquipmentCategory, SizeType, SpringType
from decimal import Decimal
from django.db.models import Q, F


def _find_size_type(shoe_size_str):
    """
    Find the matching SizeType for a given shoe size.

    Args:
        shoe_size_str: Shoe size as string (e.g., "38", "42")

    Returns:
        SizeType instance or None
    """
    if not shoe_size_str:
        return None

    try:
        size = int(shoe_size_str)
    except (ValueError, TypeError):
        return None

    return SizeType.objects.filter(
        is_active=True,
        min_shoe_size__isnull=False,
        max_shoe_size__isnull=False,
        min_shoe_size__lte=size,
        max_shoe_size__gte=size,
    ).first()


def _find_suitable_spring_types(weight):
    """
    Find all SpringTypes suitable for a given weight, ordered by preference.
    Prefers the most specific match (lowest max_weight that covers the weight),
    with unlimited (NULL max_weight) spring types as fallback.

    Args:
        weight: Weight in kg (Decimal or float)

    Returns:
        QuerySet of suitable SpringType instances, ordered by preference
    """
    if not weight:
        # Default: pick spring types with a defined max_weight, lightest first
        return SpringType.objects.filter(
            is_active=True,
            max_weight__isnull=False,
        ).order_by('max_weight')

    if not isinstance(weight, Decimal):
        weight = Decimal(str(weight))

    # Find all spring types that can handle this weight:
    # - Those with a defined max_weight >= the user's weight
    # - Those with unlimited capacity (max_weight is NULL)
    # Order: specific (lowest sufficient max_weight) first, unlimited last
    return SpringType.objects.filter(
        is_active=True,
    ).filter(
        Q(max_weight__gte=weight) | Q(max_weight__isnull=True)
    ).order_by(F('max_weight').asc(nulls_last=True))


def get_member_category(member):
    """
    Determine the EquipmentCategory for a member.
    Admin override takes priority over automatic calculation.

    Args:
        member: Member object

    Returns:
        EquipmentCategory instance or None
    """
    # Admin override takes priority
    if member.override_category:
        return member.override_category

    # Auto-determine from shoe_size and weight
    size_type = _find_size_type(member.shoe_size)
    if not size_type:
        return None

    weight = None
    if hasattr(member, 'user_profile') and member.user_profile:
        weight = member.user_profile.weight

    suitable_springs = _find_suitable_spring_types(weight)
    if not suitable_springs.exists():
        return None

    # Find a category matching this size and any of the suitable spring types
    # Prefer the most specific spring type (lowest max_weight) over unlimited
    return EquipmentCategory.objects.filter(
        is_active=True,
        size_type=size_type,
        spring_type__in=suitable_springs,
    ).order_by(F('spring_type__max_weight').asc(nulls_last=True)).first()


def get_category_from_shoe_size_and_weight(shoe_size_str, weight):
    """
    Find the EquipmentCategory matching a given shoe size and weight.
    Used for event bookings where we don't have a member object.

    Args:
        shoe_size_str: Shoe size as string (e.g., "42")
        weight: Weight in kg

    Returns:
        EquipmentCategory instance or None
    """
    categories = get_all_categories_from_shoe_size_and_weight(shoe_size_str, weight)
    return categories.first()


def get_all_categories_from_shoe_size_and_weight(shoe_size_str, weight):
    """
    Find all EquipmentCategories matching a given shoe size and weight,
    ordered by preference (most specific spring type first).
    Used for event bookings to check availability across all compatible categories.

    Args:
        shoe_size_str: Shoe size as string (e.g., "42")
        weight: Weight in kg

    Returns:
        QuerySet of EquipmentCategory instances (may be empty)
    """
    size_type = _find_size_type(shoe_size_str)
    if not size_type:
        return EquipmentCategory.objects.none()

    suitable_springs = _find_suitable_spring_types(weight)
    if not suitable_springs.exists():
        return EquipmentCategory.objects.none()

    # Find all categories matching this size and any of the suitable spring types
    # Prefer the most specific spring type (lowest max_weight) over unlimited
    return EquipmentCategory.objects.filter(
        is_active=True,
        size_type=size_type,
        spring_type__in=suitable_springs,
    ).order_by(F('spring_type__max_weight').asc(nulls_last=True))


def find_available_equipment(category):
    """
    Find available equipment in a given category.

    Args:
        category: EquipmentCategory instance

    Returns:
        QuerySet of available Equipment objects, or empty queryset
    """
    if not category:
        return Equipment.objects.none()

    return category.get_matching_equipment().filter(
        status='available',
    )


def assign_equipment(member):
    """
    Assign appropriate equipment to a member based on their category.

    Args:
        member: Member object

    Returns:
        dict with:
            - success: bool
            - equipment: Equipment object if successful, None otherwise
            - category: EquipmentCategory or None
            - message: str describing result
    """
    if not member.shoe_size and not member.override_category:
        return {
            'success': False,
            'equipment': None,
            'category': None,
            'message': 'Schoenmaat ontbreekt in profiel'
        }

    category = get_member_category(member)

    if not category:
        return {
            'success': False,
            'equipment': None,
            'category': None,
            'message': f'Geen passende boot categorie gevonden voor schoenmaat {member.shoe_size}'
        }

    available = find_available_equipment(category)

    if not available.exists():
        return {
            'success': False,
            'equipment': None,
            'category': category,
            'message': f'Geen beschikbare Kangoo Boots voor categorie {category.name}'
        }

    equipment = available.first()

    return {
        'success': True,
        'equipment': equipment,
        'category': category,
        'message': f'Kangoo Boots toegewezen: {equipment.equipment_id}'
    }


def get_equipment_requirements_display(member):
    """
    Get a human-readable description of member's equipment requirements.
    Shows the EquipmentCategory name.

    Args:
        member: Member object

    Returns:
        dict with 'text' description and category
    """
    if not member.shoe_size and not member.override_category:
        return {
            'text': "Schoenmaat onbekend",
            'category': None,
            'shoe_size': None,
        }

    category = get_member_category(member)

    if category:
        text = category.name
    else:
        text = f"Geen categorie voor maat {member.shoe_size}"

    # Mark if admin override is active
    if member.override_category:
        text += " [handmatig]"

    return {
        'text': text,
        'category': category,
        'shoe_size': member.shoe_size,
    }


def check_equipment_availability(category, count=1):
    """
    Check if sufficient equipment is available for a given category.

    Args:
        category: EquipmentCategory instance
        count: Number of equipment items needed

    Returns:
        dict with:
            - available: bool
            - count: int (number available)
            - message: str
    """
    if not category:
        return {
            'available': False,
            'count': 0,
            'message': 'Geen categorie opgegeven'
        }

    available_count = category.get_matching_equipment().filter(
        status='available',
    ).count()

    return {
        'available': available_count >= count,
        'count': available_count,
        'message': f'{available_count} van {count} benodigd beschikbaar'
    }
