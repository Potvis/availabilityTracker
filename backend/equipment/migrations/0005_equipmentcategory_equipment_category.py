"""
Migration to:
1. Register existing SizeType model in Django migration state (table already exists in DB)
2. Register existing Equipment.size_type FK in Django migration state (column already exists in DB)
3. Register existing SpringType.max_weight field in Django migration state (column already exists in DB)
4. Create new EquipmentCategory model
5. Add new Equipment.category FK

Uses SeparateDatabaseAndState for steps 1-3 because these objects exist in the
database but were never tracked in migrations. Uses CREATE TABLE IF NOT EXISTS
and conditional ALTER TABLE so it also works on a fresh database.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0004_remove_equipment_spring_type_detail_and_more'),
    ]

    operations = [
        # Step 1: Register SizeType in Django's migration state.
        # The table already exists in the database (was created via manual migrate).
        # Use CREATE TABLE IF NOT EXISTS so it also works on a fresh DB.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='SizeType',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(help_text='Bijv. S, M, L, XL', max_length=50, unique=True, verbose_name='Naam')),
                        ('description', models.TextField(blank=True, help_text='Bijv. Small (32-36)', verbose_name='Beschrijving')),
                        ('min_shoe_size', models.IntegerField(blank=True, help_text='Kleinste schoenmaat voor deze categorie', null=True, verbose_name='Min schoenmaat')),
                        ('max_shoe_size', models.IntegerField(blank=True, help_text='Grootste schoenmaat voor deze categorie', null=True, verbose_name='Max schoenmaat')),
                        ('is_active', models.BooleanField(default=True, verbose_name='Actief')),
                    ],
                    options={
                        'verbose_name': 'Schoenmaat',
                        'verbose_name_plural': 'Schoenmaten',
                        'ordering': ['min_shoe_size', 'name'],
                    },
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS equipment_sizetype (
                        id bigserial PRIMARY KEY,
                        name varchar(50) NOT NULL UNIQUE,
                        description text NOT NULL DEFAULT '',
                        min_shoe_size integer NULL,
                        max_shoe_size integer NULL,
                        is_active boolean NOT NULL DEFAULT true
                    );
                    """,
                    reverse_sql="DROP TABLE IF EXISTS equipment_sizetype;",
                ),
            ],
        ),

        # Step 2: Register Equipment.size_type FK in Django's migration state.
        # The column already exists in the database.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='equipment',
                    name='size_type',
                    field=models.ForeignKey(
                        blank=True,
                        help_text='Schoenmaat categorie (beheerd via Schoenmaten)',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to='equipment.sizetype',
                        verbose_name='Schoenmaat',
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'equipment_equipment'
                            AND column_name = 'size_type_id'
                        ) THEN
                            ALTER TABLE equipment_equipment
                                ADD COLUMN size_type_id bigint NULL
                                REFERENCES equipment_sizetype(id)
                                ON DELETE SET NULL
                                DEFERRABLE INITIALLY DEFERRED;
                            CREATE INDEX equipment_equipment_size_type_id_idx
                                ON equipment_equipment(size_type_id);
                        END IF;
                    END $$;
                    """,
                    reverse_sql="ALTER TABLE equipment_equipment DROP COLUMN IF EXISTS size_type_id;",
                ),
            ],
        ),

        # Step 3: Register SpringType.max_weight in Django's migration state.
        # The column already exists in the database.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='springtype',
                    name='max_weight',
                    field=models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text='Maximaal gewicht van een gebruiker voor dit type veer',
                        max_digits=5,
                        null=True,
                        verbose_name='Max gewicht (kg)',
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'equipment_springtype'
                            AND column_name = 'max_weight'
                        ) THEN
                            ALTER TABLE equipment_springtype
                                ADD COLUMN max_weight numeric(5,2) NULL;
                        END IF;
                    END $$;
                    """,
                    reverse_sql="ALTER TABLE equipment_springtype DROP COLUMN IF EXISTS max_weight;",
                ),
            ],
        ),

        # Step 4: Create EquipmentCategory model (new - doesn't exist in DB yet)
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

        # Step 5: Add category FK to Equipment (new - doesn't exist in DB yet)
        migrations.AddField(
            model_name='equipment',
            name='category',
            field=models.ForeignKey(
                blank=True,
                help_text='Kangoo Boot categorie (bijv. Small groen, Medium oranje)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='equipment.equipmentcategory',
                verbose_name='Categorie',
            ),
        ),
    ]
