from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid

from django.core.validators import FileExtensionValidator

from django.utils.timesince import timesince

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
    is_archived = models.BooleanField(default=False)

    class Meta:
        unique_together = ['creator', 'fan']

    def get_remaining_free_time(self):
        """Get remaining free time in seconds"""
        if not self.free_window_until or timezone.now() >= self.free_window_until:
            return 0
        return int((self.free_window_until - timezone.now()).total_seconds())

    def is_free_window_active(self):
        """Check if free window is currently active"""
        if not self.free_window_until:
            return False
        return timezone.now() < self.free_window_until

    def activate_free_window(self):
        """Activate 60-second free window after creator response"""
        self.free_window_until = timezone.now() + timedelta(seconds=60)
        self.save(update_fields=["free_window_until"])

    def get_chat_flow_status(self, user):
        """Get current chat flow status for a user"""
        is_first_message_in_chat = not self.messages.exists()
        is_first_message_from_user = not self.messages.filter(sender=user).exists()
        
        return {
            'is_first_message_in_chat': is_first_message_in_chat,
            'is_first_message_from_user': is_first_message_from_user,
            'free_window_active': self.is_free_window_active(),
            'free_window_remaining': self.get_remaining_free_time(),
            'user_role': 'creator' if user == self.creator else 'fan'
        }

    def __str__(self):
        return f"Chat: {self.creator.name} & {self.fan.name}"

class Message(models.Model):
    # MESSAGE_TYPES = [
    #     ('normal', 'Normal'),
    #     ('priority', 'Priority Whisper'),
    #     ('auto_reply', 'Auto Reply'),
    # ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,  # allow null
    blank=True
)
    content = models.TextField()
    # message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='normal')
    translated_content = models.TextField(blank=True, null=True)
    original_language = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    coins_used = models.IntegerField(default=0)  # New field for coins used
    document_file = models.FileField(upload_to='documents/', null=True, blank=True, validators=[FileExtensionValidator(['mp4', 'jpg', 'png', 'jpeg', 'gif', 'webp'])])

    class Meta:
        ordering = ['created_at']  # Add this line
    
    def __str__(self):
        return f"{self.sender}: {self.content[:20]}..."

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


    def get_last_seen_display(self):
        if self.is_online:
            return "Online"
        return f"Last seen {timesince(self.last_online)} ago"
    
    def __str__(self):
        return f"{self.user.name} - {'Online' if self.is_online else 'Offline'}"