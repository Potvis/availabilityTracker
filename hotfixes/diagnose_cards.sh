#!/bin/bash

echo "🔍 Diagnose: Kaarten Koppeling & Afrekening"
echo "==========================================="
echo ""

COMPOSE_FILE="docker-compose.prod.ssl.yml"

# Check yesterday's session
echo "1️⃣ Checking gisteren's sessie (1 december 2025)..."
docker compose -f "$COMPOSE_FILE" exec -T web python manage.py shell << 'EOF'
from bookings.models import SessionAttendance
from django.utils import timezone
from datetime import datetime, timedelta
import pytz

# Get yesterday's date
brussels_tz = pytz.timezone('Europe/Brussels')
today = timezone.now().astimezone(brussels_tz).date()
yesterday = today - timedelta(days=7)

print(f"\nVandaag: {today}")
print(f"Gisteren: {yesterday}")
print(f"\n{'='*60}")

# Find attendances from yesterday
attendances = SessionAttendance.objects.filter(
    session_date__date=yesterday
).select_related('member', 'session_card')

print(f"\nAantal aanwezigheden van gisteren: {attendances.count()}")
print(f"\n{'='*60}\n")

for attendance in attendances:
    member = attendance.member
    card = attendance.session_card
    
    print(f"Lid: {member.full_name}")
    print(f"  Email: {member.email}")
    print(f"  Gekoppelde kaart: {card.card_type if card else 'GEEN KAART'}")
    
    if card:
        print(f"  Kaart status: {card.status}")
        print(f"  Sessies gebruikt: {card.sessions_used}/{card.total_sessions}")
        print(f"  Sessie afgerekend: {'JA' if attendance.card_session_used else 'NEE'}")
        print(f"  Is trial: {'JA' if card.is_trial else 'NEE'}")
    
    # Check if member has other active cards
    active_cards = member.session_cards.filter(status='active')
    if active_cards.exists() and not card:
        print(f"  ⚠️  LID HEEFT WEL ACTIEVE KAARTEN:")
        for ac in active_cards:
            print(f"      - {ac.card_type}: {ac.sessions_remaining} sessies over")
    
    print()

print(f"{'='*60}\n")
EOF

echo ""
echo "2️⃣ Checking voor kaarten zonder afrekening..."
docker compose -f "$COMPOSE_FILE" exec -T web python manage.py shell << 'EOF'
from bookings.models import SessionAttendance
from datetime import datetime, timedelta
from django.utils import timezone
import pytz

brussels_tz = pytz.timezone('Europe/Brussels')
today = timezone.now().astimezone(brussels_tz).date()
yesterday = today - timedelta(days=7)

# Find attendances with cards but not charged
not_charged = SessionAttendance.objects.filter(
    session_date__date=yesterday,
    session_card__isnull=False,
    card_session_used=False
).select_related('member', 'session_card')

print(f"\nAantal met kaart maar NIET afgerekend: {not_charged.count()}")

if not_charged.exists():
    print("\nDetails:")
    for att in not_charged:
        print(f"  - {att.member.full_name}: {att.session_card.card_type}")
        print(f"    Sessie datum: {att.session_date}")
        print(f"    Is in verleden: {att.is_in_past}")
        print()

# Find attendances without cards where member HAS active cards
no_card_but_has = SessionAttendance.objects.filter(
    session_date__date=yesterday,
    session_card__isnull=True
).select_related('member')

print(f"\nAantal ZONDER kaart gekoppeld: {no_card_but_has.count()}")

has_active = 0
for att in no_card_but_has:
    active_cards = att.member.session_cards.filter(status='active')
    if active_cards.exists():
        has_active += 1
        print(f"\n⚠️  {att.member.full_name} heeft WEL actieve kaart(en):")
        for card in active_cards:
            print(f"     - {card.card_type}: {card.sessions_remaining} over")

print(f"\n{'='*60}")
print(f"Totaal met actieve kaarten maar niet gekoppeld: {has_active}")
print(f"{'='*60}\n")
EOF

echo ""
echo "==========================================="
echo "✅ Diagnose voltooid"
echo ""