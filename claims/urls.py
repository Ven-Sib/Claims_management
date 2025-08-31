from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    path('', views.lazypaste_claims_list, name='claims_list'),  # Following naming convention from challenge
    path('claim/<str:claim_id>/', views.lazypaste_claim_detail, name='claim_detail'),
    path('api/flag/<str:claim_id>/', views.lazypaste_flag_claim, name='flag_claim'),
    path('api/add-note/<str:claim_id>/', views.lazypaste_add_note, name='add_note'),
    path('api/search/', views.lazypaste_search_claims, name='search_claims'),
    path('api/delete/<str:claim_id>/', views.lazypaste_delete_claim, name='delete_claim'), 
    path('api/bulk-delete/', views.lazypaste_bulk_delete_claims, name='bulk_delete'),   
    path('report/<str:claim_id>/', views.lazypaste_generate_report, name='generate_report'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/upload-picture/', views.upload_profile_picture, name='upload_picture'),
    
]