from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0003_add_attendance_tracking'),
    ]

    operations = [
        # This migration doesn't change the database structure,
        # but marks the point where we removed automatic charging logic
        migrations.AlterField(
            model_name='sessionattendance',
            name='card_session_used',
            field=migrations.BooleanField(
                default=False,
                help_text='Sessie is afgerekend (handmatig door admin na ondertekening)'
            ),
        ),
    ]