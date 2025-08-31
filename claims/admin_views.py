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
        'status_stats': status_stats,  # Now includes percentage field
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
    """Process uploaded CSV file(s) - treat all files equally"""
    if request.method != 'POST':
        return redirect('admin_dashboard:csv_upload')
    
    csv_file_1 = request.FILES.get('csv_file_1')
    csv_file_2 = request.FILES.get('csv_file_2')
    upload_mode = request.POST.get('upload_mode')  # 'overwrite' or 'append'
    
    # Validation: At least one file must be uploaded
    if not csv_file_1 and not csv_file_2:
        messages.error(request, 'Please select at least one CSV file.')
        return redirect('admin_dashboard:csv_upload')
    
    # Validation: Check file extensions
    if csv_file_1 and not csv_file_1.name.endswith('.csv'):
        messages.error(request, 'File 1 must be a valid CSV file.')
        return redirect('admin_dashboard:csv_upload')
    
    if csv_file_2 and not csv_file_2.name.endswith('.csv'):
        messages.error(request, 'File 2 must be a valid CSV file.')
        return redirect('admin_dashboard:csv_upload')
    
    try:
        total_result = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'deleted': 0,
            'error_details': []
        }
        
        # Handle overwrite mode - delete existing data before processing any files
        if upload_mode == 'overwrite':
            deleted_count = Claim.objects.count()
            Claim.objects.all().delete()
            total_result['deleted'] = deleted_count
        
        # Process first file
        if csv_file_1:
            file_name = default_storage.save(f'temp/{csv_file_1.name}', ContentFile(csv_file_1.read()))
            file_path = default_storage.path(file_name)
            
            result = load_csv_data(file_path)
            
            # Accumulate results
            total_result['created'] += result['created']
            total_result['updated'] += result['updated']
            total_result['errors'] += result['errors']
            total_result['error_details'].extend(result.get('error_details', []))
            
            default_storage.delete(file_name)
        
        # Process second file
        if csv_file_2:
            file_name = default_storage.save(f'temp/{csv_file_2.name}', ContentFile(csv_file_2.read()))
            file_path = default_storage.path(file_name)
            
            result = load_csv_data(file_path)
            
            # Accumulate results
            total_result['created'] += result['created']
            total_result['updated'] += result['updated']
            total_result['errors'] += result['errors']
            total_result['error_details'].extend(result.get('error_details', []))
            
            default_storage.delete(file_name)
        
        # Show results
        success_message = f"Upload completed! {total_result['created']} created, {total_result['updated']} updated"
        if total_result['deleted'] > 0:
            success_message += f", {total_result['deleted']} deleted"
        success_message += f", {total_result['errors']} errors."
        
        messages.success(request, success_message)
        return render(request, 'admin/csv_results.html', {'result': total_result})
        
    except Exception as e:
        messages.error(request, f'Error processing file: {str(e)}')
        return redirect('admin_dashboard:csv_upload')

def process_csv_overwrite(file_path):
    """Overwrite mode: Delete all existing claims, load fresh data"""
    # Delete all existing claims
    deleted_count = Claim.objects.count()
    Claim.objects.all().delete()
    
    # Load fresh data
    result = load_csv_data(file_path)
    result['deleted'] = deleted_count
    return result

def process_csv_append(file_path):
    """Append mode: Update existing, create new"""
    return load_csv_data(file_path)

def load_csv_data(file_path):
    """Unified CSV processing - preserves existing data, only fills N/A fields"""
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
        
        for row_num, row in enumerate(reader, 1):
            try:
                # Smart claim_id detection
                claim_id = str(row.get('claim_id', '') or row.get('id', '')).strip()
                
                if not claim_id:
                    errors.append(f"Row {row_num}: No claim ID found")
                    error_count += 1
                    continue
                
                # Check if claim exists
                try:
                    claim = Claim.objects.get(claim_id=claim_id)
                    # Claim exists - only update N/A fields
                    updated_fields = []
                    
                    if row.get('patient_name') and claim.patient_name == 'N/A':
                        claim.patient_name = row.get('patient_name').strip()
                        updated_fields.append('patient_name')
                    
                    if row.get('billed_amount') and claim.billed_amount == Decimal('0'):
                        try:
                            claim.billed_amount = Decimal(str(row.get('billed_amount')))
                            updated_fields.append('billed_amount')
                        except:
                            pass
                    
                    if row.get('paid_amount') and claim.paid_amount == Decimal('0'):
                        try:
                            claim.paid_amount = Decimal(str(row.get('paid_amount')))
                            updated_fields.append('paid_amount')
                        except:
                            pass
                    
                    if row.get('status') and claim.status == 'under_review':
                        claim.status = row.get('status').lower().replace(' ', '_')
                        updated_fields.append('status')
                    
                    if row.get('insurer_name') and claim.insurer == 'N/A':
                        claim.insurer = row.get('insurer_name').strip()
                        updated_fields.append('insurer')
                    
                    if row.get('cpt_codes') and claim.cpt_codes == 'N/A':
                        claim.cpt_codes = row.get('cpt_codes').strip()
                        updated_fields.append('cpt_codes')
                    
                    if row.get('denial_reason') and claim.denial_reason == 'N/A':
                        claim.denial_reason = row.get('denial_reason').strip()
                        updated_fields.append('denial_reason')
                    
                    if updated_fields:
                        claim.save()
                        updated_count += 1
                    
                except Claim.DoesNotExist:
                    # Create new claim with N/A for missing fields
                    defaults = {
                        'patient_name': row.get('patient_name', 'N/A').strip() if row.get('patient_name') else 'N/A',
                        'billed_amount': Decimal(str(row.get('billed_amount', '0'))) if row.get('billed_amount') else Decimal('0'),
                        'paid_amount': Decimal(str(row.get('paid_amount', '0'))) if row.get('paid_amount') else Decimal('0'),
                        'status': row.get('status', 'under_review').lower().replace(' ', '_') if row.get('status') else 'under_review',
                        'insurer': row.get('insurer_name', 'N/A').strip() if row.get('insurer_name') else 'N/A',
                        'discharge_date': parse_date(row.get('discharge_date', '')) or datetime.now().date(),
                        'cpt_codes': row.get('cpt_codes', 'N/A').strip() if row.get('cpt_codes') else 'N/A',
                        'denial_reason': row.get('denial_reason', 'N/A').strip() if row.get('denial_reason') else 'N/A',
                    }
                    
                    Claim.objects.create(claim_id=claim_id, **defaults)
                    created_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1
    
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

