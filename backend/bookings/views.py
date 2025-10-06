from django.shortcuts import render, redirect
from django.db.models import Count, Sum, Q
from members.models import Member
from cards.models import SessionCard
from equipment.models import Equipment
from .models import SessionAttendance

def dashboard(request):
    """Simple dashboard view"""
    
    # Redirect non-staff users to admin login
    if not request.user.is_authenticated:
        return redirect('/admin/')
    
    # Calculate statistics
    total_members = Member.objects.count()
    total_sessions = SessionAttendance.objects.count()
    active_cards = SessionCard.objects.filter(status='active').count()
    
    # Equipment statistics
    equipment_stats = Equipment.objects.values('status').annotate(count=Count('id'))
    equipment_by_status = {stat['status']: stat['count'] for stat in equipment_stats}
    
    # Recent sessions
    recent_sessions = SessionAttendance.objects.select_related('member', 'session_card').order_by('-session_date')[:10]
    
    # Members with active cards
    members_with_cards = Member.objects.filter(
        session_cards__status='active'
    ).distinct().count()
    
    context = {
        'total_members': total_members,
        'total_sessions': total_sessions,
        'active_cards': active_cards,
        'members_with_cards': members_with_cards,
        'equipment_by_status': equipment_by_status,
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'dashboard.html', context)