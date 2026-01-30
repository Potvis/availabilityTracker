"""
Remove duplicate card_type CharField and card_category CharField from SessionCard.
The card_type_ref FK (added in 0003) becomes the sole card_type field.

Strategy:
1. Remove card_category CharField
2. Remove card_type CharField (the old free-text field)
3. Rename card_type_ref FK -> card_type
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0003_cardtype_sessioncard_card_type_ref"),
    ]

    operations = [
        # Step 1: Remove the old card_category CharField
        migrations.RemoveField(
            model_name="sessioncard",
            name="card_category",
        ),
        # Step 2: Remove the old card_type CharField (free text)
        migrations.RemoveField(
            model_name="sessioncard",
            name="card_type",
        ),
        # Step 3: Rename card_type_ref FK -> card_type
        migrations.RenameField(
            model_name="sessioncard",
            old_name="card_type_ref",
            new_name="card_type",
        ),
        # Step 4: Make the FK required (not null) and update metadata
        migrations.AlterField(
            model_name="sessioncard",
            name="card_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="session_cards",
                to="cards.cardtype",
                verbose_name="Kaartsoort",
            ),
        ),
    ]
