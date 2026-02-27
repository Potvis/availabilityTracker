# Generated migration for boot category assignment

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0005_equipmentcategory_equipment_category"),
        ("members", "0002_member_date_of_birth_member_insurance_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="override_category",
            field=models.ForeignKey(
                blank=True,
                help_text="Handmatig ingestelde boot categorie (overschrijft automatische toewijzing)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="equipment.equipmentcategory",
                verbose_name="Overschrijf schoen categorie",
            ),
        ),
    ]
