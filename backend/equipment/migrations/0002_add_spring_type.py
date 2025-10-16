# Generated migration for equipment changes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0001_initial'),
    ]

    operations = [
        # Add spring_type field
        migrations.AddField(
            model_name='equipment',
            name='spring_type',
            field=models.CharField(
                choices=[('standard', 'Standaard'), ('hd', 'HD')],
                default='standard',
                max_length=20,
                verbose_name='Soort Veer'
            ),
        ),
        
        # Remove 'in_use' from status choices by updating all in_use to available
        migrations.RunSQL(
            sql="UPDATE equipment_equipment SET status = 'available' WHERE status = 'in_use';",
            reverse_sql="",  # No reverse needed
        ),
        
        # Update the status field choices (Django will handle this in model)
        migrations.AlterField(
            model_name='equipment',
            name='status',
            field=models.CharField(
                choices=[
                    ('available', 'Beschikbaar'),
                    ('maintenance', 'Onderhoud'),
                    ('broken', 'Defect')
                ],
                default='available',
                max_length=20
            ),
        ),
    ]