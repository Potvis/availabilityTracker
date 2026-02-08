"""
Remove duplicate card_type CharField and card_category CharField from SessionCard.
The card_type_ref FK (added in 0003) becomes the sole card_type field.

Strategy:
1. Remove card_category CharField
2. Remove card_type CharField (the old free-text field)
3. Rename card_type_ref FK -> card_type
4. Data migration: fill NULLs with a default CardType
5. AlterField to make FK required (NOT NULL)
"""
import django.db.models.deletion
from django.db import migrations, models


def fill_null_card_types(apps, schema_editor):
    """Ensure every SessionCard has a card_type set.

    For rows where the old card_type_ref was NULL, create or look up a
    matching CardType based on the old total_sessions value.
    """
    CardType = apps.get_model('cards', 'CardType')
    SessionCard = apps.get_model('cards', 'SessionCard')

    null_cards = SessionCard.objects.filter(card_type__isnull=True)
    if not null_cards.exists():
        return

    # Build/reuse CardType records based on total_sessions
    for card in null_cards:
        sessions = card.total_sessions or 10
        ct, _ = CardType.objects.get_or_create(
            sessions=sessions,
            category='regular',
            defaults={
                'name': f'{sessions}-Sessie Kaart',
                'price': 0,
                'is_active': True,
                'sort_order': sessions,
            },
        )
        card.card_type_id = ct.pk
        card.save(update_fields=['card_type_id'])


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
        # Step 4: Fill NULL card_type values
        migrations.RunPython(
            fill_null_card_types,
            migrations.RunPython.noop,
        ),
        # Step 5: Make the FK required (not null) and update metadata
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
