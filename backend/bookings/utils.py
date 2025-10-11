import pandas as pd
from datetime import datetime
from django.core.files.base import ContentFile
from members.models import Member
from cards.models import SessionCard
from .models import SessionAttendance, CSVImport

def process_csv_import(csv_file, imported_by='admin', auto_assign_cards=True):
    print("=" * 50)
    print("CSV IMPORT STARTED")
    print(f"File: {csv_file.name}")
    print(f"Imported by: {imported_by}")
    print(f"Auto assign cards: {auto_assign_cards}")
    print("=" * 50)

def parse_dutch_datetime(date_str, time_str=None):
    """
    Parse Dutch datetime format with flexible spacing
    Handles: "7/10/2025   19:30" or separate date/time
    """
    if not date_str or str(date_str).strip() == 'nan':
        return None
    
    # If time_str provided separately, use it
    if time_str and str(time_str).strip() != 'nan':
        datetime_str = f"{str(date_str).strip()} {str(time_str).strip()}"
    else:
        # Clean up the string - normalize multiple spaces to single space
        datetime_str = ' '.join(str(date_str).strip().split())
    
    # Try multiple date formats - order matters!
    formats = [
        '%d/%m/%Y %H:%M',      # d/m/yyyy HH:MM (handles 7/10/2025 19:30)
        '%d/%m/%y %H:%M',      # d/m/yy HH:MM
        '%d-%m-%Y %H:%M',      # dd-mm-yyyy HH:MM
        '%d-%m-%y %H:%M',      # dd-mm-yy HH:MM
        '%Y-%m-%d %H:%M',      # yyyy-mm-dd HH:MM
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    
    return None

def process_csv_import(csv_file, imported_by='admin', auto_assign_cards=True):
    """
    Process CSV import and create SessionAttendance records
    
    Expected CSV columns:
    - Begintijd or Eindtijd (dd/mm/yyyy HH:MM format)
    - Titel (session title)
    - Omschrijving (description)
    - Capaciteit (capacity)
    - Totaal (total attendees)
    - Wachtend (waiting list)
    - Locatie (location)
    - E-mail (member email - REQUIRED)
    - Schoenmaat (shoe size)
    - Gemaakt door (created by)
    - Gewijzigd door (modified by)
    """
    errors = []
    rows_processed = 0
    rows_created = 0
    rows_skipped = 0
    
    try:
        # Read CSV with pandas
        df = pd.read_csv(csv_file, encoding='utf-8')
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        print(f"CSV Columns found: {list(df.columns)}")
        print(f"Total rows in CSV: {len(df)}")
        
        # Create CSV import record
        csv_import = CSVImport.objects.create(
            filename=csv_file.name,
            imported_by=imported_by
        )
        
        # Save the file
        csv_file.seek(0)
        csv_import.file.save(csv_file.name, ContentFile(csv_file.read()), save=False)
        
        for index, row in df.iterrows():
            rows_processed += 1
            
            try:
                # ===== GET OR CREATE MEMBER =====
                email = None
                
                # Try E-mail column first
                if 'E-mail' in df.columns and pd.notna(row.get('E-mail')):
                    email = str(row.get('E-mail')).strip().lower()
                
                # If E-mail is empty, try Gemaakt door (Created by)
                if not email or email == 'nan':
                    if 'Gemaakt door' in df.columns:
                        created_by = str(row.get('Gemaakt door', '')).strip()
                        if '@' in created_by and '.' in created_by:
                            email = created_by.lower()
                
                if not email or email == 'nan' or '@' not in email:
                    errors.append(f"Rij {index + 2}: Geen geldig e-mailadres gevonden")
                    rows_skipped += 1
                    continue
                
                # Get shoe size
                shoe_size = ''
                if 'Schoenmaat' in df.columns and pd.notna(row.get('Schoenmaat')):
                    shoe_size = str(row.get('Schoenmaat')).strip()
                
                member, created = Member.objects.get_or_create(
                    email=email,
                    defaults={'shoe_size': shoe_size}
                )
                
                # Update shoe size if member exists and we have new info
                if not created and shoe_size and not member.shoe_size:
                    member.shoe_size = shoe_size
                    member.save()
                
                # ===== PARSE SESSION DATE =====
                session_date_str = None
                time_str = None
                
                # Try Eindtijd first, then Begintijd
                if 'Eindtijd' in df.columns and pd.notna(row.get('Eindtijd')):
                    session_date_str = str(row.get('Eindtijd')).strip()
                elif 'Begintijd' in df.columns and pd.notna(row.get('Begintijd')):
                    session_date_str = str(row.get('Begintijd')).strip()
                
                if not session_date_str:
                    errors.append(f"Rij {index + 2}: Geen geldige datum (Eindtijd of Begintijd)")
                    rows_skipped += 1
                    continue
                
                session_date = parse_dutch_datetime(session_date_str)
                
                if not session_date:
                    errors.append(f"Rij {index + 2}: Ongeldige datumformat '{session_date_str}'")
                    rows_skipped += 1
                    continue
                
                # ===== GET SESSION DETAILS =====
                title = str(row.get('Titel', 'Kangoo Jumping Sessie')).strip() if 'Titel' in df.columns else 'Kangoo Jumping Sessie'
                description = str(row.get('Omschrijving', '')).strip() if 'Omschrijving' in df.columns and pd.notna(row.get('Omschrijving')) else ''
                location = str(row.get('Locatie', '')).strip() if 'Locatie' in df.columns and pd.notna(row.get('Locatie')) else ''
                
                capacity = None
                if 'Capaciteit' in df.columns and pd.notna(row.get('Capaciteit')):
                    try:
                        capacity = int(row.get('Capaciteit'))
                    except (ValueError, TypeError):
                        capacity = None
                
                total = None
                if 'Totaal' in df.columns and pd.notna(row.get('Totaal')):
                    try:
                        total = int(row.get('Totaal'))
                    except (ValueError, TypeError):
                        total = None
                
                waiting = 0
                if 'Wachtend' in df.columns and pd.notna(row.get('Wachtend')):
                    try:
                        waiting = int(row.get('Wachtend'))
                    except (ValueError, TypeError):
                        waiting = 0
                
                created_by = str(row.get('Gemaakt door', '')).strip() if 'Gemaakt door' in df.columns and pd.notna(row.get('Gemaakt door')) else ''
                modified_by = str(row.get('Gewijzigd door', '')).strip() if 'Gewijzigd door' in df.columns and pd.notna(row.get('Gewijzigd door')) else ''
                
                # ===== TRY TO FIND OR ASSIGN A SESSION CARD =====
                session_card = None
                if auto_assign_cards:
                    active_cards = member.active_cards()
                    if active_cards.exists():
                        # Get the first active card
                        session_card = active_cards.first()
                
                # ===== CREATE OR UPDATE ATTENDANCE RECORD =====
                attendance, created = SessionAttendance.objects.get_or_create(
                    member=member,
                    session_date=session_date,
                    title=title,
                    defaults={
                        'session_card': session_card,
                        'description': description,
                        'location': location,
                        'capacity': capacity,
                        'total_attendees': total,
                        'waiting_list': waiting,
                        'created_by': created_by,
                        'modified_by': modified_by,
                    }
                )
                
                if created:
                    rows_created += 1
                else:
                    rows_skipped += 1
                    
            except Exception as e:
                errors.append(f"Rij {index + 2}: {str(e)}")
                rows_skipped += 1
        
        # ===== UPDATE IMPORT RECORD =====
        csv_import.rows_processed = rows_processed
        csv_import.rows_created = rows_created
        csv_import.rows_skipped = rows_skipped
        csv_import.errors = '\n'.join(errors) if errors else ''
        csv_import.save()
        
        return {
            'processed': rows_processed,
            'created': rows_created,
            'skipped': rows_skipped,
            'errors': errors,
            'import_id': csv_import.id
        }
        
    except Exception as e:
        raise Exception(f"Fout bij het verwerken van CSV: {str(e)}")