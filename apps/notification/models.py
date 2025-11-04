from django.db import models
from django.utils import timezone
from apps.account.models import CustomUser


class Notification(models.Model):
    TYPE_CHOICES = [
        ('monetization_approved', 'Monetization Approved'),
        ('tip_received', 'Tip Received'),
        ('unlock_feed', 'Feed Unlocked'),
        ('like_received', 'Like Received'),
        ('comment_received', 'Comment Received'),
        ('follow_received', 'New Follower'),
        ('token_received', 'Token Received'),
        ('payout_processed', 'Payout Processed'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    related_event_id = models.CharField(max_length=100, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} → {self.title}"
