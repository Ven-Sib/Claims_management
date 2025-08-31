# claims/auth_views.py
import re
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

def validate_password_strength(password):
    """Validate password meets modern security requirements"""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter.")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter.")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number.")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>).")
    
    return errors

def lazypaste_login_view(request):
    """Login view with robustness in authentication handling"""
    if request.user.is_authenticated:
        return redirect('claims:claims_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                next_url = request.GET.get('next', 'claims:claims_list')
                return redirect(next_url)
            else:
                messages.error(request, 'Your account has been deactivated. Contact administrator.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'auth/login.html')

def lazypaste_signup_view(request):
    """Signup view with enhanced password validation"""
    if request.user.is_authenticated:
        return redirect('claims:claims_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Enhanced validation with robustness checks
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
        else:
            # Validate password strength
            password_errors = validate_password_strength(password1)
            if password_errors:
                for error in password_errors:
                    messages.error(request, error)
            else:
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1
                )
                messages.success(request, 'Account created successfully! Please log in.')
                return redirect('auth:login')
    
    return render(request, 'auth/signup.html')

def lazypaste_logout_view(request):
    """Logout view with redirect"""
    logout(request)
    messages.success(request, 'Successfully logged out.')
    return redirect('auth:login')

def lazypaste_password_reset_view(request):
    """Password reset request view"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build reset URL
            current_site = get_current_site(request)
            reset_url = f"http://{current_site.domain}/auth/password-reset-confirm/{uid}/{token}/"
            
            # Email content
            subject = 'Password Reset - Claims Management System'
            message = render_to_string('auth/password_reset_email.html', {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'Claims Management System'
            })
            
            # Send email
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
                html_message=message
            )
            
            messages.success(request, 'Password reset instructions have been sent to your email address.')
            return redirect('auth:password_reset_done')
            
        except User.DoesNotExist:
            messages.error(request, 'No user found with this email address.')
    
    return render(request, 'auth/password_reset.html')

def lazypaste_password_reset_done_view(request):
    """Password reset email sent confirmation"""
    return render(request, 'auth/password_reset_done.html')

def lazypaste_password_reset_confirm_view(request, uidb64, token):
    """Password reset confirmation view"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            
            if password1 != password2:
                messages.error(request, 'Passwords do not match.')
            else:
                # Validate password strength
                password_errors = validate_password_strength(password1)
                if password_errors:
                    for error in password_errors:
                        messages.error(request, error)
                else:
                    # Set new password
                    user.set_password(password1)
                    user.save()
                    messages.success(request, 'Your password has been reset successfully! Please log in.')
                    return redirect('auth:login')
        
        return render(request, 'auth/password_reset_confirm.html', {
            'validlink': True,
            'user': user
        })
    else:
        return render(request, 'auth/password_reset_confirm.html', {
            'validlink': False
        })