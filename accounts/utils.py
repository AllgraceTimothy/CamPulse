from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import EmailMessage
import logging
import secrets
import string
from django.contrib import messages

logger = logging.getLogger(__name__)

def generate_random_password(length=12):
    alphabet = string.ascii_letters + string.digits
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)) and \
           (any(c.isupper() for c in password)) and \
           (any(c.isdigit() for c in password)):
            return password
        
def send_temp_password_email(user, password):
    try:
        subject = 'Your Temporary Password your CamPulse Account'
        
        html_message = render_to_string('accounts/temp_password_email.html', {
            'user': user,
            'password': password,
            'login_url': f"{settings.SITE_URL}/login/",
            'set_password_url': f"{settings.SITE_URL}/set-password/",
        })
        
        email = EmailMessage(
            subject,
            html_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        email.content_subtype = "html"
        email.send()
        
        logger.info(f"Temporary password email sent to {user.email}")

        return True
    except Exception as e:
        logger.error(f"Failed to send temporary password email to {user.email}: {str(e)}")
        return False

def send_verification_email(user):
    try:
        subject = 'Verify Your CamPulse Account'
        verification_link = f"{settings.SITE_URL}/verify-email/{user.verification_token}/"
        
        html_message = render_to_string('accounts/verification_email.html', {
            'user': user,
            'verification_link': verification_link,
        })
        
        email = EmailMessage(
            subject,
            html_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        email.content_subtype = "html"  # Main content is now text/html
        email.send()
        
        logger.info(f"Verification email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        return False