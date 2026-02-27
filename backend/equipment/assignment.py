"""
Equipment assignment utilities
Automatically assigns appropriate equipment category based on member shoe size and weight.
Supports admin overrides via Member.override_category.
"""
from equipment.models import Equipment, EquipmentCategory, SizeType, SpringType
from decimal import Decimal


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


def _find_spring_type(weight):
    """
    Find the matching SpringType for a given weight.

    Args:
        weight: Weight in kg (Decimal or float)

    Returns:
        SpringType instance or None
    """
    if not weight:
        # Default: pick the lightest spring type (lowest max_weight)
        return SpringType.objects.filter(
            is_active=True,
            max_weight__isnull=False,
        ).order_by('max_weight').first()

    if not isinstance(weight, Decimal):
        weight = Decimal(str(weight))

    # Find the first spring type whose max_weight covers this weight
    suitable = SpringType.objects.filter(
        is_active=True,
        max_weight__isnull=False,
        max_weight__gte=weight,
    ).order_by('max_weight').first()

    if suitable:
        return suitable

    # No spring type covers this weight; pick one without max_weight (heaviest-duty)
    heaviest = SpringType.objects.filter(
        is_active=True,
        max_weight__isnull=True,
    ).first()
    if heaviest:
        return heaviest

    # Fall back to the one with the highest max_weight
    return SpringType.objects.filter(
        is_active=True,
    ).order_by('-max_weight').first()


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

    spring_type = _find_spring_type(weight)
    if not spring_type:
        return None

    return EquipmentCategory.objects.filter(
        is_active=True,
        size_type=size_type,
        spring_type=spring_type,
    ).first()


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
    size_type = _find_size_type(shoe_size_str)
    if not size_type:
        return None

    spring_type = _find_spring_type(weight)
    if not spring_type:
        return None

    return EquipmentCategory.objects.filter(
        is_active=True,
        size_type=size_type,
        spring_type=spring_type,
    ).first()


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

    return Equipment.objects.filter(
        status='available',
        category=category,
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

    available_count = Equipment.objects.filter(
        status='available',
        category=category,
    ).count()

    return {
        'available': available_count >= count,
        'count': available_count,
        'message': f'{available_count} van {count} benodigd beschikbaar'
    }
