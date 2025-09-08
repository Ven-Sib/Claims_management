from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image
import os

from django.core.files.storage import default_storage

class Claim(models.Model):
    # Status choices based on the challenge example
    STATUS_CHOICES = [
        ('denied', 'Denied'),
        ('paid', 'Paid'), 
        ('under_review', 'Under Review'),
    ]
    
    claim_id = models.CharField(max_length=20, unique=True)  
    patient_name = models.CharField(max_length=200)  
    billed_amount = models.DecimalField(max_digits=12, decimal_places=2) 
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    insurer = models.CharField(max_length=200) 
    discharge_date = models.DateField()
    
    # CPT codes as a simple text field 
    cpt_codes = models.TextField(help_text="Comma-separated CPT codes")
    denial_reason = models.TextField(blank=True, null=True)
    
    # Tracking flags
    is_flagged = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Claim {self.claim_id} - {self.patient_name}"
    
    class Meta:
        ordering = ['created_at']

class ClaimNote(models.Model):
    NOTE_TYPES = [
        ('admin', 'Admin Note'),
        ('system', 'System Flag'),
        ('user', 'User Note'),
    ]
    
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='notes')
    note_type = models.CharField(max_length=10, choices=NOTE_TYPES, default='user')
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_display_name(self):
        """Custom display for admin panel"""
        if self.note_type == 'admin':
            return 'Admin Note'
        elif self.note_type == 'system':
            return 'System Flag'
        elif self.created_by:
            return self.created_by.username
        else:
            return 'User Note'
    
    def __str__(self):
        return f"{self.get_display_name()} for Claim {self.claim.claim_id}"
    
    class Meta:
        ordering = ['-created_at']

def user_profile_picture_path(instance, filename):
    """Generate upload path for user profile pictures"""
    # Get file extension
    ext = filename.split('.')[-1]
    # Create filename: user_id.extension
    filename = f'user_{instance.user.id}.{ext}'
    return os.path.join('profile_pictures/', filename)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path, 
        blank=True, 
        null=True,
        help_text="Profile picture (max 2MB, JPEG/PNG only)"
    )
    bio = models.TextField(max_length=500, blank=True, help_text="Brief bio or description")
    phone_number = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def save(self, *args, **kwargs):
        """Override save to resize profile picture with error handling"""
        super().save(*args, **kwargs)
        
        if self.profile_picture:
            img_path = self.profile_picture.path
            try:
                # Check if file exists before trying to process it
                if os.path.exists(img_path):
                    with Image.open(img_path) as img:
                        # Resize to 300x300 pixels
                        if img.height > 300 or img.width > 300:
                            output_size = (300, 300)
                            img.thumbnail(output_size, Image.Resampling.LANCZOS)
                            img.save(img_path, quality=85, optimize=True)
                else:
                    # File doesn't exist, clear the field to prevent future errors
                    self.profile_picture = None
                    super().save(update_fields=['profile_picture'])
            except Exception as e:
                # Any error with image processing, clear the field
                print(f"Error processing profile picture: {e}")
                self.profile_picture = None
                super().save(update_fields=['profile_picture'])
    
    def get_profile_picture_url(self):
        """Get profile picture URL or default avatar"""
        if self.profile_picture:
            return self.profile_picture.url
        else:
            # Return default avatar URL
            return '/static/images/homeie.jpeg'
    
    class Meta:
        ordering = ['-created_at']

# Signal to create UserProfile when User is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)  
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)
