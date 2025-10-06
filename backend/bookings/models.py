from django.db import models
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