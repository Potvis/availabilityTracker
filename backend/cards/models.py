from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from members.models import Member


class CardType(models.Model):
    """Admin-configurable card types with pricing."""
    name = models.CharField(max_length=100, verbose_name='Naam', help_text='Bijv. 1 Beurt, 5 Beurten, 10 Beurten')
    sessions = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Aantal Beurten',
        help_text='Hoeveel beurten zitten er in deze kaart'
    )
    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name='Prijs',
        help_text='Prijs in euro'
    )
    category = models.CharField(
        max_length=20,
        choices=[('regular', 'Normale Kaart'), ('trial', 'Oefenbeurt')],
        default='regular',
        verbose_name='Categorie'
    )
    is_active = models.BooleanField(default=True, verbose_name='Actief')
    sort_order = models.IntegerField(default=0, verbose_name='Sorteervolgorde')

    class Meta:
        ordering = ['sort_order', 'sessions']
        verbose_name = 'Kaartsoort'
        verbose_name_plural = 'Kaartsoorten'

    def __str__(self):
        return f"{self.name} ({self.sessions} beurten - {self.price} EUR)"


class SessionCard(models.Model):
    STATUS_CHOICES = [
        ('active', 'Actief'),
        ('expired', 'Verlopen'),
        ('completed', 'Volledig Gebruikt'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='session_cards')
    card_type = models.CharField(max_length=50, default='10-Sessie Kaart')
    card_type_ref = models.ForeignKey(
        CardType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Kaartsoort',
        help_text='Verwijzing naar de kaartsoort (optioneel)'
    )
    card_category = models.CharField(
        max_length=20, 
        choices=[('regular', 'Normale Kaart'), ('trial', 'Oefenbeurt')],
        default='regular',
        verbose_name='Kaart Categorie'
    )
    total_sessions = models.IntegerField(default=10, validators=[MinValueValidator(1)])
    sessions_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    purchased_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    price_paid = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-purchased_date']
        verbose_name = 'Sessiekaart'
        verbose_name_plural = 'Sessiekaarten'

    def __str__(self):
        category = "🎓 " if self.card_category == 'trial' else ""
        return f"{category}{self.member.full_name} - {self.card_type} ({self.sessions_remaining}/{self.total_sessions})"

    @property
    def sessions_remaining(self):
        return max(0, self.total_sessions - self.sessions_used)

    @property
    def is_valid(self):
        """Check if card is still valid and has sessions remaining"""
        return self.status == 'active' and self.sessions_remaining > 0

    @property
    def is_trial(self):
        """Check if this is a trial card"""
        return self.card_category == 'trial'

    def use_session(self):
        """Use one session from the card"""
        if not self.is_valid:
            raise ValueError("Kaart is niet meer geldig")
        
        self.sessions_used += 1
        if self.sessions_remaining == 0:
            self.status = 'completed'
        self.save()

    def save(self, *args, **kwargs):
        # Auto-update status based on sessions
        if self.sessions_used >= self.total_sessions:
            self.status = 'completed'
        super().save(*args, **kwargs)