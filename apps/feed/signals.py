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
    if isinstance(feed, Feed):
        # Reduce like count safely
        if feed.total_like > 0:
            feed.total_like -= 1

        # Increase unlike count
        feed.total_unlike += 1

        feed.save(update_fields=["total_like", "total_unlike"])




# COMMENT SIGNALS

@receiver(post_save, sender=Comment)
def add_comment(sender, instance, created, **kwargs):
    if created:
        try:
            feed = instance.content_object
            if isinstance(feed, Feed):
                # Always recalc fresh count to avoid mismatch
                from django.contrib.contenttypes.models import ContentType
                ctype = ContentType.objects.get_for_model(Feed)
                count = Comment.objects.filter(
                    content_type=ctype, object_id=feed.id
                ).count()
                feed.total_comment = count
                feed.save(update_fields=["total_comment"])
                update_topfan(feed.profile, instance.comment_by, 3)
        except Exception as e:
            print(f"[Comment Signal Error: add_comment] {e}")


@receiver(post_delete, sender=Comment)
def remove_comment(sender, instance, **kwargs):
    try:
        feed = instance.content_object
        if isinstance(feed, Feed):
            from django.contrib.contenttypes.models import ContentType
            ctype = ContentType.objects.get_for_model(Feed)
            count = Comment.objects.filter(
                content_type=ctype, object_id=feed.id
            ).count()
            feed.total_comment = count
            feed.save(update_fields=["total_comment"])
    except Exception as e:
        print(f"[Comment Signal Error: remove_comment] {e}")




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


# =======================================
# FRIEND SUGGESTION SIGNALS
# =======================================

@receiver(post_save, sender=Like)
def update_scores_on_like(sender, instance, created, **kwargs):
    """Update interaction score when user likes content"""
    if created:
        feed = instance.content_object
        if isinstance(feed, Feed):
            from apps.feed.suggestion_engine import calculate_user_suggestion_score
            calculate_user_suggestion_score(instance.liked_by, feed.profile)


@receiver(post_save, sender=Comment)
def update_scores_on_comment(sender, instance, created, **kwargs):
    """Update interaction score when user comments"""
    if created:
        feed = instance.content_object
        if isinstance(feed, Feed):
            from apps.feed.suggestion_engine import calculate_user_suggestion_score
            calculate_user_suggestion_score(instance.comment_by, feed.profile)

# Handle Follows (remove from suggestions)
from apps.feed.models import Follow, UserInteractionScore

@receiver(post_save, sender=Follow)
def remove_suggestion_on_follow(sender, instance, created, **kwargs):
    """Remove user from suggestions when followed"""
    if created:
        # Delete suggestion score if it exists
        UserInteractionScore.objects.filter(
            user=instance.follower, 
            suggested_user=instance.following
        ).delete()

