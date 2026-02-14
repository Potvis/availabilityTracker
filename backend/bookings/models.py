from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone
from members.models import Member
from cards.models import SessionCard

SIZE_CATEGORY_CHOICES = [
    ('S', 'Small'),
    ('M', 'Medium'),
    ('L', 'Large'),
    ('XL', 'Extra Large'),
]


class SessionAttendance(models.Model):
    """Record of a member attending a session"""
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='attendances')
    session_card = models.ForeignKey(SessionCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='usages')

    # Session details from CSV
    session_date = models.DateTimeField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    capacity = models.IntegerField(null=True, blank=True)
    total_attendees = models.IntegerField(null=True, blank=True)
    waiting_list = models.IntegerField(default=0)

    # Size category for booking
    size_category = models.CharField(
        max_length=5,
        choices=SIZE_CATEGORY_CHOICES,
        blank=True,
        null=True,
        help_text="Schoenmaat categorie voor deze boeking"
    )
    
    # Tracking fields
    created_by = models.CharField(max_length=100, blank=True)
    modified_by = models.CharField(max_length=100, blank=True)
    import_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    # Card usage tracking - NOW MANUAL ONLY
    card_session_used = models.BooleanField(
        default=False,
        help_text="Sessie is afgerekend (handmatig door admin na ondertekening)"
    )
    
    # Attendance tracking for printing
    was_present = models.BooleanField(
        default=True,
        verbose_name='Aanwezig',
        help_text='Was dit lid aanwezig bij de sessie?'
    )

    class Meta:
        ordering = ['-session_date']
        verbose_name = 'Sessie Aanwezigheid'
        verbose_name_plural = 'Sessie Aanwezigheden'
        unique_together = ['member', 'session_date', 'title']

    def __str__(self):
        return f"{self.member.full_name} - {self.title} ({self.session_date.strftime('%d-%m-%Y %H:%M')})"
    
    @property
    def is_in_past(self):
        """Check if session date is in the past"""
        return self.session_date < timezone.now()


class CSVImport(models.Model):
    """Track CSV imports for audit purposes"""
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='csv_imports/')
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.CharField(max_length=100, blank=True)
    rows_processed = models.IntegerField(default=0)
    rows_created = models.IntegerField(default=0)
    rows_skipped = models.IntegerField(default=0)
    errors = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-imported_at']
        verbose_name = 'CSV Import'
        verbose_name_plural = 'CSV Imports'
    
    def __str__(self):
        return f"{self.filename} - {self.imported_at.strftime('%d-%m-%Y %H:%M')}"


# REMOVED: All automatic session charging signals
# Sessions are now only charged manually by admin after signature

@receiver(pre_delete, sender=SessionAttendance)
def return_card_session_on_delete(sender, instance, **kwargs):
    """
    Return a session to the card when attendance is deleted.
    This allows admin to correct mistakes by deleting incorrect attendances.
    """
    if instance.session_card and instance.card_session_used:
        try:
            card = instance.session_card
            
            # Decrement sessions used (can't go below 0)
            card.sessions_used = max(0, card.sessions_used - 1)
            
            # If card was marked completed but now has sessions, reactivate it
            if card.status == 'completed' and card.sessions_remaining > 0:
                card.status = 'active'
            
            card.save()
            print(f"✓ Card session returned: {card} (now {card.sessions_remaining} remaining)")
            
        except Exception as e:
            print(f"❌ Error returning card session: {e}")
# Import schedule models
from .schedule_models import SessionSchedule, SessionBooking
