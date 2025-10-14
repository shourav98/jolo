from decimal import Decimal
from django.db import transaction
from .models import Wallet, SpendEvent, CreatorMonetization, TIER_SPLITS, COIN_VALUE_USD, MonetizationStatus

def can_earn(user) -> bool:
    try:
        return user.monetization.status == MonetizationStatus.ACTIVE
    except CreatorMonetization.DoesNotExist:
        return False

@transaction.atomic
def spend_coins(fan, creator, service: str, coins: int):
    
    if not can_earn(creator):
        raise PermissionError("Creator not yet monetized or approved.")

    fan_wallet = fan.wallet
    fan_wallet.spend(coins)

    tier = creator.creator_profile.tier
    platform_pct, creator_pct = TIER_SPLITS[tier]

    gross = Decimal(coins) * COIN_VALUE_USD
    usd_platform = (platform_pct * gross).quantize(Decimal("0.01"))
    usd_creator  = (creator_pct * gross).quantize(Decimal("0.01"))

    ev = SpendEvent.objects.create(
        creator=creator, fan=fan, service=service, coins_spent=coins,
        usd_gross=gross.quantize(Decimal("0.01")),
        usd_platform=usd_platform, usd_creator=usd_creator,
    )

    # engagement bump (সরল)
    cp = creator.creator_profile
    if service in ("chat",):
        cp.engagement_score += 1
    elif service in ("photo", "video"):
        cp.engagement_score += 5
    elif service == "locked":
        cp.engagement_score += 10
    cp.save(update_fields=["engagement_score"])

    return ev
