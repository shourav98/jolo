from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from decimal import Decimal

from apps.account.models import UserProfile  


#
# Core choices / helpers

FEED_STATUS = (
    ("public", "Public"),
    ("followers", "Followers Only"),
    ("locked", "Locked Content"),
)



# Feed & Media

class Feed(models.Model):
    
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="feeds")
    content = models.TextField(blank=True, default="")  # caption / text
    status = models.CharField(max_length=16, choices=FEED_STATUS, default="public")

    # For locked content
    unlock_price = models.PositiveIntegerField(default=0, help_text="Coins required if status=locked")

    # Counters (kept hot via signals)
    total_like = models.PositiveIntegerField(default=0)
    total_comment = models.PositiveIntegerField(default=0)
    total_view = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["profile", "created_at"]),
        ]

    def __str__(self):
        return f"{self.profile.user.name} • {self.status} • #{self.id}"

    #  convenience helpers 
    @property
    def author(self):
        return self.profile.user

    def is_locked(self) -> bool:
        return self.status == "locked"

    def content_type(self):
        return ContentType.objects.get_for_model(Feed)

    # Visibility rules
    def is_visible_to(self, user) -> bool:
       
        if not user or not user.is_authenticated:
            return self.status == "public"

        if self.status == "public":
            return True

        viewer_profile = user.profile

        if self.profile_id == viewer_profile.id:
            return True  # author sees own post

        if self.status == "followers":
            return Follow.objects.filter(follower=viewer_profile, following=self.profile).exists()

        if self.status == "locked":
            return Unlock.objects.filter(fan=viewer_profile, feed=self).exists()

        return False

    def is_unlocked_for(self, user) -> bool:
        if not self.is_locked():
            return True
        if not user or not user.is_authenticated:
            return False
        vp = user.profile
        if vp.id == self.profile_id:
            return True
        return Unlock.objects.filter(fan=vp, feed=self).exists()


class FeedFile(models.Model):
    
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="feed/files/%Y/%m/%d/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"File for Feed #{self.feed_id}"
    



class FeedTip(models.Model):
    feed = models.ForeignKey("Feed", on_delete=models.CASCADE, related_name="tips", null=True, blank=True)
    sender = models.ForeignKey("account.UserProfile", on_delete=models.CASCADE, related_name="tips_sent")
    receiver = models.ForeignKey("account.UserProfile", on_delete=models.CASCADE, related_name="tips_received")
    amount = models.PositiveIntegerField()  # coins
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender.user.name} → {self.receiver.user.name} ({self.amount}c)"




# Social: Comments, Likes

class Comment(models.Model):
   
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    comment_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"Comment by {self.comment_by.user.name} on {self.content_type}#{self.object_id}"


class Like(models.Model):
   
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    liked_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("content_type", "object_id", "liked_by")
        ordering = ("-created_at",)

    def __str__(self):
        return f"Like by {self.liked_by.user.name} on {self.content_type}#{self.object_id}"


# Stories (ephemeral)

class Story(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="stories")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Story by {self.profile.user.name}"


class StoryItem(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="items")
    file = models.FileField(upload_to="stories/%Y/%m/%d/")
    expired_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"StoryItem #{self.id} of Story #{self.story_id}"

    def is_expired(self):
        return timezone.now() > self.expired_at if self.expired_at else True



# Social Graph (Follow)

class Follow(models.Model):
    follower = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("follower", "following")
        indexes = [models.Index(fields=["follower", "following"])]

    def __str__(self):
        return f"{self.follower.user.name} → {self.following.user.name}"



# Unlocks (paywall state)

class Unlock(models.Model):
    
    fan = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="unlocks")
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, related_name="unlocked_by")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("fan", "feed")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.fan.user.name} unlocked Feed #{self.feed_id}"



# Top Fan (engagement ranking)

class TopFan(models.Model):
   
    creator = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="fans")
    fan = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="topfans")
    score = models.PositiveIntegerField(default=0)
    last_interacted = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=32, default="active")

    class Meta:
        unique_together = ("creator", "fan")
        ordering = ("-score", "-last_interacted")
        indexes = [
            models.Index(fields=["creator", "-score", "-last_interacted"]),
        ]

    def __str__(self):
        return f"{self.fan.user.name} → {self.creator.user.name} ({self.score})"
