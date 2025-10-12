from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.account.models import UserProfile  

STATUS_CHOICES = (
    ('public', 'Public'),
    ('private', 'Private'),
    ('friends', 'Friends'),
)


class Feed(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='feeds')
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='public')
    total_like = models.PositiveIntegerField(default=0)
    total_unlike = models.PositiveIntegerField(default=0)
    total_comment = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.profile.user.name} - {self.content[:30]}"


class FeedFile(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='feed/files/')
    created_at = models.DateTimeField(auto_now_add=True)


class FeedVideo(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='videos')
    file = models.FileField(upload_to='feed/videos/')
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    total_like = models.PositiveIntegerField(default=0)
    total_unlike = models.PositiveIntegerField(default=0)
    total_comment = models.PositiveIntegerField(default=0)
    total_view = models.PositiveIntegerField(default=0)
    total_earn = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Video by {self.profile.user.name}"


class Comment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    comment_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.comment_by.user.name}"


class Like(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    liked_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Unlike(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    unliked_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Story(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='stories')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Story by {self.profile.user.name}"


class StoryItem(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='items')
    file = models.FileField(upload_to='stories/')
    expired_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    total_view = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class CreatorProfile(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    start_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=50, default='active')

    def __str__(self):
        return f"{self.profile.user.name}'s CreatorProfile"


class TopFan(models.Model):
    iam = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='topfans')
    fan_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='fan_of')
    status = models.CharField(max_length=50, default='active')


class Transaction(models.Model):
    TYPE_CHOICES = (
        ('tip', 'Tip'),
        ('gift', 'Gift'),
    )
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.user.name} - {self.type} - {self.amount}"


#  — Announcement model (for updates/promos/featured hosts)
class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to="announcements/", blank=True, null=True)
    video = models.FileField(upload_to="announcements/videos/", blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_featured", "-created_at"]

    def __str__(self):
        return self.title
