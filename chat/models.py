from django.conf import settings
from django.db import models

class Chat(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chats'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    chat_hidden_for = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='deleted_chats',
        blank=True
    )

    def __str__(self):
        return f"Chat {self.id}"
    
    def get_other_participant(self, user):
        """Get the other participant in a 1-on-1 chat"""
        return self.participants.exclude(id=user.id).first()
    
    def has_messages(self):
        """Check if chat has any messages"""
        return self.messages.exists()

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    edited = models.BooleanField(default=False)
    text_hidden_for = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='deleted_messages',
        blank=True
    )
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='read_messages',
        blank=True
    )
    def mark_as_read(self, user):
        self.read_by.add(user)

    def __str__(self):
        return f"Message {self.id} from {self.sender.username}"
    
    def is_visible_to(self, user):
        """Check if message is visible to a user"""
        return not self.deleted_for.filter(id=user.id).exists()