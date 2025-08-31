from django.urls import path
from . import admin_views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', admin_views.lazypaste_admin_dashboard, name='dashboard'),
    path('csv-upload/', admin_views.lazypaste_csv_upload, name='csv_upload'),  
    path('process-csv/', admin_views.lazypaste_process_csv, name='process_csv'),
    path('manage-users/', admin_views.lazypaste_manage_users, name='manage_users'),
    path('system-stats/', admin_views.lazypaste_system_stats, name='system_stats'),
    
   
]