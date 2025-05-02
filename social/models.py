from django.conf import settings
from django.db import models

class Post(models.Model):
  author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
  content = models.TextField(max_length=1000, blank=True)
  image = models.ImageField(upload_to='posts/images/', blank=True, null=True)
  video = models.FileField(upload_to='posts/videos/', blank=True, null=True)
  created_at = models.DateTimeField(auto_now_add=True)

  def total_likes(self):
    return self.likes.count()
  
  def total_comments(self):
    return self.comments.count()

  def __str__(self):
    return f"{self.author.username}'s Post at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class Like(models.Model):
  user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
  post = models.ForeignKey(Post, related_name='likes', on_delete=models.CASCADE)
  created_at = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
  user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
  post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
  content = models.TextField()
  created_at = models.DateTimeField(auto_now_add=True)