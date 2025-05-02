from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Profile
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.core.validators import RegexValidator
import re

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_.+-]+\@students.[a-zA-Z]+\.ac\.ke$',
                message='Please use a valid Kenyan student email in the format: [yourname]@students.[school].ac.ke'
            )
        ]
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['course', 'year_of_study', 'bio', 'profile_pic', 'instagram', 'linkedin']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

class UsernameChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ['username']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = None  # Remove default help text
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter new username'
        })
    def clean_username(self):
        username = self.cleaned_data['username']
        
        # Add your custom validation rules
        if len(username) < 4:
            raise ValidationError("Username must be at least 4 characters long.")
            
        if not re.match(r'^[\w.@+-]+$', username):
            raise ValidationError("Username can only contain letters, numbers, and @/./+/-/_ characters.")
            
        if User.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
            raise ValidationError("This username is already taken.")
            
        return username