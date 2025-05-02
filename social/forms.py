from django import forms
from .models import Post

class PostForm(forms.ModelForm):
  class Meta:
    model = Post
    fields = ['content', 'image', 'video']
    widgets = {
      'content': forms.Textarea(attrs={
        'class': 'w-full p-2 rounded bg-secondary text-white',
        'placeholder': "What's on your mind",
      }),
    }