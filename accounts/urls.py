from django.urls import path, include
from . import views
from .views import CustomLogoutView

urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('set-password/', views.set_password_view, name='set_password'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', CustomLogoutView.as_view(next_page='home'), name='logout'),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('verify-email/<uuid:token>/', views.verify_email_view, name='verify-email'),
    path('change-username/', views.change_username, name='change_username'),
    path('update-dp/', views.update_profile_pic, name='update_profile_pic'),
    path('oauth/complete/google-oauth2/', views.auth_complete, {'backend': 'google-oauth2'}, name='complete'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('profile/<str:username>/', views.view_profile, name='view_profile'),
]
