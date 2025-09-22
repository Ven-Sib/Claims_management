import csv
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from decimal import Decimal

from claims.models import Claim, ClaimNote

class Command(BaseCommand):
    help = 'Load claims data from CSV or JSON file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the data file')
        parser.add_argument(
            '--format',
            type=str,
            choices=['csv', 'json'],
            default='csv',
            help='File format (csv or json)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        file_format = options['format']
        clear_data = options['clear']

        if clear_data:
            self.stdout.write('Clearing existing claims data...')
            Claim.objects.all().delete()

        try:
            if file_format == 'csv':
                self.lazypaste_load_csv(file_path)
            elif file_format == 'json':
                self.lazypaste_load_json(file_path)

            self.stdout.write(
                self.style.SUCCESS('Successfully loaded claims data')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading data: {str(e)}')
            )

    def lazypaste_load_csv(self, file_path):
        """Load claims from CSV file with pipe delimiter support"""
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Try pipe delimiter first, then comma
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            if '|' in sample:
                delimiter = '|'
            else:
                delimiter = ','
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            # Check if this is a detail file (has claim_id column) or main file (has patient_name)
            fieldnames = reader.fieldnames
            is_detail_file = 'claim_id' in fieldnames and 'patient_name' not in fieldnames
            is_main_file = 'patient_name' in fieldnames
            
            if is_detail_file:
                self.stdout.write('Processing detail file (updating existing claims)...')
            elif is_main_file:
                self.stdout.write('Processing main claims file...')
            else:
                self.stdout.write('Unknown file format, attempting to process...')
            
            for row in reader:
                try:
                    if is_detail_file:
                        # Detail file: Update existing claims with claim_id, denial_reason, cpt_codes
                        claim_id = row.get('claim_id', '')
                        
                        if not claim_id:
                            continue
                        
                        try:
                            claim = Claim.objects.get(claim_id=str(claim_id))
                            
                            # Update only the detail fields
                            if row.get('cpt_codes'):
                                claim.cpt_codes = row.get('cpt_codes', '')
                            if row.get('denial_reason') and row.get('denial_reason') != 'N/A':
                                claim.denial_reason = row.get('denial_reason', '')
                            
                            claim.save()
                            self.stdout.write(f'Updated details for claim {claim.claim_id}')
                            
                        except Claim.DoesNotExist:
                            self.stdout.write(f'Claim {claim_id} not found, skipping detail update')
                            continue
                            
                    else:
                        # Main file: Create/update full claim records
                        claim_id = row.get('id') or row.get('claim_id', '')
                        
                        if not claim_id:
                            self.stdout.write(f'Skipping row with no claim_id: {row}')
                            continue
                        
                        # Parse discharge date
                        discharge_date = parse_date(row.get('discharge_date', ''))
                        if not discharge_date:
                            discharge_date = datetime.now().date()
                        
                        # Handle status conversion
                        status = row.get('status', 'under_review').lower().replace(' ', '_')
                        
                        claim, created = Claim.objects.update_or_create(
                            claim_id=str(claim_id),
                            defaults={
                                'patient_name': row.get('patient_name', ''),
                                'billed_amount': Decimal(str(row.get('billed_amount', '0'))),
                                'paid_amount': Decimal(str(row.get('paid_amount', '0'))),
                                'status': status,
                                'insurer': row.get('insurer_name', ''),
                                'discharge_date': discharge_date,
                                'cpt_codes': row.get('cpt_codes', ''),
                                'denial_reason': row.get('denial_reason', ''),
                            }
                        )
                        
                        if created:
                            self.stdout.write(f'Created claim {claim.claim_id}')
                        else:
                            self.stdout.write(f'Updated claim {claim.claim_id}')
                        
                except Exception as e:
                    self.stdout.write(f'Error processing row {row}: {str(e)}')
                    continue

    def lazypaste_load_json(self, file_path):
        """Load claims from JSON file with auto-detection for file type"""
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            
            for item in data:
                try:
                    # Auto-detect file type and get claim_id
                    if 'patient_name' in item:
                        # File 1: Use 'id' as claim_id
                        claim_id = str(item.get('id', ''))
                        
                        # Process full claim data
                        discharge_date = parse_date(item.get('discharge_date', ''))
                        if not discharge_date:
                            discharge_date = datetime.now().date()
                        
                        claim, created = Claim.objects.update_or_create(
                            claim_id=claim_id,
                            defaults={
                                'patient_name': item.get('patient_name', ''),
                                'billed_amount': Decimal(str(item.get('billed_amount', '0'))),
                                'paid_amount': Decimal(str(item.get('paid_amount', '0'))),
                                'status': item.get('status', 'under_review').lower().replace(' ', '_'),
                                'insurer': item.get('insurer_name', ''),
                                'discharge_date': discharge_date,
                                'cpt_codes': item.get('cpt_codes', ''),
                                'denial_reason': item.get('denial_reason', ''),
                            }
                        )
                    else:
                        # File 2: Use 'claim_id' to find existing claim
                        claim_id = str(item.get('claim_id', ''))
                        
                        # Only update detail fields, don't touch patient data
                        claim, created = Claim.objects.update_or_create(
                            claim_id=claim_id,
                            defaults={
                                'cpt_codes': item.get('cpt_codes', ''),
                                'denial_reason': item.get('denial_reason', ''),
                            }
                        )
                    
                    if created:
                        self.stdout.write(f'Created claim {claim.claim_id}')
                    else:
                        self.stdout.write(f'Updated claim {claim.claim_id}')
                        
                except Exception as e:
                    self.stdout.write(f'Error processing item {item}: {str(e)}')
                    continue