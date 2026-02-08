"""
Management command to create User accounts for existing Members
Run with: python manage.py create_user_accounts_for_members
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from members.models import Member
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Create User accounts for existing Members who don\'t have one yet'

    def add_arguments(self, parser):
        parser.add_argument(
            '--default-password',
            type=str,
            default='ChangeMe123!',
            help='Default password for new accounts (they should change it on first login)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating anything',
        )
        parser.add_argument(
            '--send-emails',
            action='store_true',
            help='Send email to users with their login credentials (requires email backend configured)',
        )

    def handle(self, *args, **options):
        default_password = options['default_password']
        dry_run = options['dry_run']
        send_emails = options['send_emails']

        # Get all members without user accounts
        members_without_accounts = Member.objects.filter(
            user_profile__isnull=True
        ).order_by('email')

        total_count = members_without_accounts.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✓ All members already have user accounts!'))
            return

        self.stdout.write(f'\nFound {total_count} member(s) without user accounts.')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))

        created_count = 0
        error_count = 0
        emails_sent = 0

        for member in members_without_accounts:
            try:
                if dry_run:
                    self.stdout.write(
                        f'Would create account for: {member.email} '
                        f'({member.first_name} {member.last_name})'
                    )
                    created_count += 1
                else:
                    with transaction.atomic():
                        # Check if user with this email already exists
                        if User.objects.filter(email=member.email).exists():
                            self.stdout.write(
                                self.style.WARNING(
                                    f'⚠ User with email {member.email} already exists, skipping...'
                                )
                            )
                            continue

                        # Create user
                        user = User.objects.create_user(
                            username=member.email,  # Use email as username
                            email=member.email,
                            first_name=member.first_name or '',
                            last_name=member.last_name or '',
                            password=default_password
                        )

                        # UserProfile should be created automatically by signal
                        # But let's verify it exists
                        if not hasattr(user, 'profile'):
                            self.stdout.write(
                                self.style.ERROR(
                                    f'✗ Failed to create profile for {member.email} - signal may not have fired'
                                )
                            )
                            user.delete()
                            error_count += 1
                            continue

                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Created account for: {member.email} '
                                f'({member.first_name} {member.last_name})'
                            )
                        )
                        created_count += 1

                        # Send email if requested
                        if send_emails:
                            try:
                                self.send_welcome_email(user, default_password)
                                emails_sent += 1
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'⚠ Failed to send email to {member.email}: {str(e)}'
                                    )
                                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Error creating account for {member.email}: {str(e)}'
                    )
                )
                error_count += 1

        # Summary
        self.stdout.write('\n' + '='*50)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'Would create {created_count} account(s)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Created {created_count} account(s)'))
            if error_count > 0:
                self.stdout.write(self.style.ERROR(f'✗ Failed to create {error_count} account(s)'))
            if send_emails:
                self.stdout.write(self.style.SUCCESS(f'📧 Sent {emails_sent} welcome email(s)'))

        if not dry_run and created_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠ IMPORTANT: All new users have password: {default_password}'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    '⚠ They should change it on first login!'
                )
            )
            if not send_emails:
                self.stdout.write(
                    self.style.WARNING(
                        '\n💡 TIP: Run with --send-emails to notify users automatically'
                    )
                )

    def send_welcome_email(self, user, password):
        """
        Send welcome email to new user with login credentials.
        Requires email backend to be configured in settings.
        """
        from django.core.mail import send_mail
        from django.conf import settings

        subject = 'Welkom bij Jump4Fun - Uw Account is Aangemaakt'
        
        message = f"""
Hallo {user.first_name or user.email},

Uw Jump4Fun account is aangemaakt!

Inloggegevens:
Email: {user.email}
Tijdelijk wachtwoord: {password}

Log in op: {settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'http://localhost:8000'}/accounts/login/

⚠ BELANGRIJK: Wijzig uw wachtwoord na het eerste inloggen!

Na het inloggen:
1. Vul uw profiel aan (voornaam, achternaam, telefoonnummer, schoenmaat, gewicht)
2. Bekijk beschikbare sessies
3. Boek uw eerste sessie!

Voor vragen, neem contact met ons op.

Met vriendelijke groet,
Het Jump4Fun Team
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
