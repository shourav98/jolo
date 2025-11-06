from django.core.management.base import BaseCommand
from apps.monetization.models import Wallet, CoinLot
from apps.account.models import CustomUser

class Command(BaseCommand):
    help = 'Check wallet status and coin lots'
    
    def handle(self, *args, **options):
        users = CustomUser.objects.all()
        
        for user in users:
            wallet = user.wallet
            coin_lots = user.coin_lots.all()
            
            self.stdout.write(f"\nUser: {user.name}")
            self.stdout.write(f"Stored balance: {wallet.balance}")
            self.stdout.write(f"Calculated balance: {wallet.calculated_balance}")
            self.stdout.write(f"Coin lots: {coin_lots.count()}")
            
            for lot in coin_lots:
                self.stdout.write(f"  - Lot {lot.id}: {lot.coins_granted}g / {lot.coins_remaining}r")
            
            if wallet.balance != wallet.calculated_balance:
                self.stdout.write(self.style.ERROR("BALANCE MISMATCH!"))