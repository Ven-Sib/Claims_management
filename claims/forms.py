from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile


class ProfilePictureForm(forms.ModelForm):
    """Form for uploading profile picture"""
    class Meta:
        model = UserProfile
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def clean_profile_picture(self):
        """Validate profile picture"""
        picture = self.cleaned_data.get('profile_picture')
        
        if picture:
            # Check file size (2MB limit)
            if picture.size > 2 * 1024 * 1024:
                raise ValidationError('Image file too large. Maximum size is 2MB.')
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
            if picture.content_type not in allowed_types:
                raise ValidationError('Invalid file type. Only JPEG and PNG images are allowed.')
        
        return picture

class UserProfileForm(forms.ModelForm):
    """Form for editing user profile information"""
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)
    
    class Meta:
        model = UserProfile
        fields = ['bio', 'phone_number']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 123-4567'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
        
        # Add Bootstrap classes
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def save(self, user=None):
        """Save profile and user information"""
        profile = super().save(commit=False)
        
        if user:
            # Update user fields
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            user.email = self.cleaned_data.get('email', '')
            user.save()
            
            profile.user = user
        
        profile.save()
        return profile