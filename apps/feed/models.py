from django.db import models
from apps.account.models import CustomUser  

class Feed(models.Model):
    profile = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    # timesince = models.DateTimeField(auto_now_add=True)
    total_like = models.IntegerField(default=0)
    total_unlike = models.IntegerField(default=0)
    total_comment = models.IntegerField(default=0)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class FeedFile(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    file = models.FileField(upload_to='feed_files/')

class FeedVideo(models.Model):
    profile = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    file = models.FileField(upload_to='feed_videos/')
    title = models.CharField(max_length=255)
    description = models.TextField()
    total_like = models.IntegerField(default=0)
    total_unlike = models.IntegerField(default=0)
    total_comment = models.IntegerField(default=0)
    total_view = models.IntegerField(default=0)
    total_earn = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
    content_type_id = models.IntegerField()
    comment_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Like(models.Model):
    content_type_id = models.IntegerField()
    liked_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Unlike(models.Model):
    content_type_id = models.IntegerField()
    unliked_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Story(models.Model):
    profile = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class StoryItem(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE)
    file = models.FileField(upload_to='story_items/')
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    total_view = models.IntegerField(default=0)