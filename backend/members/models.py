from django.db import models
from django.core.validators import EmailValidator

class Member(models.Model):
    INSURANCE_STATUS_CHOICES = [
        ('none', 'Niet aangevraagd'),
        ('requested', 'Aangevraagd'),
        ('processing', 'In verwerking'),
        ('approved', 'In orde'),
        ('refused', 'Geweigerd (wil geen verzekering)'),
    ]

    email = models.EmailField(unique=True, validators=[EmailValidator()])
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(
        null=True, blank=True,
        verbose_name='Geboortedatum',
        help_text='Vereist voor verzekering'
    )
    shoe_size = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    insurance_status = models.CharField(
        max_length=20,
        choices=INSURANCE_STATUS_CHOICES,
        default='none',
        verbose_name='Verzekeringsstatus',
        help_text='Status van de verzekering voor dit lid'
    )
    # Admin override for boot category (takes priority over auto-calculation)
    override_category = models.ForeignKey(
        'equipment.EquipmentCategory',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Overschrijf schoen categorie',
        help_text='Handmatig ingestelde boot categorie (overschrijft automatische toewijzing)'
    )

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
        return self.attendances.count()

    def active_cards(self):
        """Get all active session cards for this member"""
        return self.session_cards.filter(
            status='active'
        ).order_by('-purchased_date')