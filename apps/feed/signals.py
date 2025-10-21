from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from apps.feed.models import (
    Feed, Like, Comment, Unlock, FeedTip, TopFan,StoryItem
)

# helper: add or update fan score
def update_topfan(creator, fan, points: int):
    if creator == fan:
        return
    obj, created = TopFan.objects.get_or_create(
        creator=creator,
        fan=fan,
        defaults={"score": points, "status": "active"},
    )
    if not created:
        obj.score += points
        obj.last_interacted = timezone.now()
        obj.save(update_fields=["score", "last_interacted"])



# LIKE SIGNALS

@receiver(post_save, sender=Like)
def add_like(sender, instance, created, **kwargs):
    if created:
        feed = instance.content_object
        if isinstance(feed, Feed):
            feed.total_like += 1
            feed.save(update_fields=["total_like"])
            update_topfan(feed.profile, instance.liked_by, 2)

@receiver(post_delete, sender=Like)
def remove_like(sender, instance, **kwargs):
    feed = instance.content_object
    if isinstance(feed, Feed) and feed.total_like > 0:
        feed.total_like -= 1
        feed.save(update_fields=["total_like"])



# COMMENT SIGNALS

@receiver(post_save, sender=Comment)
def add_comment(sender, instance, created, **kwargs):
    if created:
        feed = instance.content_object
        if isinstance(feed, Feed):
            feed.total_comment += 1
            feed.save(update_fields=["total_comment"])
            update_topfan(feed.profile, instance.comment_by, 3)

@receiver(post_delete, sender=Comment)
def remove_comment(sender, instance, **kwargs):
    feed = instance.content_object
    if isinstance(feed, Feed) and feed.total_comment > 0:
        feed.total_comment -= 1
        feed.save(update_fields=["total_comment"])



# UNLOCK SIGNALS

@receiver(post_save, sender=Unlock)
def add_unlock(sender, instance, created, **kwargs):
    if created:
        feed = instance.feed
        feed.total_view += 1
        feed.save(update_fields=["total_view"])
        update_topfan(feed.profile, instance.fan, 5)



# TIP SIGNALS

@receiver(post_save, sender=FeedTip)
def add_tip(sender, instance, created, **kwargs):
    if created:
        update_topfan(instance.receiver, instance.sender, 5)


#Story

@receiver(post_save, sender=StoryItem)
def auto_set_expiry(sender, instance, created, **kwargs):
    
    if created and not instance.expired_at:
        instance.expired_at = timezone.now() + timedelta(hours=24)
        instance.save(update_fields=["expired_at"])
