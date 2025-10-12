from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser
from apps.monetization.models import Wallet, CreatorProfile, CreatorMonetization

@receiver(post_save, sender=CustomUser)
def create_related_records(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(user=instance)
        CreatorMonetization.objects.get_or_create(user=instance)  # non_monetized by default
        CreatorProfile.objects.get_or_create(user=instance)
