# claims/auth_urls.py
from django.urls import path
from . import auth_views

app_name = 'auth'

urlpatterns = [
    path('login/', auth_views.lazypaste_login_view, name='login'),
    path('signup/', auth_views.lazypaste_signup_view, name='signup'),
    path('logout/', auth_views.lazypaste_logout_view, name='logout'),
    path('password-reset/', auth_views.lazypaste_password_reset_view, name='password_reset'),
    path('password-reset-done/', auth_views.lazypaste_password_reset_done_view, name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.lazypaste_password_reset_confirm_view, name='password_reset_confirm'),
]