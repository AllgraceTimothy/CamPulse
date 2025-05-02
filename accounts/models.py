from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class User(AbstractUser):
    is_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    token_created_at = models.DateTimeField(default=timezone.now)
    
    previous_username = models.CharField(max_length=150, blank=True)
    username_changed = models.BooleanField(default=False)

    temp_password = models.CharField(max_length=128, blank=True, null=True)
    password_changed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.pk and 'username' in kwargs.get('update_fields', []):
            original_user = User.objects.get(pk=self.pk)
            if original_user.username != self.username:
                self.previous_username = original_user.username
                self.username_changed = True
        
        if hasattr(self, 'social_auth') or (self.pk and self.social_auth.exists()):
            self.is_verified = True
            
        super().save(*args, **kwargs)
        
        if self._state.adding:
            Profile.objects.get_or_create(user=self)

    def has_changed_temp_password(self):
        return self.password_changed or not self.temp_password

class Profile(models.Model):
  user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
  course = models.CharField(max_length=100)
  bio = models.TextField(blank=True)
  year_of_study = models.CharField(max_length=20, blank=True)
  profile_pic = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.png', blank=True)
  instagram = models.CharField(max_length=255, blank=True)
  linkedin = models.CharField(max_length=255, blank=True)

  def __str__(self):
    return f"{self.user.username}'s Profile"