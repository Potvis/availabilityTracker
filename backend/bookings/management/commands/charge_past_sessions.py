from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import SessionAttendance
from django.db.models import Q


class Command(BaseCommand):
    help = 'Charge session cards for past sessions that have not been charged yet'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be charged without actually charging',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        now = timezone.now()
        
        # Find all past sessions with cards linked but not yet charged
        past_uncharged = SessionAttendance.objects.filter(
            session_date__lt=now,  # Session is in the past
            session_card__isnull=False,  # Has a card linked
            card_session_used=False  # Not yet charged
        ).select_related('session_card', 'member')
        
        count = past_uncharged.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No sessions to charge'))
            return
        
        self.stdout.write(f'\n📋 Found {count} past session(s) to charge:')
        self.stdout.write('=' * 60)
        
        charged_count = 0
        skipped_count = 0
        
        for attendance in past_uncharged:
            card = attendance.session_card
            member = attendance.member
            
            trial_badge = "🎓 " if card.is_trial else ""
            
            # Check if card is valid
            if card.status == 'active' and card.sessions_remaining > 0:
                if dry_run:
                    self.stdout.write(
                        f'[DRY RUN] Would charge: {member.full_name} - '
                        f'{trial_badge}{card.card_type} '
                        f'({attendance.session_date.strftime("%d-%m-%Y %H:%M")})'
                    )
                else:
                    # Increment sessions used
                    card.sessions_used += 1
                    
                    # Auto-update status if all sessions are now used
                    if card.sessions_used >= card.total_sessions:
                        card.status = 'completed'
                    
                    card.save()
                    
                    # Mark as charged
                    attendance.card_session_used = True
                    attendance.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Charged: {member.full_name} - '
                            f'{trial_badge}{card.card_type} '
                            f'({card.sessions_remaining} remaining)'
                        )
                    )
                
                charged_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Skipped: {member.full_name} - '
                        f'{trial_badge}{card.card_type} '
                        f'(status: {card.status}, remaining: {card.sessions_remaining})'
                    )
                )
                skipped_count += 1
        
        self.stdout.write('=' * 60)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n🔍 DRY RUN - Would charge {charged_count} session(s), '
                    f'skip {skipped_count} session(s)'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Charged {charged_count} session(s), '
                    f'skipped {skipped_count} session(s)'
                )
            )