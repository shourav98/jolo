from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from apps.monetization.models import CreatorProfile, SpendEvent

def evaluate_tier(fans, score):
    if fans >= 500 and score >= 85: return "diamond"
    if fans >= 250 and score >= 70: return "platinum"
    if fans >= 100 and score >= 50: return "gold"
    return "silver"

class Command(BaseCommand):
    help = "Monthly tier refresh"
    def handle(self, *args, **kwargs):
        since = timezone.now() - timedelta(days=30)
        for cp in CreatorProfile.objects.select_related("user"):
            fans_30d = (SpendEvent.objects
                        .filter(creator=cp.user, created_at__gte=since)
                        .values("fan").distinct().count())
            new_tier = evaluate_tier(fans_30d, cp.engagement_score)
            if cp.tier != new_tier:
                cp.tier = new_tier
            cp.last_refresh = timezone.now()
            cp.save(update_fields=["tier","last_refresh"])
        self.stdout.write(self.style.SUCCESS("Tiers refreshed"))
