"""
Remove duplicate spring_type CharField from Equipment.
The spring_type_detail FK (added in 0003) becomes the sole spring_type field.

Strategy:
1. Remove the old spring_type CharField
2. Rename spring_type_detail FK -> spring_type
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0003_shelltype_springtype_alter_equipment_spring_type_and_more"),
    ]

    operations = [
        # Step 1: Remove the old spring_type CharField
        migrations.RemoveField(
            model_name="equipment",
            name="spring_type",
        ),
        # Step 2: Rename spring_type_detail FK -> spring_type
        migrations.RenameField(
            model_name="equipment",
            old_name="spring_type_detail",
            new_name="spring_type",
        ),
        # Step 3: Update field metadata
        migrations.AlterField(
            model_name="equipment",
            name="spring_type",
            field=models.ForeignKey(
                blank=True,
                help_text="Type veer (beheerd via Soorten Veren)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="equipment.springtype",
                verbose_name="Soort Veer",
            ),
        ),
    ]
