# Generated migration for session schedules

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0003_add_attendance_tracking'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='Kangoo Jumping Sessie', max_length=200)),
                ('description', models.TextField(blank=True)),
                ('size_category', models.CharField(
                    choices=[('S', 'Small (32-36)'), ('M', 'Medium (37-41)'), ('L', 'Large (42-46)'), ('XL', 'Extra Large (47+)')],
                    help_text='Schoenmaat categorie voor deze sessie',
                    max_length=5
                )),
                ('weekday', models.IntegerField(
                    choices=[(0, 'Maandag'), (1, 'Dinsdag'), (2, 'Woensdag'), (3, 'Donderdag'), (4, 'Vrijdag'), (5, 'Zaterdag'), (6, 'Zondag')],
                    help_text='Dag van de week'
                )),
                ('start_time', models.TimeField(help_text='Starttijd van de sessie')),
                ('duration_minutes', models.IntegerField(
                    default=60,
                    help_text='Duur van de sessie in minuten',
                    validators=[django.core.validators.MinValueValidator(15), django.core.validators.MaxValueValidator(180)]
                )),
                ('location', models.CharField(default='Deinze Kouter 93', max_length=200)),
                ('max_capacity', models.IntegerField(
                    default=15,
                    help_text='Maximum aantal deelnemers',
                    validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(50)]
                )),
                ('booking_opens_days_before', models.IntegerField(
                    default=14,
                    help_text='Hoeveel dagen van tevoren kan men boeken',
                    validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(90)]
                )),
                ('booking_closes_hours_before', models.IntegerField(
                    default=2,
                    help_text='Hoeveel uur van tevoren sluit de boeking',
                    validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(48)]
                )),
                ('start_date', models.DateField(help_text='Vanaf welke datum is deze sessie geldig')),
                ('end_date', models.DateField(
                    blank=True,
                    help_text='Tot welke datum is deze sessie geldig (leeg = onbeperkt)',
                    null=True
                )),
                ('is_active', models.BooleanField(default=True, help_text='Is deze sessie actief en boekbaar')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.CharField(blank=True, max_length=100)),
            ],
            options={
                'verbose_name': 'Sessie Schema',
                'verbose_name_plural': 'Sessie Schemas',
                'ordering': ['weekday', 'start_time'],
            },
        ),
        migrations.CreateModel(
            name='SessionBooking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_datetime', models.DateTimeField(help_text='De specifieke datum en tijd van deze sessie')),
                ('booked_at', models.DateTimeField(auto_now_add=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('cancellation_reason', models.TextField(blank=True)),
                ('attendance', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='booking',
                    to='bookings.sessionattendance'
                )),
                ('schedule', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='bookings',
                    to='bookings.sessionschedule'
                )),
            ],
            options={
                'verbose_name': 'Sessie Boeking',
                'verbose_name_plural': 'Sessie Boekingen',
                'ordering': ['-session_datetime'],
            },
        ),
    ]
