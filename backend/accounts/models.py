from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from members.models import Member


class UserProfile(models.Model):
    """Extended user profile linked to Member model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name='user_profile')
    
    # Additional profile fields
    weight = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(30), MaxValueValidator(300)],
        help_text="Gewicht in kg (nodig voor selectie Kangoo Boots)"
    )
    
    # Profile completion tracking
    profile_complete = models.BooleanField(default=False)
    
    # Preferences
    receive_notifications = models.BooleanField(default=True)
    newsletter_subscription = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Gebruikersprofiel'
        verbose_name_plural = 'Gebruikersprofielen'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.member.email}"
    
    def check_profile_complete(self):
        """Check if all required profile fields are filled in"""
        required_fields = [
            self.member.first_name,
            self.member.last_name,
            self.member.date_of_birth,
            self.member.shoe_size,
            self.member.phone,
            self.weight,
        ]
        
        is_complete = all(field for field in required_fields)
        
        # Update profile_complete flag if changed
        if is_complete != self.profile_complete:
            self.profile_complete = is_complete
            self.save(update_fields=['profile_complete'])
        
        return is_complete
    
    @property
    def missing_fields(self):
        """Get list of missing required fields"""
        missing = []
        
        if not self.member.first_name:
            missing.append('Voornaam')
        if not self.member.last_name:
            missing.append('Achternaam')
        if not self.member.date_of_birth:
            missing.append('Geboortedatum')
        if not self.member.shoe_size:
            missing.append('Schoenmaat')
        if not self.member.phone:
            missing.append('Telefoonnummer')
        if not self.weight:
            missing.append('Gewicht')
        
        return missing
