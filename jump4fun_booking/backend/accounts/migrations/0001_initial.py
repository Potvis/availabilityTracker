# Generated migration for accounts app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('members', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weight', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text='Gewicht in kg (nodig voor apparatuurselectie)',
                    max_digits=5,
                    null=True,
                    validators=[
                        django.core.validators.MinValueValidator(30),
                        django.core.validators.MaxValueValidator(300)
                    ]
                )),
                ('profile_complete', models.BooleanField(default=False)),
                ('receive_notifications', models.BooleanField(default=True)),
                ('newsletter_subscription', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('member', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='user_profile',
                    to='members.member'
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Gebruikersprofiel',
                'verbose_name_plural': 'Gebruikersprofielen',
                'ordering': ['-created_at'],
            },
        ),
    ]
