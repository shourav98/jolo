from django.core.management.base import BaseCommand
from apps.monetization.models import CoinPackage

PACKS = [
    ("Chat Pack", 10,  "0.99",  "0.0990"),
    ("Spark",     50,  "2.99",  "0.0598"),
    ("Boost",     260, "11.99", "0.0461"),
    ("Momentum",  540, "23.99", "0.0444"),
    ("Power",     1100,"47.99", "0.0436"),
]

class Command(BaseCommand):
    help = "Seed Whyspers coin packages"

    def handle(self, *args, **kwargs):
        for name, coins, price, pcr in PACKS:
            CoinPackage.objects.update_or_create(
                name=name, defaults={"coins": coins, "price_usd": price, "per_coin_rate": pcr}
            )
        self.stdout.write(self.style.SUCCESS("Coin packs seeded."))
