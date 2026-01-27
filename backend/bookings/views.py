from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from members.models import Member
from cards.models import SessionCard
from equipment.models import Equipment
from .models import SessionAttendance
from .forms import CSVImportForm
from .utils import process_csv_import

def dashboard(request):
    """Admin statistics dashboard view"""

    # Redirect non-authenticated users to login
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    # Redirect non-staff users to client dashboard
    if not request.user.is_staff:
        return redirect('accounts:client_dashboard')
    
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


def import_csv(request):
    """CSV import view for manual file upload"""
    if not request.user.is_staff:
        return redirect('/admin/login/')
    
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            auto_assign_cards = form.cleaned_data['auto_assign_cards']
            
            try:
                print(f"DEBUG: Starting CSV import for file: {csv_file.name}")
                print(f"DEBUG: File size: {csv_file.size} bytes")
                
                # Read the file content to ensure it's valid
                csv_file.seek(0)
                content = csv_file.read()
                print(f"DEBUG: Content length: {len(content)} bytes")
                
                # Reset file pointer
                csv_file.seek(0)
                
                result = process_csv_import(csv_file, request.user.username if request.user.is_authenticated else 'admin', auto_assign_cards)
                
                print(f"DEBUG: Import result - Processed: {result['processed']}, Created: {result['created']}, Skipped: {result['skipped']}")
                
                if result['errors']:
                    messages.warning(request, f"Import voltooid met waarschuwingen. {result['created']} rijen toegevoegd, {result['skipped']} overgeslagen. Fouten: {len(result['errors'])}")
                else:
                    messages.success(request, f"Import succesvol! {result['created']} rijen toegevoegd, {result['skipped']} overgeslagen.")
                
                return redirect('admin:bookings_csvimport_changelist')
            except Exception as e:
                print(f"DEBUG: Import error: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"Fout tijdens import: {str(e)}")
    else:
        form = CSVImportForm()
    
    context = {
        'form': form,
        'title': 'CSV Importeren',
    }
    return render(request, 'admin/bookings/csvimport/import_form.html', context)