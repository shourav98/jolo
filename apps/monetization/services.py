from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Wallet, SpendEvent, CreatorMonetization, TIER_SPLITS, COIN_VALUE_USD, MonetizationStatus

def can_earn(user) -> bool:
    try:
        return user.monetization.status == MonetizationStatus.ACTIVE
    except CreatorMonetization.DoesNotExist:
        return False

@transaction.atomic
def spend_coins(fan, creator, service: str, coins: int):
    
    if not can_earn(creator) and service != "profile_unlock":
        # Fan can unlock a profile even if creator isn't monetized (goes to platform only)
        raise PermissionError("Creator not yet monetized or approved.")

    fan.wallet.spend(coins)

    # Compute split
    gross = Decimal(coins) * COIN_VALUE_USD
    if service == "profile_unlock":
        platform_pct, creator_pct = Decimal("1.00"), Decimal("0.00")
    else:
        tier = creator.creator_profile.tier
        platform_pct, creator_pct = TIER_SPLITS[tier]

    usd_platform = (platform_pct * gross).quantize(Decimal("0.01"))
    usd_creator  = (creator_pct  * gross).quantize(Decimal("0.01"))

    ev = SpendEvent.objects.create(
        creator=creator, fan=fan, service=service, coins_spent=coins,
        usd_gross=gross.quantize(Decimal("0.01")),
        usd_platform=usd_platform, usd_creator=usd_creator,
    )

    # Engagement bump (simple, matches spec)
    if service in ("chat", "tip"):
        creator.creator_profile.engagement_score += 1
    elif service in ("photo", "video"):
        creator.creator_profile.engagement_score += 5
    elif service == "locked":
        creator.creator_profile.engagement_score += 10
    creator.creator_profile.save(update_fields=["engagement_score"])
    return ev
