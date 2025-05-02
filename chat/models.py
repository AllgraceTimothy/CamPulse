from django.conf import settings
from django.db import models

class Chat(models.Model):
  participants = models.ManyToManyField(
        getattr(settings, 'AUTH_USER_MODEL', 'accounts.User'),
        related_name='chats'
    )
  created_at = models.DateTimeField(auto_now_add=True)
  deleted_for = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='deleted_chats', blank=True)

  def __str__(self):
    return f"Chat {self.id}"
  
class Message(models.Model):
  chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
  sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
  content = models.TextField()
  timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
  edited = models.BooleanField(default=False)
  deleted_for_all = models.BooleanField(default=False)

  def __str__(self):
    return f"Message {self.id} from {self.sender.username}"
  
class MessageVisibility(models.Model):
  text = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='visibility')
  user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
  visible = models.BooleanField(default=True)

  class Meta:
    unique_together = ('text', 'user')

class HiddenChat(models.Model):
  chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
  user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
  hidden_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    unique_together = ('chat', 'user')