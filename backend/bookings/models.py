from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from members.models import Member
from cards.models import SessionCard

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
    
    # Tracking fields
    created_by = models.CharField(max_length=100, blank=True)
    modified_by = models.CharField(max_length=100, blank=True)
    import_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    # Card usage tracking
    card_session_used = models.BooleanField(
        default=False,
        help_text="Indicates if this session consumed a session from the card"
    )

    class Meta:
        ordering = ['-session_date']
        verbose_name = 'Sessie Aanwezigheid'
        verbose_name_plural = 'Sessie Aanwezigheden'
        unique_together = ['member', 'session_date', 'title']

    def __str__(self):
        return f"{self.member.full_name} - {self.title} ({self.session_date.strftime('%d-%m-%Y %H:%M')})"


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


# Signal handlers for automatic card usage tracking
@receiver(post_save, sender=SessionAttendance)
def use_card_session_on_save(sender, instance, created, **kwargs):
    """
    Automatically use a session from the card when attendance is linked to a card.
    This fires whenever a SessionAttendance is created or updated.
    """
    # Only process if there's a card linked and we haven't already used it
    if instance.session_card and not instance.card_session_used:
        try:
            card = instance.session_card
            
            # Check if card is valid (active and has sessions remaining)
            if card.status == 'active' and card.sessions_remaining > 0:
                # Increment sessions used
                card.sessions_used += 1
                
                # Auto-update status if all sessions are now used
                if card.sessions_used >= card.total_sessions:
                    card.status = 'completed'
                
                card.save()
                
                # Mark that we've consumed a session from this card
                # Use update() to avoid triggering the signal again
                SessionAttendance.objects.filter(pk=instance.pk).update(card_session_used=True)
                
                print(f"✓ Card session used: {card} (now {card.sessions_remaining} remaining)")
            else:
                print(f"⚠ Card {card} cannot be used (status: {card.status}, remaining: {card.sessions_remaining})")
                
        except Exception as e:
            print(f"❌ Error using card session: {e}")


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