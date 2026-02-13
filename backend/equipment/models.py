from django.db import models


class SizeType(models.Model):
    """Admin-configurable shoe size categories for equipment."""
    name = models.CharField(max_length=50, unique=True, verbose_name='Naam',
                            help_text='Bijv. S, M, L, XL')
    description = models.TextField(blank=True, verbose_name='Beschrijving',
                                   help_text='Bijv. Small (32-36)')
    min_shoe_size = models.IntegerField(
        null=True, blank=True,
        verbose_name='Min schoenmaat',
        help_text='Kleinste schoenmaat voor deze categorie'
    )
    max_shoe_size = models.IntegerField(
        null=True, blank=True,
        verbose_name='Max schoenmaat',
        help_text='Grootste schoenmaat voor deze categorie'
    )
    is_active = models.BooleanField(default=True, verbose_name='Actief')

    class Meta:
        ordering = ['min_shoe_size', 'name']
        verbose_name = 'Schoenmaat'
        verbose_name_plural = 'Schoenmaten'

    def __str__(self):
        if self.min_shoe_size and self.max_shoe_size:
            return f"{self.name} ({self.min_shoe_size}-{self.max_shoe_size})"
        return self.name


class SpringType(models.Model):
    """Admin-configurable spring types for equipment."""
    name = models.CharField(max_length=50, unique=True, verbose_name='Naam')
    description = models.TextField(blank=True, verbose_name='Beschrijving')
    max_weight = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name='Max gewicht (kg)',
        help_text='Maximaal gewicht van een gebruiker voor dit type veer'
    )
    is_active = models.BooleanField(default=True, verbose_name='Actief')

    class Meta:
        ordering = ['name']
        verbose_name = 'Soort Veer'
        verbose_name_plural = 'Soorten Veren'

    def __str__(self):
        return self.name


class ShellType(models.Model):
    """Admin-configurable shell types for equipment."""
    name = models.CharField(max_length=50, unique=True, verbose_name='Naam')
    description = models.TextField(blank=True, verbose_name='Beschrijving')
    is_active = models.BooleanField(default=True, verbose_name='Actief')

    class Meta:
        ordering = ['name']
        verbose_name = 'Soort Schelp'
        verbose_name_plural = 'Soorten Schelpen'

    def __str__(self):
        return self.name


class EquipmentCategory(models.Model):
    """
    Admin-defined category for Kangoo Boots combinations.
    Each category represents a unique combination of size, spring type, and shell type.
    E.g. "Small groen" = Small + XR6 veren + L schelpen
    """
    name = models.CharField(
        max_length=100, unique=True, verbose_name='Naam',
        help_text='Bijv. Small groen, Medium oranje'
    )
    size_type = models.ForeignKey(
        SizeType, on_delete=models.CASCADE,
        verbose_name='Schoenmaat',
        help_text='Schoenmaat categorie voor deze groep'
    )
    spring_type = models.ForeignKey(
        SpringType, on_delete=models.CASCADE,
        verbose_name='Soort Veer',
        help_text='Type veer voor deze groep'
    )
    shell_type = models.ForeignKey(
        ShellType, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Soort Schelp',
        help_text='Type schelp voor deze groep (optioneel)'
    )
    is_active = models.BooleanField(default=True, verbose_name='Actief')

    class Meta:
        ordering = ['name']
        verbose_name = 'Kangoo Boot Categorie'
        verbose_name_plural = 'Kangoo Boot Categorieën'

    def __str__(self):
        return self.name


class Equipment(models.Model):
    STATUS_CHOICES = [
        ('available', 'Beschikbaar'),
        ('maintenance', 'Onderhoud'),
        ('broken', 'Defect'),
    ]

    # Size choices - actual ranges managed via Schoenmaten (SizeType)
    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
    ]

    name = models.CharField(max_length=100)
    equipment_id = models.CharField(max_length=50, unique=True, help_text="Unieke ID voor deze Kangoo Boot")
    size = models.CharField(max_length=5, choices=SIZE_CHOICES)
    size_type = models.ForeignKey(
        SizeType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Schoenmaat',
        help_text='Schoenmaat categorie (beheerd via Schoenmaten)'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    spring_type = models.ForeignKey(
        SpringType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Soort Veer',
        help_text='Type veer (beheerd via Soorten Veren)'
    )
    shell_type = models.ForeignKey(
        ShellType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Soort Schelp',
        help_text='Type schelp van de schoen'
    )
    category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Categorie',
        help_text='Kangoo Boot categorie (bijv. Small groen, Medium oranje)'
    )
    purchase_date = models.DateField(null=True, blank=True)
    last_maintenance = models.DateField(null=True, blank=True)
    next_maintenance = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['size', 'equipment_id']
        verbose_name = 'Kangoo Boot'
        verbose_name_plural = 'Kangoo Boots'

    def __str__(self):
        parts = [f"{self.name} ({self.equipment_id})", self.get_size_display()]
        if self.spring_type:
            parts.append(self.spring_type.name)
        if self.shell_type:
            parts.append(f"Schelp: {self.shell_type.name}")
        return ' - '.join(parts)

    @property
    def is_available(self):
        """Check if equipment is available for booking"""
        return self.status == 'available'

    @classmethod
    def get_available_count_by_size(cls):
        """Get count of available equipment per size"""
        from django.db.models import Count, Q
        return cls.objects.filter(status='available').values('size').annotate(count=Count('id'))


class MaintenanceLog(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenance_logs')
    date = models.DateField()
    description = models.TextField()
    performed_by = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Onderhoudslogboek'
        verbose_name_plural = 'Onderhoudslogboeken'

    def __str__(self):
        return f"{self.equipment.equipment_id} - {self.date}"