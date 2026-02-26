# Generated migration for boot category assignment

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0005_equipmentcategory_equipment_category"),
        ("bookings", "0009_merge_0004_remove_automatic_charging_0008_company"),
    ]

    operations = [
        # SessionAttendance: remove size_category, add equipment_category FK
        migrations.RemoveField(
            model_name="sessionattendance",
            name="size_category",
        ),
        migrations.AddField(
            model_name="sessionattendance",
            name="equipment_category",
            field=models.ForeignKey(
                blank=True,
                help_text="Kangoo Boot categorie voor deze boeking",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="equipment.equipmentcategory",
                verbose_name="Boot Categorie",
            ),
        ),
        # BusinessEventBooking: remove size_category, add equipment_category FK
        migrations.RemoveField(
            model_name="businesseventbooking",
            name="size_category",
        ),
        migrations.AddField(
            model_name="businesseventbooking",
            name="equipment_category",
            field=models.ForeignKey(
                blank=True,
                help_text="Kangoo Boot categorie voor deze boeking",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="equipment.equipmentcategory",
                verbose_name="Boot Categorie",
            ),
        ),
    ]
