# Create a management command to sync balances
# apps/monetization/management/commands/sync_wallet_balances.py
from django.core.management.base import BaseCommand
from apps.monetization.models import Wallet
from django.utils import timezone

class Command(BaseCommand):
    help = 'Sync wallet balance fields with coin lots'
    
    def handle(self, *args, **options):
        for wallet in Wallet.objects.all():
            calculated_balance = wallet.calculated_balance
            if wallet.balance != calculated_balance:
                self.stdout.write(
                    f"Fixing {wallet.user.name}: {wallet.balance} -> {calculated_balance}"
                )
                wallet.balance = calculated_balance
                wallet.updated_at = timezone.now()
                wallet.save()
        
        self.stdout.write(self.style.SUCCESS('Successfully synced all wallet balances'))