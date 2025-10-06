import pandas as pd
from datetime import datetime
from django.core.files.base import ContentFile
from members.models import Member
from cards.models import SessionCard
from .models import SessionAttendance, CSVImport

def parse_dutch_datetime(date_str):
    """Parse Dutch datetime format: supports multiple formats"""
    if not date_str or str(date_str).strip() == 'nan':
        return None
    
    # Clean up the string - remove extra spaces
    date_str = ' '.join(str(date_str).strip().split())
    
    # Try multiple date formats
    formats = [
        '%d/%m/%Y %H:%M',      # d/m/yyyy HH:MM or dd/mm/yyyy HH:MM
        '%d-%m-%Y %H:%M',      # dd-mm-yyyy HH:MM
        '%d/%m/%y %H:%M',      # d/m/yy HH:MM
        '%d-%m-%y %H:%M',      # dd-mm-yy HH:MM
        '%Y-%m-%d %H:%M',      # yyyy-mm-dd HH:MM
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def process_csv_import(csv_file, imported_by='admin', auto_assign_cards=True):
    """
    Process CSV import and create SessionAttendance records
    
    Expected CSV columns:
    - Eindtijd (dd-mm-yyyy HH:MM)
    - Titel
    - Omschrijving
    - Capaciteit
    - Totaal
    - Wachtend
    - Locatie
    - E-mail
    - Schoenmaat
    - Gemaakt door
    - Gewijzigd door
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
        
        # Log the columns found
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
                # Get or create member - try multiple columns for email
                email = None
                
                # Try E-mail column first
                if pd.notna(row.get('E-mail')):
                    email = str(row.get('E-mail')).strip().lower()
                
                # If E-mail is empty, try Gemaakt door (Created by)
                if not email or email == 'nan':
                    created_by = str(row.get('Gemaakt door', '')).strip()
                    # Check if it looks like an email
                    if '@' in created_by and '.' in created_by:
                        email = created_by.lower()
                
                if not email or email == 'nan' or '@' not in email:
                    errors.append(f"Rij {index + 2}: Geen geldig e-mailadres gevonden (E-mail of Gemaakt door)")
                    rows_skipped += 1
                    continue
                
                member, created = Member.objects.get_or_create(
                    email=email,
                    defaults={
                        'shoe_size': str(row.get('Schoenmaat', '')).strip() if pd.notna(row.get('Schoenmaat')) else ''
                    }
                )
                
                # Parse session date - try both Eindtijd and Begintijd
                session_date_str = None
                if 'Eindtijd' in row and pd.notna(row.get('Eindtijd')):
                    session_date_str = str(row.get('Eindtijd')).strip()
                elif 'Begintijd' in row and pd.notna(row.get('Begintijd')):
                    session_date_str = str(row.get('Begintijd')).strip()
                
                if not session_date_str:
                    errors.append(f"Rij {index + 2}: Geen geldige datum (Eindtijd of Begintijd)")
                    rows_skipped += 1
                    continue
                
                session_date = parse_dutch_datetime(session_date_str)
                
                if not session_date:
                    errors.append(f"Rij {index + 2}: Ongeldige datum '{session_date_str}'")
                    rows_skipped += 1
                    continue
                
                # Get session details
                title = str(row.get('Titel', 'Kangoo Jumping Sessie')).strip()
                description = str(row.get('Omschrijving', '')).strip() if pd.notna(row.get('Omschrijving')) else ''
                location = str(row.get('Locatie', '')).strip() if pd.notna(row.get('Locatie')) else ''
                capacity = int(row.get('Capaciteit')) if pd.notna(row.get('Capaciteit')) else None
                total = int(row.get('Totaal')) if pd.notna(row.get('Totaal')) else None
                waiting = int(row.get('Wachtend', 0)) if pd.notna(row.get('Wachtend')) else 0
                created_by = str(row.get('Gemaakt door', '')).strip() if pd.notna(row.get('Gemaakt door')) else ''
                modified_by = str(row.get('Gewijzigd door', '')).strip() if pd.notna(row.get('Gewijzigd door')) else ''
                
                # Try to find or assign a session card
                session_card = None
                if auto_assign_cards:
                    # Try to find an active card for this member
                    active_cards = member.active_cards()
                    if active_cards.exists():
                        session_card = active_cards.first()
                
                # Create or update attendance record
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
                    # Use a session from the card if assigned
                    if session_card and auto_assign_cards:
                        try:
                            session_card.use_session()
                        except ValueError as e:
                            errors.append(f"Rij {index + 2}: Kon sessie niet gebruiken - {str(e)}")
                else:
                    rows_skipped += 1
                    
            except Exception as e:
                errors.append(f"Rij {index + 2}: {str(e)}")
                rows_skipped += 1
        
        # Update import record
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