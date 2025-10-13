from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from .models import (
    Feed, FeedVideo, Like, Unlike, Comment,
    Transaction, VideoTip, Wallet, CreatorProfile, TopFan
)



#  UNIVERSAL HELPER FOR TOP FAN SCORE


def update_topfan_score(creator_profile, fan_profile, points):
    
    if not creator_profile or not fan_profile:
        return
    if creator_profile == fan_profile:
        return  

    fan, created = TopFan.objects.get_or_create(
        iam=creator_profile,
        fan_profile=fan_profile,
        defaults={"score": points, "status": "active"}
    )
    if not created:
        fan.score += points
        fan.last_interacted = timezone.now()
        fan.save(update_fields=["score", "last_interacted"])



#  LIKE / UNLIKE + COUNTS + FAN SCORE


@receiver(post_save, sender=Like)
def handle_like(sender, instance, created, **kwargs):
   
    target = instance.content_object

    if created:
        # Toggle unlike remove
        Unlike.objects.filter(
            content_type=instance.content_type,
            object_id=instance.object_id,
            unliked_by=instance.liked_by
        ).delete()

        # Like count update
        if hasattr(target, "total_like"):
            target.total_like += 1
            target.save(update_fields=["total_like"])

        # Fan scoring
        creator = getattr(target, "profile", None)
        fan = instance.liked_by
        update_topfan_score(creator, fan, points=2)


@receiver(post_delete, sender=Like)
def handle_like_delete(sender, instance, **kwargs):
    target = instance.content_object
    if hasattr(target, "total_like") and target.total_like > 0:
        target.total_like -= 1
        target.save(update_fields=["total_like"])


@receiver(post_save, sender=Unlike)
def handle_unlike(sender, instance, created, **kwargs):
   
    target = instance.content_object
    if created:
        Like.objects.filter(
            content_type=instance.content_type,
            object_id=instance.object_id,
            liked_by=instance.unliked_by
        ).delete()

        if hasattr(target, "total_unlike"):
            target.total_unlike += 1
            target.save(update_fields=["total_unlike"])


@receiver(post_delete, sender=Unlike)
def handle_unlike_delete(sender, instance, **kwargs):
    target = instance.content_object
    if hasattr(target, "total_unlike") and target.total_unlike > 0:
        target.total_unlike -= 1
        target.save(update_fields=["total_unlike"])



#  COMMENT COUNT + FAN SCORE

@receiver(post_save, sender=Comment)
def handle_comment(sender, instance, created, **kwargs):
    
    if created:
        target = instance.content_object
        if hasattr(target, "total_comment"):
            target.total_comment += 1
            target.save(update_fields=["total_comment"])

        creator = getattr(target, "profile", None)
        fan = instance.comment_by
        update_topfan_score(creator, fan, points=3)


@receiver(post_delete, sender=Comment)
def handle_comment_delete(sender, instance, **kwargs):
    target = instance.content_object
    if hasattr(target, "total_comment") and target.total_comment > 0:
        target.total_comment -= 1
        target.save(update_fields=["total_comment"])



#  TRANSACTION (TIP / GIFT) + WALLET + FAN SCORE


@receiver(post_save, sender=Transaction)
def handle_transaction(sender, instance, created, **kwargs):
    """Tip/Gift  wallet update and fan score update"""
    if created:
        sender_wallet, _ = Wallet.objects.get_or_create(profile=instance.sender)
        receiver_wallet, _ = Wallet.objects.get_or_create(profile=instance.receiver)
        amount = Decimal(instance.amount)

        # Safe update
        sender_wallet.balance = max(sender_wallet.balance - amount, Decimal("0.00"))
        receiver_wallet.balance += amount

        sender_wallet.save(update_fields=["balance"])
        receiver_wallet.save(update_fields=["balance"])

        # Fan score update (+5)
        update_topfan_score(instance.receiver, instance.sender, points=5)



#  VIDEO TIP AUTOMATION


@receiver(post_save, sender=VideoTip)
def handle_video_tip(sender, instance, created, **kwargs):
    
    if created:
        video = instance.video
        if hasattr(video, "total_earn"):
            video.total_earn += instance.amount
            video.save(update_fields=["total_earn"])

        receiver_wallet, _ = Wallet.objects.get_or_create(profile=video.profile)
        receiver_wallet.balance += instance.amount
        receiver_wallet.save(update_fields=["balance"])

        # Fan scoring (+5)
        update_topfan_score(video.profile, instance.sender, points=5)



#  VIDEO VIEW → FAN SCORE 


@receiver(post_save, sender=FeedVideo)
def handle_video_view(sender, instance, **kwargs):
    
    viewer = getattr(instance, "viewer", None)
    creator = instance.profile
    if viewer:
        update_topfan_score(creator, viewer, points=1)
