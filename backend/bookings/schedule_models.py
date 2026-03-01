from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
import uuid

class SessionSchedule(models.Model):
    """
    Defines when sessions are available for booking.
    Admin creates these, and clients book SessionAttendance records against them.
    """
    WEEKDAY_CHOICES = [
        (0, 'Maandag'),
        (1, 'Dinsdag'),
        (2, 'Woensdag'),
        (3, 'Donderdag'),
        (4, 'Vrijdag'),
        (5, 'Zaterdag'),
        (6, 'Zondag'),
    ]

    # Session details
    title = models.CharField(max_length=200, default='Kangoo Jumping Sessie')
    description = models.TextField(blank=True)

    # Scheduling
    weekday = models.IntegerField(
        choices=WEEKDAY_CHOICES,
        help_text="Dag van de week"
    )
    start_time = models.TimeField(help_text="Starttijd van de sessie")
    duration_minutes = models.IntegerField(
        default=60,
        validators=[MinValueValidator(15), MaxValueValidator(180)],
        help_text="Duur van de sessie in minuten"
    )

    # Location
    location = models.CharField(max_length=200, default='Deinze Kouter 93')

    # Booking window
    booking_opens_days_before = models.IntegerField(
        default=14,
        validators=[MinValueValidator(1), MaxValueValidator(90)],
        help_text="Hoeveel dagen van tevoren kan men boeken"
    )
    booking_closes_hours_before = models.IntegerField(
        default=2,
        validators=[MinValueValidator(0), MaxValueValidator(48)],
        help_text="Hoeveel uur van tevoren sluit de boeking"
    )

    # Validity period
    start_date = models.DateField(
        help_text="Vanaf welke datum is deze sessie geldig"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Tot welke datum is deze sessie geldig (leeg = onbeperkt)"
    )

    # Capacity
    max_capacity = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        help_text="Maximaal aantal deelnemers (leeg = gebaseerd op beschikbare Kangoo Boots)"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Is deze sessie actief en boekbaar"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['weekday', 'start_time']
        verbose_name = 'Sessie Schema'
        verbose_name_plural = 'Sessie Schemas'

    def __str__(self):
        return f"{self.get_weekday_display()} {self.start_time.strftime('%H:%M')} - {self.title}"

    @property
    def total_capacity(self):
        """Get total capacity across all sizes based on available equipment"""
        from equipment.models import Equipment
        total = Equipment.objects.filter(status='available').count()
        if self.max_capacity is not None:
            return min(total, self.max_capacity)
        return total

    def get_capacity_for_category(self, category):
        """Get capacity for a specific equipment category."""
        if not category:
            return 0
        return category.get_matching_equipment().filter(
            status='available',
        ).count()

    def get_next_occurrence(self, from_date=None):
        """Get the next occurrence of this session schedule"""
        if from_date is None:
            from_date = timezone.now().date()

        # Find the next occurrence of this weekday on or after from_date
        days_ahead = self.weekday - from_date.weekday()
        if days_ahead < 0:  # Target day already happened this week
            days_ahead += 7

        next_date = from_date + timedelta(days=days_ahead)

        # If next_date is before start_date, find the first correct weekday
        # on or after start_date
        if next_date < self.start_date:
            days_ahead = self.weekday - self.start_date.weekday()
            if days_ahead < 0:
                days_ahead += 7
            next_date = self.start_date + timedelta(days=days_ahead)

        if self.end_date and next_date > self.end_date:
            return None

        # Combine date and time
        next_datetime = timezone.datetime.combine(
            next_date,
            self.start_time,
            tzinfo=timezone.get_current_timezone()
        )

        return next_datetime

    def is_booking_open(self, session_datetime):
        """Check if booking is currently open for a specific session occurrence"""
        now = timezone.now()

        # Check if session is in the future
        if session_datetime <= now:
            return False

        # Check if booking window has opened
        booking_opens = session_datetime - timedelta(days=self.booking_opens_days_before)
        if now < booking_opens:
            return False

        # Check if booking window has closed
        booking_closes = session_datetime - timedelta(hours=self.booking_closes_hours_before)
        if now > booking_closes:
            return False

        return True

    def get_available_capacity_for_category(self, session_datetime, category):
        """Get available capacity for a specific equipment category"""
        from bookings.models import SessionAttendance

        if not category:
            return 0

        # Get total capacity for this category
        total_capacity = self.get_capacity_for_category(category)

        # Count existing bookings for this specific date/time and category
        booked_count = SessionAttendance.objects.filter(
            session_date=session_datetime,
            title=self.title,
            equipment_category=category,
        ).count()

        available = max(0, total_capacity - booked_count)

        # Also respect max_capacity if set
        if self.max_capacity is not None:
            total_booked = SessionAttendance.objects.filter(
                session_date=session_datetime,
                title=self.title,
            ).count()
            total_remaining = max(0, self.max_capacity - total_booked)
            available = min(available, total_remaining)

        return available

    def get_available_capacity(self, session_datetime, category=None):
        """Get available capacity for a specific session occurrence"""
        if category:
            return self.get_available_capacity_for_category(session_datetime, category)

        # Return total available across all categories
        from bookings.models import SessionAttendance
        from equipment.models import EquipmentCategory

        total_available = 0
        categories = EquipmentCategory.objects.filter(is_active=True)
        for cat in categories:
            equipment_count = cat.get_matching_equipment().filter(
                status='available',
            ).count()
            booked = SessionAttendance.objects.filter(
                session_date=session_datetime,
                title=self.title,
                equipment_category=cat,
            ).count()
            total_available += max(0, equipment_count - booked)

        if self.max_capacity is not None:
            total_booked = SessionAttendance.objects.filter(
                session_date=session_datetime,
                title=self.title,
            ).count()
            total_remaining = max(0, self.max_capacity - total_booked)
            total_available = min(total_available, total_remaining)

        return total_available

    def can_book(self, session_datetime, category=None):
        """Check if a session can be booked"""
        return (
            self.is_active and
            self.is_booking_open(session_datetime) and
            self.get_available_capacity(session_datetime, category) > 0
        )

    def has_capacity_for_category(self, category):
        """Check if there is available equipment for this category."""
        if not category:
            return False
        return category.get_matching_equipment().filter(
            status='available',
        ).exists()

    @staticmethod
    def get_equipment_capacities():
        """Get available equipment count per category"""
        from equipment.models import Equipment, EquipmentCategory
        from django.db.models import Count

        counts = Equipment.objects.filter(
            status='available',
            category__isnull=False,
        ).values('category__id', 'category__name').annotate(
            count=Count('id')
        )
        result = {}
        for item in counts:
            result[item['category__name']] = item['count']
        return result


class SessionBooking(models.Model):
    """
    Represents a client's booking for a specific session occurrence.
    This links to both the schedule and creates a SessionAttendance.
    """
    schedule = models.ForeignKey(
        SessionSchedule, 
        on_delete=models.CASCADE, 
        related_name='bookings'
    )
    session_datetime = models.DateTimeField(
        help_text="De specifieke datum en tijd van deze sessie"
    )
    
    # Link to existing SessionAttendance
    attendance = models.OneToOneField(
        'bookings.SessionAttendance',
        on_delete=models.CASCADE,
        related_name='booking'
    )
    
    # Booking details
    booked_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-session_datetime']
        verbose_name = 'Sessie Boeking'
        verbose_name_plural = 'Sessie Boekingen'
    
    def __str__(self):
        return f"{self.attendance.member.full_name} - {self.schedule.title} op {self.session_datetime.strftime('%d-%m-%Y %H:%M')}"
    
    @property
    def is_cancelled(self):
        return self.cancelled_at is not None
    
    def cancel(self, reason=''):
        """Cancel this booking"""
        if not self.is_cancelled:
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.save()

class Company(models.Model):
    """
    A company that can have multiple business events.
    Each company gets one shareable link; users pick from available events.
    """
    name = models.CharField(max_length=200, verbose_name='Bedrijfsnaam')
    contact_email = models.EmailField(blank=True, verbose_name='Contact E-mail')
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name='Contact Telefoon')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    allow_multiple_bookings = models.BooleanField(
        default=False,
        verbose_name='Meerdere inschrijvingen toestaan',
        help_text='Als aangevinkt mogen gebruikers zich voor meerdere events van dit bedrijf inschrijven'
    )
    notes = models.TextField(blank=True, verbose_name='Opmerkingen')
    is_active = models.BooleanField(default=True, verbose_name='Actief')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Bedrijf'
        verbose_name_plural = 'Bedrijven'

    def __str__(self):
        return self.name

    def get_active_events(self):
        return self.events.filter(is_active=True, event_datetime__gt=timezone.now()).order_by('event_datetime')


class BusinessEvent(models.Model):
    """
    A private/business event session with a unique shareable link.
    Guests can book via the link without needing an account.
    Can belong to a company for multi-event support.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name='Bedrijf',
        help_text='Optioneel: koppel aan een bedrijf voor meerdere events onder één link'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, default='Deinze Kouter 93')

    event_datetime = models.DateTimeField(help_text="Datum en tijd van het evenement")
    duration_minutes = models.IntegerField(
        default=60,
        validators=[MinValueValidator(15), MaxValueValidator(180)],
        help_text="Duur in minuten"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    max_capacity = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        help_text="Maximaal aantal deelnemers (leeg = gebaseerd op beschikbare Kangoo Boots)"
    )

    is_active = models.BooleanField(default=True, help_text="Is dit evenement nog open voor boekingen")

    created_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-event_datetime']
        verbose_name = 'Bedrijfsevenement'
        verbose_name_plural = 'Bedrijfsevenementen'

    def __str__(self):
        prefix = f"{self.company.name} - " if self.company else ""
        local_dt = timezone.localtime(self.event_datetime)
        return f"{prefix}{self.title} - {local_dt.strftime('%d-%m-%Y %H:%M')}"
 
    @property
    def is_in_future(self):
        return self.event_datetime > timezone.now()

    @property
    def bookings_count(self):
        return self.event_bookings.count()

    def get_equipment_capacity_for_category(self, category):
        """Get capacity for a specific equipment category based on available equipment."""
        if not category:
            return 0
        return category.get_matching_equipment().filter(
            status='available',
        ).count()

    def get_booked_count_for_category(self, category):
        """Get number of bookings for a specific equipment category."""
        if not category:
            return 0
        return self.event_bookings.filter(equipment_category=category).count()

    def get_available_spots_for_category(self, category):
        """Get available spots for a specific equipment category."""
        equipment_count = self.get_equipment_capacity_for_category(category)
        booked_count = self.get_booked_count_for_category(category)
        available = max(0, equipment_count - booked_count)
        if self.max_capacity is not None:
            total_remaining = max(0, self.max_capacity - self.bookings_count)
            return min(available, total_remaining)
        return available

    def get_available_spots(self):
        """Get total available spots across all categories, based on equipment."""
        from equipment.models import EquipmentCategory

        total_available = sum(
            self.get_available_spots_for_category(cat)
            for cat in EquipmentCategory.objects.filter(is_active=True)
        )

        if self.max_capacity is not None:
            total_remaining = max(0, self.max_capacity - self.bookings_count)
            return min(total_available, total_remaining)
        return total_available

    def can_book(self):
        """Check if the event can accept any more bookings."""
        return self.is_active and self.is_in_future and self.get_available_spots() > 0

    def can_book_for_category(self, category):
        """Check if the event can accept a booking for a specific category."""
        return self.is_active and self.is_in_future and self.get_available_spots_for_category(category) > 0
 
 
class BusinessEventBooking(models.Model):
    """
    A booking for a business event. Stores guest info directly so
    guests can book without creating an account.
    """
    event = models.ForeignKey(
        BusinessEvent,
        on_delete=models.CASCADE,
        related_name='event_bookings'
    )
 
    # Guest info (always stored here)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    shoe_size = models.CharField(max_length=10)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
 
    equipment_category = models.ForeignKey(
        'equipment.EquipmentCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Boot Categorie',
        help_text='Boot categorie voor deze boeking'
    )
 
    # Optional link to member (if guest opted in for account creation)
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='business_event_bookings'
    )
 
    booked_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-booked_at']
        verbose_name = 'Evenement Boeking'
        verbose_name_plural = 'Evenement Boekingen'
 
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.event.title}"
 
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"