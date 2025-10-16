# Generated migration for session card changes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sessioncard',
            name='card_category',
            field=models.CharField(
                choices=[('regular', 'Normale Kaart'), ('trial', 'Oefenbeurt')],
                default='regular',
                max_length=20,
                verbose_name='Kaart Categorie'
            ),
        ),
    ]