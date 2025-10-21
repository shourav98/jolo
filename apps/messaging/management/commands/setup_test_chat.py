# apps/messaging/management/commands/setup_test_chat.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.account.models import UserProfile
from apps.monetization.models import CreatorProfile, CreatorMonetization, Wallet
from apps.messaging.models import UserActivity

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup test users for chat system'

    def handle(self, *args, **options):
        # Create test creator
        creator, created = User.objects.get_or_create(
            phone='+8801700000001',
            defaults={'name': 'Test Creator'}
        )
        UserProfile.objects.get_or_create(
            user=creator, 
            defaults={'is_creator': True, 'is_online': True}
        )
        CreatorProfile.objects.get_or_create(user=creator, defaults={'tier': 'silver'})
        CreatorMonetization.objects.get_or_create(user=creator, defaults={'status': 'active'})
        Wallet.objects.get_or_create(user=creator, defaults={'balance': 0})
        UserActivity.objects.get_or_create(user=creator, defaults={'is_online': True})
        
        # Create test fan
        fan, created = User.objects.get_or_create(
            phone='+8801700000002',
            defaults={'name': 'Test Fan'}
        )
        UserProfile.objects.get_or_create(user=fan, defaults={'is_creator': False})
        Wallet.objects.get_or_create(user=fan, defaults={'balance': 100})
        UserActivity.objects.get_or_create(user=fan, defaults={'is_online': True})
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created test users:\n'
                f'Creator: {creator.name} (ID: {creator.id})\n'
                f'Fan: {fan.name} (ID: {fan.id})'
            )
        )