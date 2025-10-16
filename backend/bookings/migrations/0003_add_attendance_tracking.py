# Generated migration for session attendance changes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0002_sessionattendance_card_session_used'),
    ]

    operations = [
        migrations.AddField(
            model_name='sessionattendance',
            name='was_present',
            field=models.BooleanField(
                default=True,
                help_text='Was dit lid aanwezig bij de sessie?',
                verbose_name='Aanwezig'
            ),
        ),
    ]