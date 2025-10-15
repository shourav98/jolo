# models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='creator_sessions'
    )
    fan = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='fan_sessions'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    free_window_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['creator', 'fan']
    
    def __str__(self):
        return f"Chat: {self.creator.name} & {self.fan.name}"


class Message(models.Model):
    MESSAGE_TYPES = [
        ('normal', 'Normal'),
        ('priority', 'Priority Whisper'),
        ('auto_reply', 'Auto Reply'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) 
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='normal')
    tokens_used = models.IntegerField(default=0)
    translated_content = models.TextField(blank=True, null=True)
    original_language = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']


class MessageReaction(models.Model):
    REACTION_CHOICES = [
        ('❤️', 'Heart'),
        ('🔥', 'Fire'),
        ('😈', 'Smirk'),
    ]
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user']


class UserActivity(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity')
    last_online = models.DateTimeField(default=timezone.now)
    is_online = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.name} - {'Online' if self.is_online else 'Offline'}"