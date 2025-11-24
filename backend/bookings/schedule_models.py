from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta


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
    
    SIZE_CATEGORY_CHOICES = [
        ('S', 'Small (32-36)'),
        ('M', 'Medium (37-41)'),
        ('L', 'Large (42-46)'),
        ('XL', 'Extra Large (47+)'),
    ]
    
    # Session details
    title = models.CharField(max_length=200, default='Kangoo Jumping Sessie')
    description = models.TextField(blank=True)
    
    # Size category this session is for
    size_category = models.CharField(
        max_length=5, 
        choices=SIZE_CATEGORY_CHOICES,
        help_text="Schoenmaat categorie voor deze sessie"
    )
    
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
    
    # Capacity
    max_capacity = models.IntegerField(
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Maximum aantal deelnemers"
    )
    
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
        return f"{self.get_weekday_display()} {self.start_time.strftime('%H:%M')} - {self.title} (Maat {self.size_category})"
    
    def get_next_occurrence(self, from_date=None):
        """Get the next occurrence of this session schedule"""
        if from_date is None:
            from_date = timezone.now().date()
        
        # Find the next occurrence of this weekday
        days_ahead = self.weekday - from_date.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        next_date = from_date + timedelta(days=days_ahead)
        
        # Check if it's within validity period
        if next_date < self.start_date:
            next_date = self.start_date
        
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
    
    def get_available_capacity(self, session_datetime):
        """Get available capacity for a specific session occurrence"""
        from bookings.models import SessionAttendance
        
        # Count existing bookings for this specific date/time
        booked_count = SessionAttendance.objects.filter(
            session_date=session_datetime,
            title=self.title
        ).count()
        
        return max(0, self.max_capacity - booked_count)
    
    def can_book(self, session_datetime):
        """Check if a session can be booked"""
        return (
            self.is_active and
            self.is_booking_open(session_datetime) and
            self.get_available_capacity(session_datetime) > 0
        )


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
