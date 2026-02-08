from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='wants_insurance',
            field=models.BooleanField(
                default=False,
                verbose_name='Wil Verzekering',
                help_text='Lid wil een verzekering afsluiten'
            ),
        ),
        migrations.AddField(
            model_name='member',
            name='insurance_status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('none', 'Geen Verzekering'),
                    ('requested', 'Aangevraagd (Contact Nodig)'),
                    ('pending', 'In Afwachting van Bevestiging'),
                    ('insured', 'Verzekerd'),
                ],
                default='none',
                verbose_name='Verzekering Status'
            ),
        ),
    ]