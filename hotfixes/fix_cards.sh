#!/bin/bash

echo "🔧 Fix: Kaarten Koppelen & Afrekenen"
echo "====================================="
echo ""

COMPOSE_FILE="docker-compose.prod.ssl.yml"

echo "Deze script doet het volgende:"
echo "1. Koppelt actieve kaarten aan aanwezigheden zonder kaart"
echo "2. Rekent sessies af van gisteren die nog niet afgerekend zijn"
echo ""

read -p "Doorgaan? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Fix script
docker compose -f "$COMPOSE_FILE" exec -T web python manage.py shell << 'EOF'
from bookings.models import SessionAttendance
from cards.models import SessionCard
from datetime import datetime, timedelta
from django.utils import timezone
import pytz

brussels_tz = pytz.timezone('Europe/Brussels')
today = timezone.now().astimezone(brussels_tz).date()
yesterday = today - timedelta(days=14)

print(f"Vandaag: {today}")
print(f"Gisteren: {yesterday}\n")

# Step 1: Link cards to attendances without cards
print("=" * 60)
print("STAP 1: Kaarten koppelen aan aanwezigheden")
print("=" * 60)

no_card_attendances = SessionAttendance.objects.filter(
    session_date__date=yesterday,
    session_card__isnull=True
).select_related('member')

linked_count = 0

for attendance in no_card_attendances:
    # Get member's active cards
    active_cards = attendance.member.session_cards.filter(status='active')
    
    if active_cards.exists():
        # Assign first active card
        card = active_cards.first()
        attendance.session_card = card
        attendance.save()
        linked_count += 1
        print(f"✅ Gekoppeld: {attendance.member.full_name} → {card.card_type}")

print(f"\nTotaal gekoppeld: {linked_count}")

# Step 2: Charge sessions from yesterday
print("\n" + "=" * 60)
print("STAP 2: Sessies afrekenen")
print("=" * 60)

to_charge = SessionAttendance.objects.filter(
    session_date__date=yesterday,
    session_card__isnull=False,
    card_session_used=False
).select_related('session_card')

charged_count = 0

for attendance in to_charge:
    card = attendance.session_card
    
    # Check if card is valid
    if card.status == 'active' and card.sessions_remaining > 0:
        # Increment sessions used
        card.sessions_used += 1
        
        # Auto-update status if all sessions are now used
        if card.sessions_used >= card.total_sessions:
            card.status = 'completed'
        
        card.save()
        
        # Mark as charged
        attendance.card_session_used = True
        attendance.save()
        
        charged_count += 1
        trial_msg = " (🎓 OEFENBEURT)" if card.is_trial else ""
        print(f"✅ Afgerekend: {attendance.member.full_name} - {card.card_type}{trial_msg}")
        print(f"   Nu: {card.sessions_used}/{card.total_sessions} gebruikt, {card.sessions_remaining} over")
    else:
        print(f"⚠️  Kan niet afrekenen: {attendance.member.full_name}")
        print(f"   Kaart status: {card.status}, Sessies over: {card.sessions_remaining}")

print(f"\nTotaal afgerekend: {charged_count}")

print("\n" + "=" * 60)
print("✅ KLAAR!")
print("=" * 60)
EOF

echo ""
echo "====================================="
echo "Controleer nu in de admin:"
echo "1. Sessie Aanwezigheden van gisteren"
echo "2. Sessiekaarten - check de gebruikte sessies"
echo "====================================="
echo ""