import os
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.shortcuts import render, redirect
import json
from django.template.loader import render_to_string
from decimal import Decimal
from django.utils import timezone
from .forms import UserProfileForm, ProfilePictureForm
from .models import UserProfile
from .models import Claim, ClaimNote
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required
def lazypaste_claims_list(request):
    """Main claims list view with search, filter, and pagination functionality"""
    claims = Claim.objects.all().order_by('claim_id')  # Order by claim ID ascending (30001, 30002, etc.)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        claims = claims.filter(
            Q(claim_id__icontains=search_query) |
            Q(patient_name__icontains=search_query) |
            Q(insurer__icontains=search_query) |
            Q(status__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        if status_filter == 'flagged':
            claims = claims.filter(is_flagged=True)
        else:
            claims = claims.filter(status=status_filter)
    
    # Pagination - 25 claims per page
    paginator = Paginator(claims, 25)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'claims': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Claim.STATUS_CHOICES,
        'is_paginated': paginator.num_pages > 1,
    }
    
    return render(request, 'claims/claims_list.html', context)

@login_required
def lazypaste_claim_detail(request, claim_id):
    """HTMX detail view for specific claim"""
    claim = get_object_or_404(Claim, claim_id=claim_id)
    notes = claim.notes.all()
    
    # Check if this is an HTMX request for partial update
    if request.headers.get('HX-Request'):
        return render(request, 'claims/claim_detail_partial.html', {
            'claim': claim,
            'notes': notes,
        })
    
    return render(request, 'claims/claim_detail.html', {
        'claim': claim,
        'notes': notes,
        'user': request.user, 
    })

@login_required
@csrf_exempt
def lazypaste_flag_claim(request, claim_id):
    """Toggle flag status for a claim"""
    if request.method == 'POST':
        claim = get_object_or_404(Claim, claim_id=claim_id)
        claim.is_flagged = not claim.is_flagged
        claim.save()
        
        # Return the updated button HTML for the modal
        if claim.is_flagged:
            button_html = f'''
                <button 
                    class="lazypaste-btn lazypaste-btn-danger lazypaste-action-btn"
                    hx-post="/api/flag/{claim.claim_id}/"
                    hx-target="#flag-button-container"
                    hx-swap="innerHTML"
                >
                    🚩 Remove Flag
                </button>
            '''
        else:
            button_html = f'''
                <button 
                    class="lazypaste-btn lazypaste-btn-outline lazypaste-action-btn"
                    hx-post="/api/flag/{claim.claim_id}/"
                    hx-target="#flag-button-container"
                    hx-swap="innerHTML"
                >
                    🏳️ Flag for Review
                </button>
            '''
        
        return HttpResponse(button_html)
    
    return JsonResponse({'success': False})

@login_required
@csrf_exempt
def lazypaste_add_note(request, claim_id):
    """Add a note to a claim"""
    if request.method == 'POST':
        claim = get_object_or_404(Claim, claim_id=claim_id)
        
        try:
            note_content = request.POST.get('content', '').strip()
            
            if note_content:
                note = ClaimNote.objects.create(
                claim=claim,
                content=note_content,
                note_type='admin' if request.user.is_staff else 'user',  # Auto-detect note type
                created_by=request.user
            )
                
                # Return rendered HTML 
                return render(request, 'claims/note_partial.html', {'note': note})
            
        except Exception as e:
            # Return error message as HTML
            return HttpResponse(f'<div class="alert alert-danger">Error: {str(e)}</div>')
    
    # Return empty response for invalid requests
    return HttpResponse('')

@login_required
def lazypaste_search_claims(request):
    """HTMX search endpoint for dynamic filtering with pagination"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    page_number = request.GET.get('page', 1)
    
    claims = Claim.objects.all().order_by('claim_id')  # Order by claim ID ascending
    
    if search_query:
        claims = claims.filter(
            Q(claim_id__icontains=search_query) |
            Q(patient_name__icontains=search_query) |
            Q(insurer__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'flagged':
            claims = claims.filter(is_flagged=True)
        else:
            claims = claims.filter(status=status_filter)
    
    # Pagination for HTMX requests
    paginator = Paginator(claims, 25)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'claims': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search_query': search_query,
        'status_filter': status_filter,
        'is_paginated': paginator.num_pages > 1,
    }
    
    # Return the full table section for HTMX replacement
    return render(request, 'claims/claims_table_partial.html', context)

@login_required
def lazypaste_generate_report(request, claim_id):
    """Generate individual claim report"""
    claim = get_object_or_404(Claim, claim_id=claim_id)
    notes = claim.notes.all().order_by('created_at')
    
    # Calculate financial metrics
    underpayment = claim.billed_amount - claim.paid_amount
    underpayment_percentage = 0
    if claim.billed_amount > 0:
        underpayment_percentage = (underpayment / claim.billed_amount) * 100
    
    # Parse CPT codes
    cpt_codes_list = []
    if claim.cpt_codes:
        codes = claim.cpt_codes.split(',')
        cpt_codes_list = [code.strip() for code in codes if code.strip()]
    
    context = {
        'claim': claim,
        'notes': notes,
        'underpayment': underpayment,
        'underpayment_percentage': underpayment_percentage,
        'cpt_codes_list': cpt_codes_list,
        'generated_by': request.user.get_full_name() or request.user.username,
        'generation_date': timezone.now(),
    }
    
    # Check if user wants PDF or HTML
    format_type = request.GET.get('format', 'html')
    
    if format_type == 'pdf':
        # return HTML that can be printed
        html_content = render_to_string('claims/claim_report.html', context, request)
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'inline; filename="claim_{claim.claim_id}_report.html"'
        return response
    else:
        # Return HTML view
        return render(request, 'claims/claim_report.html', context)
    


@login_required
def profile_view(request):
    """Display and edit user profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile, user=request.user)
        
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, 'Profile updated successfully!')
            return redirect('claims:profile')
    else:
        form = UserProfileForm(instance=profile, user=request.user)
    
    context = {
        'form': form,
        'profile': profile,
        'user': request.user
    }
    
    return render(request, 'claims/profile.html', context)

@login_required
def upload_profile_picture(request):
    """AJAX upload for profile picture"""
    if request.method == 'POST':
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        form = ProfilePictureForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'picture_url': profile.get_profile_picture_url(),
                'message': 'Profile picture updated successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


