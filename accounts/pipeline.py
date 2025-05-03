import re
from social_core.pipeline.user import get_username
from django.core.exceptions import ValidationError
from social_core.exceptions import AuthForbidden
from .models import Profile
from django.contrib.auth import login
from django.shortcuts import render, redirect
from .utils import generate_random_password, send_temp_password_email
from django.contrib import messages
from social_core.pipeline.user import get_username

def validate_student_email(strategy, details, backend, user=None, *args, **kwargs):
    email = details.get('email')
    pattern = r'^[a-zA-Z0-9_.+-]+\@students.[a-zA-Z]+\.ac\.ke$'
    
    if not email or not re.fullmatch(pattern, email):
        request = strategy.request if hasattr(strategy, 'request') else None
        if request:
            messages.error(
                request,
                'You must sign up with a valid Kenyan student email in the format: [yourname]@students.[school].ac.ke'
            )
            request.session.save()
            return redirect('register')
        raise AuthForbidden(backend, 'Invalid student email format')

def send_verification_email(strategy, details, backend, user=None, *args, **kwargs):
    if user and not user.is_verified and backend.name != 'google-oauth2':
        send_verification_email(user)
    return None

def create_profile(strategy, details, backend, user=None, *args, **kwargs):
    if user and not hasattr(user, 'profile'):
        Profile.objects.create(user=user)
    return None

def force_password_set(strategy, backend, user, response, *args, **kwargs):
    """Mark social auth users who need to set a password."""
    if user is None:
        return None
    
    if kwargs.get('is_new', False) and not user.has_usable_password():
        strategy.session_set('force_password_set', True)
        strategy.session_set('social_auth_force_password_set', True)
        if hasattr(strategy, 'session'):
            strategy.session.save()
    return None

def create_profile(strategy, details, backend, user=None, *args, **kwargs):
    if user and not hasattr(user, 'profile'):
        Profile.objects.create(user=user)
    return None

def set_temporary_password(strategy, details, backend, user=None, *args, **kwargs):
    """Set a temporary password for new social auth users."""
    if backend.name == 'google-oauth2' and kwargs.get('is_new', False):
        temp_password = generate_random_password()
        user.set_password(temp_password)
        user.temp_password = temp_password 
        user.password_changed = False 
        user.save()
        
        # Store whether email was sent successfully
        email_sent = send_temp_password_email(user, temp_password)
        strategy.session_set('temp_email_sent', email_sent)
        
        strategy.session_set('force_password_set', True)
        strategy.session_set('is_temp_password', True)
    return None

def check_temp_password_on_login(strategy, user, response, *args, **kwargs):
    """Check if user is logging in with temp password."""
    request = strategy.request
    if request.method == 'POST' and 'password' in request.POST:
        if hasattr(user, 'temp_password') and user.check_password(request.POST['password']):
            request.session['force_password_set'] = True
            request.session['used_temp_password'] = True
    return None

def redirect_to_password_set(strategy, backend, user, response, *args, **kwargs):
    """Redirect to password set page if needed."""
    if strategy.session_get('force_password_set'):
        if not strategy.session_get('oauth_success'):
            return redirect('set_password')
    return None