from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from .forms import UserRegisterForm, ProfileForm, UsernameChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LogoutView
from .models import User, Profile
from .utils import send_verification_email, generate_random_password
from django.utils import timezone
from datetime import timedelta
from social.models import Post
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from social_django.models import UserSocialAuth
from django.contrib.auth.forms import SetPasswordForm
from django.conf import settings
from social_django.utils import load_strategy
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site

def home_view(request):
  posts = Post.objects.all().order_by('-created_at')
  return render(request, 'accounts/home.html', {'posts': posts})

def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            
            # Create a profile for the new user
            Profile.objects.get_or_create(user=user)
            
            # Send verification email
            send_verification_email(user)
            
            messages.success(request, 'Registration successful! Please check your email to verify your account.')
            return redirect('login')

    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def verify_email_view(request, token):
    try:
        user = User.objects.get(verification_token=token)
        
        if timezone.now() > user.token_created_at + timedelta(hours=24):
            messages.error(request, 'Verification link has expired. Please request a new one.')
            return redirect('login')
            
        user.is_verified = True
        user.is_active = True
        user.save()
        
        messages.success(request, 'Email verified successfully! You can now log in.')
        return redirect('login')
    except User.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('login')
    
def auth_complete(request, backend):
    """Handle Google OAuth completion."""
    try:
        user = request.backend.do_auth(
            request.backend.strategy.request_data(),
            request=request
        )
        
        if user:
            login(request, user, backend='social_core.backends.google.GoogleOAuth2')
            
            if request.session.get('force_password_set'):
                return redirect('set_password')
            
            if request.session.get('temp_email_sent'):
                request.session['oauth_success'] = True
                request.session.pop('temp_email_sent', None)
                request.session.modified = True
            return redirect('login')
            
    except Exception as e:
        messages.error(request, f"Authentication error: {str(e)}")
    return redirect('login')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    oauth_success = request.session.pop('oauth_success', False)
    
    if not oauth_success and request.session.get('temp_email_sent'):
        oauth_success = True
        request.session.pop('temp_email_sent', None)
    
    print(f"Login View - Final oauth_success: {oauth_success}")  # Debug
        
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user:
            if user.is_verified:
                social_auth = UserSocialAuth.objects.filter(user=user).exists()
                
                if social_auth and not user.has_changed_temp_password():
                    login(request, user)
                    request.session['force_password_set'] = True
                    messages.info(request, 'Please set a new password for your account.')
                    return redirect('set_password')
                
                login(request, user)
                messages.success(request, 'Logged in successfully!')
                return redirect('home')
            else:
                messages.error(request, 'Your account is not verified. Please check your email.')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'accounts/login.html', {'oauth_success': oauth_success})

@login_required
def set_password_view(request):
    if not (request.session.get('force_password_set', False)) and \
       not (hasattr(request.user, 'temp_password') and \
       not getattr(request.user, 'password_changed', True)):
        return redirect('dashboard')
    
    context = {}
    redirect_target = 'dashboard'
    
    if hasattr(request.user, 'temp_password') and not request.user.password_changed:
        context['password_set_reason'] = 'password_reset'
        redirect_target = 'home'
    elif request.session.get('social_auth_force_password_set', False):
        context['password_set_reason'] = 'google_signup'
        request.session.pop('social_auth_force_password_set', None)
        redirect_target = 'dashboard'
    else:
        context['password_set_reason'] = 'other'
        redirect_target = 'home'


    if request.method == 'POST':
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            if hasattr(user, 'temp_password'):
                user.temp_password = None
            user.password_changed = True
            user.save()
            
            update_session_auth_hash(request, user)
            request.session.pop('force_password_set', None)
            messages.success(request, 'Password set successfully!')
            return redirect(redirect_target)
    else:
        form = SetPasswordForm(request.user)
    
    context['form'] = form
    return render(request, 'accounts/set_password.html', context)

@login_required
def dashboard_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('dashboard')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'accounts/dashboard.html', {'form': form, 'profile': profile})

@login_required
def change_username(request):
    if request.method == 'POST':
        form = UsernameChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Your username has been updated successfully!')
            return redirect('dashboard')
        else:
            for error in form.errors.get('username', []):
                messages.error(request, error)
    
    return redirect('dashboard')

@login_required
@require_POST
def update_profile_pic(request):
    profile = request.user.profile
    if 'profile_pic' in request.FILES:
        profile.profile_pic = request.FILES['profile_pic']
        profile.save()
        messages.success(request, 'Profile picture updated successfully!')
        return JsonResponse({
            'success': True,
            'url': profile.profile_pic.url
        })
    else:
        messages.error(request, 'Failed to update profile picture')
    return JsonResponse({'success': False}, status=400)

def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)

            temp_passwd = generate_random_password()
            user.set_password(temp_passwd)
            user.temp_password = temp_passwd
            user.password_changed = False
            user.save()

            subject = 'Password Reset Request'
            html_message = render_to_string('accounts/password_reset_email.html', {
                'user': user,
                'temp_password': temp_passwd,
                'domain': get_current_site(request).domain,
            })
            plain_message = strip_tags(html_message)
            send_mail(subject, plain_message, None, [user.email], html_message=html_message)
            
            messages.success(request, 'An email with temporary credentials has been sent to your email address.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email address.')
    
    return render(request, 'accounts/password_reset_request.html')

class CustomLogoutView(LogoutView):
  def dispatch(self, request, *args, **kwargs):
    messages.success(request, "You have been logged out successfully.")
    return super().dispatch(request, *args, **kwargs)