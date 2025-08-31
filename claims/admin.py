from django.contrib import admin
from .models import Claim, ClaimNote, UserProfile

# Register UserProfile as a standalone model
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Profile Details', {
            'fields': ('profile_picture', 'bio', 'phone_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_id', 'patient_name', 'status', 'insurer', 'billed_amount', 'paid_amount', 'is_flagged']
    list_filter = ['status', 'insurer', 'is_flagged']
    search_fields = ['claim_id', 'patient_name', 'insurer']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ClaimNote)
class ClaimNoteAdmin(admin.ModelAdmin):
    list_display = ['get_display_name', 'content', 'claim', 'created_at']
    list_filter = ['note_type', 'created_at']
