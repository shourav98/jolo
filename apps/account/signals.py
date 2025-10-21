from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import CustomUser, UserProfile
from apps.monetization.models import Wallet, CreatorProfile, CreatorMonetization


@receiver(post_save, sender=CustomUser)
def create_related_records(sender, instance, created, **kwargs):
    
    if created:
        # Profile
        UserProfile.objects.get_or_create(user=instance)
        # Wallet
        Wallet.objects.get_or_create(user=instance)
        # Monetization info
        CreatorMonetization.objects.get_or_create(user=instance)
        # Creator profile (default tier)
        CreatorProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=CreatorProfile)
def set_creator_flag(sender, instance, created, **kwargs):
    
    try:
        profile = instance.user.profile
        if not profile.is_creator:
            profile.is_creator = True
            profile.save(update_fields=["is_creator"])
    except UserProfile.DoesNotExist:
        pass


@receiver(post_delete, sender=CreatorProfile)
def unset_creator_flag(sender, instance, **kwargs):
    
    try:
        profile = instance.user.profile
        if profile.is_creator:
            profile.is_creator = False
            profile.save(update_fields=["is_creator"])
    except UserProfile.DoesNotExist:
        pass


