from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0004_remove_equipment_spring_type_detail_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Bijv. Small groen, Medium oranje', max_length=100, unique=True, verbose_name='Naam')),
                ('is_active', models.BooleanField(default=True, verbose_name='Actief')),
                ('shell_type', models.ForeignKey(blank=True, help_text='Type schelp voor deze groep (optioneel)', null=True, on_delete=django.db.models.deletion.SET_NULL, to='equipment.shelltype', verbose_name='Soort Schelp')),
                ('size_type', models.ForeignKey(help_text='Schoenmaat categorie voor deze groep', on_delete=django.db.models.deletion.CASCADE, to='equipment.sizetype', verbose_name='Schoenmaat')),
                ('spring_type', models.ForeignKey(help_text='Type veer voor deze groep', on_delete=django.db.models.deletion.CASCADE, to='equipment.springtype', verbose_name='Soort Veer')),
            ],
            options={
                'verbose_name': 'Kangoo Boot Categorie',
                'verbose_name_plural': 'Kangoo Boot Categorieën',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='equipment',
            name='category',
            field=models.ForeignKey(blank=True, help_text='Kangoo Boot categorie (bijv. Small groen, Medium oranje)', null=True, on_delete=django.db.models.deletion.SET_NULL, to='equipment.equipmentcategory', verbose_name='Categorie'),
        ),
    ]
