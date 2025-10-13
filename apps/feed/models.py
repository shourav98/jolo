from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.account.models import UserProfile



#  FEED & SOCIAL CONTENT


STATUS_CHOICES = (
    ("public", "Public"),
    ("private", "Private"),
    ("friends", "Friends"),
)


class Feed(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="feeds")
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="public")
    total_like = models.PositiveIntegerField(default=0)
    total_comment = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.profile.user.name} - {self.content[:30]}"


class FeedFile(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="feed/files/%Y/%m/%d/")
    created_at = models.DateTimeField(auto_now_add=True)


class FeedVideo(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="videos")
    file = models.FileField(upload_to="feed/videos/%Y/%m/%d/")
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    total_like = models.PositiveIntegerField(default=0)
    total_comment = models.PositiveIntegerField(default=0)
    total_view = models.PositiveIntegerField(default=0)
    total_earn = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Video by {self.profile.user.name}"



#  COMMENTS / LIKES


class Comment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    comment_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.comment_by.user.name}"


class CommentLike(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    liked_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Like(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    liked_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Unlike(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    unliked_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)




#  STORIES


class Story(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="stories")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Story by {self.profile.user.name}"


class StoryItem(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="items")
    file = models.FileField(upload_to="stories/%Y/%m/%d/")
    expired_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    total_view = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expired_at if self.expired_at else False



#  SOCIAL RELATIONSHIPS


class Follow(models.Model):
    follower = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")

    def __str__(self):
        return f"{self.follower.user.name} → {self.following.user.name}"



#  CREATOR & TRANSACTIONS


class CreatorProfile(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="creator_profile")
    start_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=50, default="active")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.profile.is_creator = True
        self.profile.save()

    def __str__(self):
        return f"{self.profile.user.name}'s Creator Profile"


class Wallet(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.profile.user.name} Wallet - {self.balance}"


class Transaction(models.Model):
    TYPE_CHOICES = (
        ('tip', 'Tip'),
        ('gift', 'Gift'),
    )
    sender = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name='sent_transactions'
    )
    receiver = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name='received_transactions'
    )
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.user.name} → {self.receiver.user.name} ({self.type})"



class VideoTip(models.Model):
    video = models.ForeignKey(FeedVideo, on_delete=models.CASCADE, related_name="tips")
    sender = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class TopFan(models.Model):
    iam = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="topfans")
    fan_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="fan_of")
    status = models.CharField(max_length=50, default="active")

    def __str__(self):
        return f"{self.fan_profile.user.name} is top fan of {self.iam.user.name}"



#  ANNOUNCEMENTS


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

 #Top Fans

class TopFan(models.Model):
    iam = models.ForeignKey(
        'account.UserProfile', on_delete=models.CASCADE, related_name='topfans'
    )  # Creator
    fan_profile = models.ForeignKey(
        'account.UserProfile', on_delete=models.CASCADE, related_name='fan_of'
    )  # Fan
    score = models.PositiveIntegerField(default=0)
    last_interacted = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=50, default='active')

    class Meta:
        unique_together = ('iam', 'fan_profile')
        ordering = ['-score', '-last_interacted']

    def __str__(self):
        return f"{self.fan_profile.user.name} → {self.iam.user.name} ({self.score})"
