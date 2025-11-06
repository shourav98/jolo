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
    document_file = models.URLField(null=True, blank=True)  # Store Cloudinary URL
    document_public_id = models.CharField(max_length=255, null=True, blank=True)  # Store Cloudinary public ID

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
    last_seen = models.DateTimeField(default=timezone.now)  # For more granular tracking
    
    # Add these methods for better online status management
    def update_online_status(self):
        """Update online status based on last activity"""
        time_since_last_activity = timezone.now() - self.last_seen
        self.is_online = time_since_last_activity < timedelta(minutes=5)  # 5 minutes threshold
        self.save(update_fields=['is_online'])
    
    def mark_online(self):
        """Mark user as currently online"""
        self.is_online = True
        self.last_seen = timezone.now()
        self.last_online = timezone.now()
        self.save(update_fields=['is_online', 'last_seen', 'last_online'])
    
    def mark_offline(self):
        """Mark user as offline"""
        self.is_online = False
        self.last_online = timezone.now()
        self.save(update_fields=['is_online', 'last_online'])
    
    def get_status_display(self):
        """Get user status for display"""
        if self.is_online:
            return "Online"
        
        time_diff = timezone.now() - self.last_online
        if time_diff < timedelta(minutes=1):
            return "Just now"
        elif time_diff < timedelta(hours=1):
            return f"{int(time_diff.seconds / 60)} min ago"
        elif time_diff < timedelta(days=1):
            return f"{int(time_diff.seconds / 3600)} hours ago"
        else:
            return f"{time_diff.days} days ago"

    def __str__(self):
        return f"{self.user.name} - {'Online' if self.is_online else 'Offline'}"