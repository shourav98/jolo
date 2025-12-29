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


@receiver(post_save, sender=CreatorMonetization)
def set_creator_flag_based_on_monetization(sender, instance, **kwargs):

    try:
        profile = instance.user.profile
        should_be_creator = instance.status == 'active'
        if profile.is_creator != should_be_creator:
            profile.is_creator = should_be_creator
            profile.save(update_fields=["is_creator"])
    except UserProfile.DoesNotExist:
        pass


