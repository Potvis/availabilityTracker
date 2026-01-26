from django.core.management.base import BaseCommand
from equipment.models import Equipment
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Create sample equipment data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing equipment before creating new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            deleted_count = Equipment.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} existing equipment items'))

        # Define equipment distribution per size
        # Realistic distribution: more medium sizes, fewer XL
        equipment_config = [
            # Size S (32-36)
            {'size': 'S', 'count': 4, 'prefix': 'KJ-S'},
            # Size M (37-41)
            {'size': 'M', 'count': 6, 'prefix': 'KJ-M'},
            # Size L (42-46)
            {'size': 'L', 'count': 5, 'prefix': 'KJ-L'},
            # Size XL (47+)
            {'size': 'XL', 'count': 3, 'prefix': 'KJ-XL'},
        ]

        created_count = 0
        today = date.today()

        for config in equipment_config:
            size = config['size']
            count = config['count']
            prefix = config['prefix']

            for i in range(1, count + 1):
                equipment_id = f"{prefix}-{i:03d}"

                # Check if already exists
                if Equipment.objects.filter(equipment_id=equipment_id).exists():
                    self.stdout.write(f'  Skipping {equipment_id} (already exists)')
                    continue

                # Random purchase date (1-3 years ago)
                days_ago = random.randint(365, 365 * 3)
                purchase_date = today - timedelta(days=days_ago)

                # Random last maintenance (1-6 months ago)
                last_maintenance = today - timedelta(days=random.randint(30, 180))

                # Next maintenance (3-6 months from last)
                next_maintenance = last_maintenance + timedelta(days=random.randint(90, 180))

                # Most are available, some in maintenance or broken
                status_choices = ['available'] * 8 + ['maintenance'] + ['broken']
                status = random.choice(status_choices)

                # Spring type - standard mostly, some HD for heavier users
                spring_type = 'hd' if size in ['L', 'XL'] and random.random() > 0.6 else 'standard'

                Equipment.objects.create(
                    name=f"Kangoo Jumps {size}",
                    equipment_id=equipment_id,
                    size=size,
                    status=status,
                    spring_type=spring_type,
                    purchase_date=purchase_date,
                    last_maintenance=last_maintenance,
                    next_maintenance=next_maintenance,
                    notes=f"Kangoo Jumps schoenen maat {size}" + (
                        " - HD veren voor zwaardere gebruikers" if spring_type == 'hd' else ""
                    )
                )
                created_count += 1
                status_icon = '✓' if status == 'available' else ('⚠' if status == 'maintenance' else '✗')
                self.stdout.write(f'  {status_icon} Created {equipment_id} ({size}, {spring_type}, {status})')

        self.stdout.write(self.style.SUCCESS(f'\nCreated {created_count} equipment items'))

        # Show summary
        self.stdout.write('\nEquipment Summary:')
        for size_choice in ['S', 'M', 'L', 'XL']:
            total = Equipment.objects.filter(size=size_choice).count()
            available = Equipment.objects.filter(size=size_choice, status='available').count()
            self.stdout.write(f'  {size_choice}: {available}/{total} available')
