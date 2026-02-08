"""
Management command to load data from a PostgreSQL v15 dump (previous schema version)
into the current database schema.

Handles these schema transformations:
- members_member: drops wants_insurance, adds date_of_birth=NULL, keeps insurance_status
- cards_sessioncard: maps text card_type + card_category to CardType FK
- equipment_equipment: maps text spring_type to SpringType FK, sets shell_type=NULL
- bookings_sessionattendance: extracts size_category from title field

Usage:
    python manage.py load_legacy_dump /path/to/dump.sql
    python manage.py load_legacy_dump /path/to/dump.sql --dry-run
"""

import re
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


# Mapping from title keywords to size_category codes
SIZE_CATEGORY_MAP = {
    'small': 'S',
    'medium': 'M',
    'large': 'L',
    'xtra large': 'XL',
    'extra large': 'XL',
}


def parse_copy_blocks(content):
    """Parse COPY ... FROM stdin blocks from a pg_dump file.

    Returns a dict of {table_name: {'columns': [...], 'rows': [...]}}
    """
    blocks = {}
    # Match COPY public.table_name (col1, col2, ...) FROM stdin;
    copy_pattern = re.compile(
        r'^COPY\s+public\.(\w+)\s+\(([^)]+)\)\s+FROM\s+stdin;',
        re.MULTILINE,
    )

    for match in copy_pattern.finditer(content):
        table_name = match.group(1)
        columns = [c.strip() for c in match.group(2).split(',')]

        # Find the data block after this COPY statement
        data_start = match.end() + 1  # skip the newline
        data_end = content.find('\n\\.', data_start)
        if data_end == -1:
            continue

        raw_data = content[data_start:data_end]
        rows = []
        for line in raw_data.split('\n'):
            if not line:
                continue
            # Tab-separated values; \N means NULL
            values = []
            for val in line.split('\t'):
                if val == '\\N':
                    values.append(None)
                else:
                    values.append(val)
            rows.append(values)

        blocks[table_name] = {
            'columns': columns,
            'rows': rows,
        }

    return blocks


def extract_size_category(title):
    """Extract size category from session title like 'Maat Small', 'Maat Medium', etc."""
    if not title:
        return None
    title_lower = title.lower()
    # Check for 'xtra large' / 'extra large' before 'large'
    for keyword, code in SIZE_CATEGORY_MAP.items():
        if keyword in title_lower:
            return code
    return None


def build_insert_sql(table, columns, rows, placeholder_count=None):
    """Build a parameterized INSERT statement with multiple value tuples."""
    if not rows:
        return None, []

    col_str = ', '.join(f'"{c}"' for c in columns)
    n = placeholder_count or len(columns)
    placeholders = ', '.join(['%s'] * n)
    sql = f'INSERT INTO public."{table}" ({col_str}) VALUES ({placeholders})'
    return sql, rows


class Command(BaseCommand):
    help = 'Load data from a previous-version PostgreSQL dump into the current schema'

    def add_arguments(self, parser):
        parser.add_argument(
            'dump_file',
            help='Path to the PostgreSQL dump (.sql) file',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and validate without inserting data',
        )

    def handle(self, *args, **options):
        dump_path = options['dump_file']
        dry_run = options['dry_run']

        try:
            with open(dump_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            raise CommandError(f'Dump file not found: {dump_path}')

        self.stdout.write(f'Parsing dump file: {dump_path}')
        blocks = parse_copy_blocks(content)

        self.stdout.write(f'Found {len(blocks)} table(s) with data:')
        for table, info in blocks.items():
            self.stdout.write(f'  - {table}: {len(info["rows"])} row(s)')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] Validating transformations...\n'))
            self._validate(blocks)
            self.stdout.write(self.style.SUCCESS('\nDry run complete. No data was inserted.'))
            return

        self.stdout.write('\nLoading data into current schema...\n')

        with transaction.atomic():
            self._load_all(blocks)

        self.stdout.write(self.style.SUCCESS('\nData migration complete.'))

    def _validate(self, blocks):
        """Validate that the dump contains expected tables and data can be transformed."""
        expected = [
            'members_member', 'cards_sessioncard', 'equipment_equipment',
            'bookings_sessionattendance', 'bookings_csvimport',
            'equipment_maintenancelog', 'auth_user', 'auth_permission',
            'django_content_type',
        ]
        for table in expected:
            if table not in blocks:
                self.stdout.write(self.style.WARNING(f'  Warning: expected table {table} not found'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  OK: {table} ({len(blocks[table]["rows"])} rows)'))

        # Validate card type mappings
        if 'cards_sessioncard' in blocks:
            card_data = blocks['cards_sessioncard']
            cols = card_data['columns']
            ct_idx = cols.index('card_type')
            cc_idx = cols.index('card_category')
            types_seen = set()
            for row in card_data['rows']:
                types_seen.add((row[ct_idx], row[cc_idx]))
            self.stdout.write(f'\n  Card types found: {types_seen}')

        # Validate spring type mappings
        if 'equipment_equipment' in blocks:
            eq_data = blocks['equipment_equipment']
            cols = eq_data['columns']
            st_idx = cols.index('spring_type')
            types_seen = set()
            for row in eq_data['rows']:
                types_seen.add(row[st_idx])
            self.stdout.write(f'  Spring types found: {types_seen}')

        # Validate size category extraction
        if 'bookings_sessionattendance' in blocks:
            att_data = blocks['bookings_sessionattendance']
            cols = att_data['columns']
            title_idx = cols.index('title')
            sizes = set()
            for row in att_data['rows']:
                sc = extract_size_category(row[title_idx])
                sizes.add(sc)
            self.stdout.write(f'  Size categories extracted: {sizes}')

    def _load_all(self, blocks):
        """Load all data in the correct order (respecting FK dependencies)."""
        cursor = connection.cursor()

        # ---- Phase 1: Create reference/lookup data ----
        self.stdout.write('Phase 1: Creating reference data...')

        # Create CardType records
        card_type_map = self._create_card_types(cursor, blocks)
        # Create SpringType records
        spring_type_map = self._create_spring_types(cursor)

        # ---- Phase 2: Load tables with no FK dependencies ----
        self.stdout.write('Phase 2: Loading independent tables...')

        self._load_direct(cursor, blocks, 'django_content_type')
        self._load_direct(cursor, blocks, 'auth_permission')
        self._load_direct(cursor, blocks, 'auth_group')
        self._load_direct(cursor, blocks, 'auth_user')
        self._load_direct(cursor, blocks, 'auth_group_permissions')
        self._load_direct(cursor, blocks, 'auth_user_groups')
        self._load_direct(cursor, blocks, 'auth_user_user_permissions')

        # ---- Phase 3: Load app data (FK dependencies) ----
        self.stdout.write('Phase 3: Loading app data with transformations...')

        self._load_members(cursor, blocks)
        self._load_session_cards(cursor, blocks, card_type_map)
        self._load_equipment(cursor, blocks, spring_type_map)
        self._load_session_attendance(cursor, blocks)
        self._load_direct(cursor, blocks, 'bookings_csvimport')
        self._load_direct(cursor, blocks, 'equipment_maintenancelog')

        # ---- Phase 4: Load admin log (depends on auth_user + content_type) ----
        self.stdout.write('Phase 4: Loading admin log...')
        self._load_direct(cursor, blocks, 'django_admin_log')

        # ---- Phase 5: Load django_migrations to record old migration history ----
        self.stdout.write('Phase 5: Loading migration history...')
        self._load_direct(cursor, blocks, 'django_migrations')

        # ---- Phase 6: Reset all sequences ----
        self.stdout.write('Phase 6: Resetting sequences...')
        self._reset_sequences(cursor)

        self.stdout.write(self.style.SUCCESS('All data loaded successfully.'))

    def _create_card_types(self, cursor, blocks):
        """Create CardType records based on the old card_type/card_category text values.

        Returns a mapping: (old_card_type_text, old_card_category) -> new_card_type_id
        """
        # Collect all unique (card_type, card_category) combinations from old data
        card_type_configs = {}
        if 'cards_sessioncard' in blocks:
            card_data = blocks['cards_sessioncard']
            cols = card_data['columns']
            ct_idx = cols.index('card_type')
            cc_idx = cols.index('card_category')
            ts_idx = cols.index('total_sessions')

            for row in card_data['rows']:
                key = (row[ct_idx], row[cc_idx])
                if key not in card_type_configs:
                    card_type_configs[key] = int(row[ts_idx])

        # Define the CardType records to create
        # Map old text values to proper CardType attributes
        card_type_map = {}
        sort_order = 0

        # Known card types from the dump
        type_definitions = {
            ('1-Sessie Kaart', 'trial'): {'sessions': 1, 'price': 10.00, 'category': 'trial', 'name': '1 Beurt (Proefles)'},
            ('1-Sessie Kaart', 'regular'): {'sessions': 1, 'price': 10.00, 'category': 'trial', 'name': '1 Beurt (Proefles)'},
            ('5-Sessie Kaart', 'regular'): {'sessions': 5, 'price': 60.00, 'category': 'regular', 'name': '5 Beurten'},
            ('10-Sessie Kaart', 'regular'): {'sessions': 10, 'price': 100.00, 'category': 'regular', 'name': '10 Beurten'},
        }

        for (old_type, old_cat), defaults in type_definitions.items():
            sort_order += 1
            cursor.execute(
                """
                INSERT INTO cards_cardtype (name, sessions, price, category, is_active, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                [defaults['name'], defaults['sessions'], defaults['price'],
                 defaults['category'], True, sort_order],
            )
            card_type_id = cursor.fetchone()[0]
            card_type_map[(old_type, old_cat)] = card_type_id
            self.stdout.write(f'  Created CardType: {defaults["name"]} (id={card_type_id})')

        # Handle any unexpected combinations from the dump
        for key, total_sessions in card_type_configs.items():
            if key not in card_type_map:
                old_type, old_cat = key
                # Try to match to an existing CardType by text pattern
                matched = False
                for def_key, def_id in card_type_map.items():
                    if def_key[0] == old_type:
                        card_type_map[key] = def_id
                        matched = True
                        break
                if not matched:
                    sort_order += 1
                    sessions = total_sessions or 10
                    category = 'trial' if old_cat == 'trial' else 'regular'
                    cursor.execute(
                        """
                        INSERT INTO cards_cardtype (name, sessions, price, category, is_active, sort_order)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        [old_type, sessions, 0, category, True, sort_order],
                    )
                    card_type_id = cursor.fetchone()[0]
                    card_type_map[key] = card_type_id
                    self.stdout.write(
                        self.style.WARNING(f'  Created fallback CardType: {old_type} (id={card_type_id})')
                    )

        return card_type_map

    def _create_spring_types(self, cursor):
        """Create SpringType records for the old text-based spring types.

        Returns a mapping: old_text_value -> new_spring_type_id
        """
        spring_type_map = {}
        definitions = [
            ('standard', 'Standaard', 'Standaard XR6 veren'),
            ('hd', 'HD', 'Heavy Duty Pro6/Pro7 veren'),
        ]
        for old_val, name, description in definitions:
            cursor.execute(
                """
                INSERT INTO equipment_springtype (name, description, is_active)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                [name, description, True],
            )
            spring_type_id = cursor.fetchone()[0]
            spring_type_map[old_val] = spring_type_id
            self.stdout.write(f'  Created SpringType: {name} (id={spring_type_id})')

        return spring_type_map

    def _load_direct(self, cursor, blocks, table_name):
        """Load a table directly with no transformations needed."""
        if table_name not in blocks:
            self.stdout.write(f'  Skipping {table_name} (no data in dump)')
            return

        data = blocks[table_name]
        columns = data['columns']
        rows = data['rows']

        if not rows:
            self.stdout.write(f'  Skipping {table_name} (empty)')
            return

        col_str = ', '.join(f'"{c}"' for c in columns)
        placeholders = ', '.join(['%s'] * len(columns))
        sql = f'INSERT INTO public."{table_name}" ({col_str}) VALUES ({placeholders})'

        count = 0
        for row in rows:
            cursor.execute(sql, row)
            count += 1

        self.stdout.write(f'  Loaded {table_name}: {count} row(s)')

    def _load_members(self, cursor, blocks):
        """Load members_member with schema transformation.

        Old: id, email, first_name, last_name, shoe_size, phone, notes,
             created_at, updated_at, wants_insurance, insurance_status
        New: id, email, first_name, last_name, date_of_birth, shoe_size, phone,
             insurance_status, notes, created_at, updated_at
        """
        if 'members_member' not in blocks:
            self.stdout.write('  Skipping members_member (no data)')
            return

        data = blocks['members_member']
        old_cols = data['columns']
        rows = data['rows']

        # Build column index map
        idx = {col: i for i, col in enumerate(old_cols)}

        new_columns = [
            'id', 'email', 'first_name', 'last_name', 'date_of_birth',
            'shoe_size', 'phone', 'insurance_status', 'notes',
            'created_at', 'updated_at',
        ]
        col_str = ', '.join(f'"{c}"' for c in new_columns)
        placeholders = ', '.join(['%s'] * len(new_columns))
        sql = f'INSERT INTO public."members_member" ({col_str}) VALUES ({placeholders})'

        count = 0
        for row in rows:
            new_row = [
                row[idx['id']],
                row[idx['email']],
                row[idx['first_name']],
                row[idx['last_name']],
                None,  # date_of_birth (not in old schema)
                row[idx['shoe_size']],
                row[idx['phone']],
                row[idx['insurance_status']],
                row[idx['notes']],
                row[idx['created_at']],
                row[idx['updated_at']],
            ]
            cursor.execute(sql, new_row)
            count += 1

        self.stdout.write(f'  Loaded members_member: {count} row(s)')

    def _load_session_cards(self, cursor, blocks, card_type_map):
        """Load cards_sessioncard with schema transformation.

        Old: id, card_type(text), total_sessions, sessions_used, purchased_date,
             expiry_date, status, price_paid, notes, created_at, updated_at,
             member_id, card_category
        New: id, total_sessions, sessions_used, purchased_date, expiry_date,
             status, price_paid, notes, created_at, updated_at, member_id,
             card_type_id (FK)
        """
        if 'cards_sessioncard' not in blocks:
            self.stdout.write('  Skipping cards_sessioncard (no data)')
            return

        data = blocks['cards_sessioncard']
        old_cols = data['columns']
        rows = data['rows']

        idx = {col: i for i, col in enumerate(old_cols)}

        new_columns = [
            'id', 'total_sessions', 'sessions_used', 'purchased_date',
            'expiry_date', 'status', 'price_paid', 'notes', 'created_at',
            'updated_at', 'member_id', 'card_type_id',
        ]
        col_str = ', '.join(f'"{c}"' for c in new_columns)
        placeholders = ', '.join(['%s'] * len(new_columns))
        sql = f'INSERT INTO public."cards_sessioncard" ({col_str}) VALUES ({placeholders})'

        count = 0
        for row in rows:
            old_card_type = row[idx['card_type']]
            old_category = row[idx['card_category']]
            card_type_id = card_type_map.get((old_card_type, old_category))

            if card_type_id is None:
                # Fallback: try matching by card_type text only
                for key, val in card_type_map.items():
                    if key[0] == old_card_type:
                        card_type_id = val
                        break

            if card_type_id is None:
                self.stdout.write(self.style.WARNING(
                    f'  Warning: No CardType match for ({old_card_type}, {old_category}), '
                    f'using first available'
                ))
                card_type_id = list(card_type_map.values())[0]

            new_row = [
                row[idx['id']],
                row[idx['total_sessions']],
                row[idx['sessions_used']],
                row[idx['purchased_date']],
                row[idx['expiry_date']],
                row[idx['status']],
                row[idx['price_paid']],
                row[idx['notes']],
                row[idx['created_at']],
                row[idx['updated_at']],
                row[idx['member_id']],
                card_type_id,
            ]
            cursor.execute(sql, new_row)
            count += 1

        self.stdout.write(f'  Loaded cards_sessioncard: {count} row(s)')

    def _load_equipment(self, cursor, blocks, spring_type_map):
        """Load equipment_equipment with schema transformation.

        Old: id, name, equipment_id, size, status, purchase_date, last_maintenance,
             next_maintenance, notes, created_at, updated_at, spring_type(text)
        New: id, name, equipment_id, size, status, purchase_date, last_maintenance,
             next_maintenance, notes, created_at, updated_at, spring_type_id(FK),
             shell_type_id(FK)
        """
        if 'equipment_equipment' not in blocks:
            self.stdout.write('  Skipping equipment_equipment (no data)')
            return

        data = blocks['equipment_equipment']
        old_cols = data['columns']
        rows = data['rows']

        idx = {col: i for i, col in enumerate(old_cols)}

        new_columns = [
            'id', 'name', 'equipment_id', 'size', 'status', 'purchase_date',
            'last_maintenance', 'next_maintenance', 'notes', 'created_at',
            'updated_at', 'spring_type_id', 'shell_type_id',
        ]
        col_str = ', '.join(f'"{c}"' for c in new_columns)
        placeholders = ', '.join(['%s'] * len(new_columns))
        sql = f'INSERT INTO public."equipment_equipment" ({col_str}) VALUES ({placeholders})'

        count = 0
        for row in rows:
            old_spring_type = row[idx['spring_type']]
            spring_type_id = spring_type_map.get(old_spring_type)

            new_row = [
                row[idx['id']],
                row[idx['name']],
                row[idx['equipment_id']],
                row[idx['size']],
                row[idx['status']],
                row[idx['purchase_date']],
                row[idx['last_maintenance']],
                row[idx['next_maintenance']],
                row[idx['notes']],
                row[idx['created_at']],
                row[idx['updated_at']],
                spring_type_id,
                None,  # shell_type_id (not in old schema)
            ]
            cursor.execute(sql, new_row)
            count += 1

        self.stdout.write(f'  Loaded equipment_equipment: {count} row(s)')

    def _load_session_attendance(self, cursor, blocks):
        """Load bookings_sessionattendance with schema transformation.

        Old: id, session_date, title, description, location, capacity,
             total_attendees, waiting_list, created_by, modified_by,
             import_date, notes, member_id, session_card_id,
             card_session_used, was_present
        New: same columns + size_category (extracted from title)
        """
        if 'bookings_sessionattendance' not in blocks:
            self.stdout.write('  Skipping bookings_sessionattendance (no data)')
            return

        data = blocks['bookings_sessionattendance']
        old_cols = data['columns']
        rows = data['rows']

        idx = {col: i for i, col in enumerate(old_cols)}

        new_columns = old_cols + ['size_category']
        col_str = ', '.join(f'"{c}"' for c in new_columns)
        placeholders = ', '.join(['%s'] * len(new_columns))
        sql = f'INSERT INTO public."bookings_sessionattendance" ({col_str}) VALUES ({placeholders})'

        count = 0
        size_stats = {}
        for row in rows:
            title = row[idx['title']]
            size_category = extract_size_category(title)
            size_stats[size_category] = size_stats.get(size_category, 0) + 1

            new_row = list(row) + [size_category]
            cursor.execute(sql, new_row)
            count += 1

        self.stdout.write(f'  Loaded bookings_sessionattendance: {count} row(s)')
        self.stdout.write(f'    Size categories assigned: {size_stats}')

    def _reset_sequences(self, cursor):
        """Reset all auto-increment sequences to match the loaded data."""
        sequences = [
            ('auth_group_id_seq', 'auth_group', 'id'),
            ('auth_group_permissions_id_seq', 'auth_group_permissions', 'id'),
            ('auth_permission_id_seq', 'auth_permission', 'id'),
            ('auth_user_id_seq', 'auth_user', 'id'),
            ('auth_user_groups_id_seq', 'auth_user_groups', 'id'),
            ('auth_user_user_permissions_id_seq', 'auth_user_user_permissions', 'id'),
            ('bookings_csvimport_id_seq', 'bookings_csvimport', 'id'),
            ('bookings_sessionattendance_id_seq', 'bookings_sessionattendance', 'id'),
            ('cards_sessioncard_id_seq', 'cards_sessioncard', 'id'),
            ('django_admin_log_id_seq', 'django_admin_log', 'id'),
            ('django_content_type_id_seq', 'django_content_type', 'id'),
            ('django_migrations_id_seq', 'django_migrations', 'id'),
            ('equipment_equipment_id_seq', 'equipment_equipment', 'id'),
            ('equipment_maintenancelog_id_seq', 'equipment_maintenancelog', 'id'),
            ('members_member_id_seq', 'members_member', 'id'),
        ]

        for seq_name, table, column in sequences:
            try:
                cursor.execute(
                    f"SELECT setval('public.\"{seq_name}\"', "
                    f"COALESCE((SELECT MAX(\"{column}\") FROM public.\"{table}\"), 0) + 1, false)"
                )
                result = cursor.fetchone()
                self.stdout.write(f'  Reset {seq_name} -> {result[0]}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Could not reset {seq_name}: {e}'))
