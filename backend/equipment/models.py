from django.db import models

class Equipment(models.Model):
    STATUS_CHOICES = [
        ('available', 'Beschikbaar'),
        ('in_use', 'In Gebruik'),
        ('maintenance', 'Onderhoud'),
        ('broken', 'Defect'),
    ]

    SIZE_CHOICES = [
        ('S', 'Small (32-36)'),
        ('M', 'Medium (37-41)'),
        ('L', 'Large (42-46)'),
        ('XL', 'Extra Large (47+)'),
    ]

    name = models.CharField(max_length=100)
    equipment_id = models.CharField(max_length=50, unique=True, help_text="Unieke ID voor dit stuk apparatuur")
    size = models.CharField(max_length=5, choices=SIZE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    purchase_date = models.DateField(null=True, blank=True)
    last_maintenance = models.DateField(null=True, blank=True)
    next_maintenance = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['size', 'equipment_id']
        verbose_name = 'Apparatuur'
        verbose_name_plural = 'Apparatuur'

    def __str__(self):
        return f"{self.name} ({self.equipment_id}) - {self.get_size_display()}"

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