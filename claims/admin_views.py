from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Avg, Sum
from django.contrib.auth.models import User
from django.http import JsonResponse
from decimal import Decimal
import csv
import json
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from datetime import datetime
from django.utils.dateparse import parse_date
from .models import Claim, ClaimNote

@login_required
@staff_member_required
def lazypaste_admin_dashboard(request):
    """Main admin dashboard with stats and quick actions"""
    
    # Calculate system statistics with robustness in data aggregation
    total_claims = Claim.objects.count()
    flagged_claims = Claim.objects.filter(is_flagged=True).count()
    
    # Calculate average underpayment (difference between billed and paid)
    claims_with_amounts = Claim.objects.exclude(billed_amount=0)
    avg_underpayment = 0
    total_underpayment = 0
    
    if claims_with_amounts.exists():
        underpayments = []
        total_billed = Decimal('0')
        total_paid = Decimal('0')
        
        for claim in claims_with_amounts:
            underpayment = claim.billed_amount - claim.paid_amount
            if underpayment > 0:  # Only count actual underpayments
                underpayments.append(underpayment)
                total_underpayment += underpayment
            total_billed += claim.billed_amount
            total_paid += claim.paid_amount
        
        if underpayments:
            avg_underpayment = sum(underpayments) / len(underpayments)
    
    # Status distribution with calculated percentages
    status_counts = Claim.objects.values('status').annotate(count=Count('status'))
    status_stats = []
    
    for status in status_counts:
        percentage = (status['count'] / total_claims * 100) if total_claims > 0 else 0
        status_stats.append({
            'status': status['status'],
            'count': status['count'],
            'percentage': round(percentage, 1)  # Round to 1 decimal place
        })
    
    # Recent activity
    recent_notes = ClaimNote.objects.select_related('claim').order_by('-created_at')[:10]
    recent_claims = Claim.objects.order_by('-created_at')[:5]
    
    # User statistics
    total_users = User.objects.count()
    admin_users = User.objects.filter(is_staff=True).count()
    
    context = {
        'total_claims': total_claims,
        'flagged_claims': flagged_claims,
        'avg_underpayment': avg_underpayment,
        'total_underpayment': total_underpayment,
        'status_stats': status_stats, 
        'recent_notes': recent_notes,
        'recent_claims': recent_claims,
        'total_users': total_users,
        'admin_users': admin_users,
    }
    
    return render(request, 'admin/dashboard.html', context)

@login_required
@staff_member_required
def lazypaste_csv_upload(request):
    """CSV upload page"""
    return render(request, 'admin/csv_upload.html')

@login_required
@staff_member_required
def lazypaste_process_csv(request):
    """bulk CSV processing optimized for PostgreSQL"""
    if request.method != 'POST':
        return redirect('admin_dashboard:csv_upload')
    
    csv_file_1 = request.FILES.get('csv_file_1')
    csv_file_2 = request.FILES.get('csv_file_2')
    upload_mode = request.POST.get('upload_mode')
    
    # Validation
    if not csv_file_1 and not csv_file_2:
        messages.error(request, 'Please select at least one CSV file.')
        return redirect('admin_dashboard:csv_upload')
    
    if csv_file_1 and not csv_file_1.name.endswith('.csv'):
        messages.error(request, 'File 1 must be a valid CSV file.')
        return redirect('admin_dashboard:csv_upload')
    
    if csv_file_2 and not csv_file_2.name.endswith('.csv'):
        messages.error(request, 'File 2 must be a valid CSV file.')
        return redirect('admin_dashboard:csv_upload')
    
    # 4MB file size limit
    MAX_FILE_SIZE = 4 * 1024 * 1024
    if csv_file_1 and csv_file_1.size > MAX_FILE_SIZE:
        messages.error(request, 'File 1 is too large. Please use files under 4MB.')
        return redirect('admin_dashboard:csv_upload')
    
    if csv_file_2 and csv_file_2.size > MAX_FILE_SIZE:
        messages.error(request, 'File 2 is too large. Please use files under 4MB.')
        return redirect('admin_dashboard:csv_upload')
    
    try:
        total_result = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'deleted': 0,
            'error_details': []
        }
        
        # Handle overwrite mode
        if upload_mode == 'overwrite':
            deleted_count = Claim.objects.count()
            if deleted_count > 0:
                Claim.objects.all().delete()
                total_result['deleted'] = deleted_count
        
        # Process files
        files_to_process = []
        if csv_file_1:
            files_to_process.append(csv_file_1)
        if csv_file_2:
            files_to_process.append(csv_file_2)
        
        for csv_file in files_to_process:
            file_name = default_storage.save(f'temp/{csv_file.name}', ContentFile(csv_file.read()))
            file_path = default_storage.path(file_name)
            
            result = load_csv_data_bulk(file_path)
            
            total_result['created'] += result['created']
            total_result['updated'] += result['updated']
            total_result['errors'] += result['errors']
            total_result['error_details'].extend(result.get('error_details', []))
            
            default_storage.delete(file_name)
        
        success_message = f"Upload completed! {total_result['created']} created, {total_result['updated']} updated"
        if total_result['deleted'] > 0:
            success_message += f", {total_result['deleted']} deleted"
        success_message += f", {total_result['errors']} errors."
        
        messages.success(request, success_message)
        return render(request, 'admin/csv_results.html', {'result': total_result})
    
    except Exception as e:
        messages.error(request, f'Error processing file: {str(e)}')
        return redirect('admin_dashboard:csv_upload')


def load_csv_data_bulk(file_path):
    """bulk CSV processing using PostgreSQL-optimized operations"""
    created_count = 0
    updated_count = 0
    error_count = 0
    errors = []
    
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        # Auto-detect delimiter
        sample = csvfile.read(1024)
        csvfile.seek(0)
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        
        # Parse all rows first
        parsed_data = []
        for row_num, row in enumerate(reader, 1):
            claim_id = str(row.get('claim_id', '') or row.get('id', '')).strip()
            if not claim_id:
                errors.append(f"Row {row_num}: No claim ID found")
                error_count += 1
                continue
            
            try:
                parsed_row = {
                    'claim_id': claim_id,
                    'patient_name': row.get('patient_name', 'N/A').strip() if row.get('patient_name') else 'N/A',
                    'billed_amount': Decimal(str(row.get('billed_amount', '0'))) if row.get('billed_amount') else Decimal('0'),
                    'paid_amount': Decimal(str(row.get('paid_amount', '0'))) if row.get('paid_amount') else Decimal('0'),
                    'status': row.get('status', 'under_review').lower().replace(' ', '_') if row.get('status') else 'under_review',
                    'insurer': row.get('insurer_name', 'N/A').strip() if row.get('insurer_name') else 'N/A',
                    'discharge_date': parse_date(row.get('discharge_date', '')),
                    'cpt_codes': row.get('cpt_codes', 'N/A').strip() if row.get('cpt_codes') else 'N/A',
                    'denial_reason': row.get('denial_reason', 'N/A').strip() if row.get('denial_reason') else 'N/A',
                }
                parsed_data.append(parsed_row)
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1
        
        if not parsed_data:
            return {'created': 0, 'updated': 0, 'errors': error_count, 'error_details': errors[:10]}
        
        # Get all claim IDs from parsed data
        claim_ids = [row['claim_id'] for row in parsed_data]
        
        # Single query to get existing claims
        existing_claims_dict = {
            claim.claim_id: claim 
            for claim in Claim.objects.filter(claim_id__in=claim_ids)
        }
        
        # Separate new claims from updates
        claims_to_create = []
        claims_to_update = []
        
        for row_data in parsed_data:
            claim_id = row_data['claim_id']
            
            if claim_id in existing_claims_dict:
                # Update existing claim
                claim = existing_claims_dict[claim_id]
                needs_update = False
                
                # Only update fields that are currently N/A or 0
                if row_data['patient_name'] != 'N/A' and claim.patient_name == 'N/A':
                    claim.patient_name = row_data['patient_name']
                    needs_update = True
                
                if row_data['billed_amount'] != Decimal('0') and claim.billed_amount == Decimal('0'):
                    claim.billed_amount = row_data['billed_amount']
                    needs_update = True
                
                if row_data['paid_amount'] != Decimal('0') and claim.paid_amount == Decimal('0'):
                    claim.paid_amount = row_data['paid_amount']
                    needs_update = True
                
                if row_data['status'] != 'under_review' and claim.status == 'under_review':
                    claim.status = row_data['status']
                    needs_update = True
                
                if row_data['insurer'] != 'N/A' and claim.insurer == 'N/A':
                    claim.insurer = row_data['insurer']
                    needs_update = True
                
                if row_data['cpt_codes'] != 'N/A' and claim.cpt_codes == 'N/A':
                    claim.cpt_codes = row_data['cpt_codes']
                    needs_update = True
                
                if row_data['denial_reason'] != 'N/A' and claim.denial_reason == 'N/A':
                    claim.denial_reason = row_data['denial_reason']
                    needs_update = True
                
                if needs_update:
                    claims_to_update.append(claim)
            else:
                # Create new claim
                claims_to_create.append(Claim(**row_data))
        
        # Perform bulk operations
        if claims_to_create:
            # Bulk create new claims
            Claim.objects.bulk_create(claims_to_create, batch_size=500)
            created_count = len(claims_to_create)
        
        if claims_to_update:
            # Bulk update existing claims
            Claim.objects.bulk_update(
                claims_to_update,
                ['patient_name', 'billed_amount', 'paid_amount', 'status', 'insurer', 'cpt_codes', 'denial_reason'],
                batch_size=500
            )
            updated_count = len(claims_to_update)
    
    return {
        'created': created_count,
        'updated': updated_count,
        'errors': error_count,
        'error_details': errors[:10]
    }

@login_required
@staff_member_required
def lazypaste_manage_users(request):
    """User management interface with enhanced functionality"""
    users = User.objects.all().order_by('-date_joined')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        try:
            user = User.objects.get(id=user_id)
            
            # Prevent users from modifying superusers or themselves
            if user.is_superuser:
                messages.error(request, 'Cannot modify super admin accounts.')
                return redirect('admin_dashboard:manage_users')
                
            if user == request.user:
                messages.error(request, 'Cannot modify your own account.')
                return redirect('admin_dashboard:manage_users')
            
            if action == 'make_staff':
                user.is_staff = True
                user.save()
                messages.success(request, f'{user.username} has been promoted to admin.')
                
            elif action == 'remove_staff':
                user.is_staff = False
                user.save()
                messages.success(request, f'{user.username} admin privileges have been removed.')
                
            elif action == 'deactivate':
                user.is_active = False
                user.save()
                messages.success(request, f'{user.username} has been deactivated.')
                
            elif action == 'activate':
                user.is_active = True
                user.save()
                messages.success(request, f'{user.username} has been activated.')
                
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    # Calculate statistics
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    admin_users = users.filter(is_staff=True).count()
    inactive_users = users.filter(is_active=False).count()
    
    context = {
        'users': users,
        'total_users': total_users,
        'active_users': active_users,
        'admin_users': admin_users,
        'inactive_users': inactive_users,
    }
    
    return render(request, 'admin/manage_users.html', context)

@login_required
@staff_member_required
def lazypaste_system_stats(request):
    """Detailed system statistics and reports"""
    
    # Comprehensive statistics with robustness in calculation
    stats = {
        'claims': {
            'total': Claim.objects.count(),
            'by_status': dict(Claim.objects.values_list('status').annotate(Count('status'))),
            'by_insurer': dict(Claim.objects.values_list('insurer').annotate(Count('insurer'))[:10]),
            'flagged': Claim.objects.filter(is_flagged=True).count(),
        },
        'financial': {
            'total_billed': Claim.objects.aggregate(Sum('billed_amount'))['billed_amount__sum'] or 0,
            'total_paid': Claim.objects.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0,
            'avg_claim_amount': Claim.objects.aggregate(Avg('billed_amount'))['billed_amount__avg'] or 0,
        },
        'users': {
            'total': User.objects.count(),
            'admins': User.objects.filter(is_staff=True).count(),
            'active': User.objects.filter(is_active=True).count(),
        },
        'activity': {
            'total_notes': ClaimNote.objects.count(),
            'notes_by_type': dict(ClaimNote.objects.values_list('note_type').annotate(Count('note_type'))),
        }
    }
    
    return render(request, 'admin/system_stats.html', {'stats': stats})

