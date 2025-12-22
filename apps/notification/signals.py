from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.notification.models import Notification

# Import models from all related apps
from apps.monetization.models import CreatorMonetization, PayoutRequest, SpendEvent
from apps.feed.models import FeedTip, Follow, Like, Comment, Unlock


# 1️⃣ Monetization Approved → Notify Creator
@receiver(post_save, sender=CreatorMonetization)
def notify_monetization_approved(sender, instance, **kwargs):
    if instance.status == "ACTIVE":
        Notification.objects.create(
            user=instance.user,
            title="Your monetization request has been approved!",
            type="monetization_approved"
        )


# 2️⃣ Tips → Creator gets token received notification
@receiver(post_save, sender=FeedTip)
def notify_tip_received(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.receiver.user,
            title=f"You received {instance.amount} coins from @{instance.sender.user.username}.",
            type="tip_received"
        )


# 3️⃣ Unlock Feed → Creator notified
@receiver(post_save, sender=Unlock)
def notify_unlock_feed(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.feed.profile.user,
            title=f"@{instance.fan.user.username} unlocked your post.",
            type="unlock_feed"
        )


# 4️⃣ Like Feed → Creator notified
@receiver(post_save, sender=Like)
def notify_like_received(sender, instance, created, **kwargs):
    if created:
        feed = getattr(instance.content_object, "feed", None)
        if hasattr(instance.content_object, "profile"):
            creator = instance.content_object.profile.user
            Notification.objects.create(
                user=creator,
                title=f"@{instance.liked_by.user.username} liked your post.",
                type="like_received"
            )


# 5️⃣ Comment → Creator notified
@receiver(post_save, sender=Comment)
def notify_comment_received(sender, instance, created, **kwargs):
    if created:
        if hasattr(instance.content_object, "profile"):
            # Feed comments
            creator = instance.content_object.profile.user
            content_type = "post"
        elif hasattr(instance.content_object, "story"):
            # Story comments
            creator = instance.content_object.story.profile.user
            content_type = "story"
        else:
            return

        Notification.objects.create(
            user=creator,
            title=f"@{instance.comment_by.user.username} commented on your {content_type}.",
            body=instance.content,  # Include the actual comment content
            type="comment_received",
            related_event_id=str(instance.id)  # Store comment ID for reference
        )


# 6️⃣ Follow → Creator notified
@receiver(post_save, sender=Follow)
def notify_new_follower(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.following.user,
            title=f"@{instance.follower.user.username} started following you.",
            type="follow_received"
        )


# 7️⃣ SpendEvent (like token purchase / unlock) → Creator gets token_received
@receiver(post_save, sender=SpendEvent)
def notify_spend_event(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.creator,
            title=f"You received {instance.coins_spent} tokens from @{instance.fan.username}.",
            type="token_received"
        )


# 8️⃣ Payout Request → Notify Creator when payout processed
@receiver(post_save, sender=PayoutRequest)
def notify_payout_processed(sender, instance, created, **kwargs):
    # optional: if you have a `status` field, check for 'approved'
    if created:
        Notification.objects.create(
            user=instance.user,
            title="Your payout request has been processed.",
            type="payout_processed"
        )
