"""
Equipment assignment utilities
Automatically assigns appropriate equipment based on member shoe size and weight
"""
from equipment.models import Equipment
from decimal import Decimal


def get_size_category_from_shoe_size(shoe_size_str):
    """
    Convert shoe size string to equipment size category.
    
    Args:
        shoe_size_str: Shoe size as string (e.g., "38", "42", etc.)
    
    Returns:
        Size category: 'S', 'M', 'L', or 'XL'
    """
    if not shoe_size_str:
        return None
    
    try:
        size = int(shoe_size_str)
    except (ValueError, TypeError):
        return None
    
    # Size mapping based on Equipment.SIZE_CHOICES
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
    
    Args:
        weight: Weight in kg (Decimal or float)
    
    Returns:
        Spring type: 'standard' or 'hd'
    """
    if not weight:
        return 'standard'  # Default to standard if no weight provided
    
    # Convert to Decimal for precise comparison
    if not isinstance(weight, Decimal):
        weight = Decimal(str(weight))
    
    # HD springs for heavier users (typically 80kg+)
    WEIGHT_THRESHOLD = Decimal('80.00')
    
    return 'hd' if weight >= WEIGHT_THRESHOLD else 'standard'


def find_available_equipment(shoe_size_str, weight, session_datetime=None):
    """
    Find available equipment matching the member's requirements.
    
    Args:
        shoe_size_str: Member's shoe size
        weight: Member's weight in kg
        session_datetime: Optional datetime to check availability
    
    Returns:
        QuerySet of available Equipment objects, or None if requirements can't be determined
    """
    size_category = get_size_category_from_shoe_size(shoe_size_str)
    if not size_category:
        return None
    
    spring_type = get_spring_type_from_weight(weight)
    
    # Find available equipment matching criteria
    available_equipment = Equipment.objects.filter(
        size=size_category,
        spring_type=spring_type,
        status='available'
    )
    
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
    if not member.shoe_size:
        return {
            'success': False,
            'equipment': None,
            'size_category': None,
            'spring_type': None,
            'message': 'Schoenmaat ontbreekt in profiel'
        }
    
    # Get weight from user profile if available
    weight = None
    if hasattr(member, 'user_profile') and member.user_profile:
        weight = member.user_profile.weight
    
    # Determine requirements
    size_category = get_size_category_from_shoe_size(member.shoe_size)
    spring_type = get_spring_type_from_weight(weight)
    
    if not size_category:
        return {
            'success': False,
            'equipment': None,
            'size_category': None,
            'spring_type': spring_type,
            'message': f'Ongeldige schoenmaat: {member.shoe_size}'
        }
    
    # Find available equipment
    available = find_available_equipment(member.shoe_size, weight, session_datetime)
    
    if not available or not available.exists():
        return {
            'success': False,
            'equipment': None,
            'size_category': size_category,
            'spring_type': spring_type,
            'message': f'Geen beschikbare apparatuur voor maat {size_category} met {spring_type} veer'
        }
    
    # Return first available equipment
    equipment = available.first()
    
    return {
        'success': True,
        'equipment': equipment,
        'size_category': size_category,
        'spring_type': spring_type,
        'message': f'Apparatuur toegewezen: {equipment.equipment_id}'
    }


def get_equipment_requirements_display(member):
    """
    Get a human-readable description of member's equipment requirements.
    
    Args:
        member: Member object
    
    Returns:
        str: Description of requirements
    """
    if not member.shoe_size:
        return "Schoenmaat onbekend"
    
    size_category = get_size_category_from_shoe_size(member.shoe_size)
    
    weight = None
    if hasattr(member, 'user_profile') and member.user_profile:
        weight = member.user_profile.weight
    
    spring_type = get_spring_type_from_weight(weight)
    
    spring_desc = "HD veer" if spring_type == 'hd' else "Standaard veer"
    
    size_ranges = {
        'S': '32-36',
        'M': '37-41',
        'L': '42-46',
        'XL': '47+'
    }
    
    size_range = size_ranges.get(size_category, '?')
    
    return f"Maat {size_category} ({size_range}) - {spring_desc}"


def check_equipment_availability(size_category, spring_type, count=1):
    """
    Check if sufficient equipment is available for given requirements.
    
    Args:
        size_category: Equipment size category ('S', 'M', 'L', 'XL')
        spring_type: Spring type ('standard', 'hd')
        count: Number of equipment items needed
    
    Returns:
        dict with:
            - available: bool
            - count: int (number available)
            - message: str
    """
    available_equipment = Equipment.objects.filter(
        size=size_category,
        spring_type=spring_type,
        status='available'
    )
    
    available_count = available_equipment.count()
    
    return {
        'available': available_count >= count,
        'count': available_count,
        'message': f'{available_count} van {count} benodigd beschikbaar'
    }
