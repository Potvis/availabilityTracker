from django.db import models
from django.core.validators import EmailValidator

class Member(models.Model):
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    shoe_size = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name', 'email']
        verbose_name = 'Lid'
        verbose_name_plural = 'Leden'

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.email})"
        return self.email

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email

    def total_sessions_attended(self):
        """Count total sessions attended by this member"""
        from sessions.models import SessionAttendance
        return SessionAttendance.objects.filter(member=self).count()

    def active_cards(self):
        """Get all active session cards for this member"""
        from cards.models import SessionCard
        return SessionCard.objects.filter(
            member=self,
            status='active'
        ).order_by('-purchased_date')