from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Wallet, SpendEvent, CreatorMonetization, TIER_SPLITS, COIN_VALUE_USD, MonetizationStatus
import logging
logger = logging.getLogger(__name__)

def can_earn(user) -> bool:
    try:
        return user.monetization.status == MonetizationStatus.ACTIVE
    except CreatorMonetization.DoesNotExist:
        return False

@transaction.atomic
def spend_coins(fan, creator, service: str, coins: int):
    """
    Fixed coin spending logic - only add creator's share to creator wallet
    """
    logger.info(f"Starting coin spend: {fan.name} -> {creator.name}, {coins} coins for {service}")
    
    if not can_earn(creator):
        logger.warning(f"Creator {creator.name} cannot earn - monetization not active")
        raise PermissionError("Creator not yet monetized or approved.")

    # Get fan's wallet and spend coins
    fan_wallet = fan.wallet
    logger.info(f"Fan wallet balance before: {fan_wallet.balance}")
    
    # Check balance before spending
    if fan_wallet.balance < coins:
        raise ValueError(f"Insufficient coins. Required: {coins}, Available: {fan_wallet.balance}")
    
    fan_wallet.spend(coins)
    logger.info(f"Fan wallet balance after: {fan_wallet.balance}")

    # Get creator's tier and calculate revenue split
    tier = creator.creator_profile.tier
    platform_pct, creator_pct = TIER_SPLITS[tier]
    logger.info(f"Creator tier: {tier}, Split: {creator_pct*100}% creator, {platform_pct*100}% platform")

    # Calculate USD values
    gross = Decimal(coins) * COIN_VALUE_USD
    usd_platform = (platform_pct * gross).quantize(Decimal("0.01"))
    usd_creator = (creator_pct * gross).quantize(Decimal("0.01"))

    logger.info(f"Revenue calculation: {coins} coins = ${gross} gross, "
                f"Creator gets: ${usd_creator}, Platform earns: ${usd_platform}")

    # ✅ FIXED: Calculate creator's coin share based on percentage
    # Convert Decimal to float for multiplication, then back to int
    creator_coins_earned = int(float(coins) * float(creator_pct))
    
    # Add only creator's share to creator's wallet
    if creator_coins_earned > 0:
        creator_wallet = creator.wallet
        current_creator_balance = creator_wallet.balance
        creator_wallet.add(creator_coins_earned)
        logger.info(f"Added {creator_coins_earned} coins to creator {creator.name}'s wallet. Balance: {current_creator_balance} -> {creator_wallet.balance}")

    # Record the spend event
    ev = SpendEvent.objects.create(
        creator=creator, 
        fan=fan, 
        service=service, 
        coins_spent=coins,
        usd_gross=gross.quantize(Decimal("0.01")),
        usd_platform=usd_platform, 
        usd_creator=usd_creator,
    )

    logger.info(f"SpendEvent created: ID {ev.id}")

    # Update creator's engagement score
    cp = creator.creator_profile
    old_score = cp.engagement_score
    old_tier = cp.tier
    
    if service in ("chat",):
        cp.engagement_score += 1
    elif service in ("photo", "video"):
        cp.engagement_score += 5
    elif service == "locked":
        cp.engagement_score += 10
    
    # Update tier based on new score
    cp.update_tier_based_on_score()
    cp.save(update_fields=["engagement_score", "tier"])
    
    logger.info(f"Creator engagement: {old_score} -> {cp.engagement_score}, "
                f"Tier: {old_tier} -> {cp.tier}")

    return ev



# from decimal import Decimal
# from django.db import transaction
# from django.utils import timezone
# from .models import Wallet, SpendEvent, CreatorMonetization, TIER_SPLITS, COIN_VALUE_USD, MonetizationStatus
# import logging
# logger = logging.getLogger(__name__)

# def can_earn(user) -> bool:
#     try:
#         return user.monetization.status == MonetizationStatus.ACTIVE
#     except CreatorMonetization.DoesNotExist:
#         return False

# @transaction.atomic
# def spend_coins(fan, creator, service: str, coins: int):
#     """
#     ফ্যান কয়েন খরচ করলে — Vault থেকে deduct, split হিসাব, SpendEvent রেকর্ড।
#     Only allowed যদি creator monetization ACTIVE থাকে।
#     """
#     logger.info(f"Starting coin spend: {fan.name} -> {creator.name}, {coins} coins for {service}")
    
#     if not can_earn(creator):
#         logger.warning(f"Creator {creator.name} cannot earn - monetization not active")
#         raise PermissionError("Creator not yet monetized or approved.")

#     # Get fan's wallet and spend coins
#     fan_wallet = fan.wallet
#     logger.info(f"Fan wallet balance before: {fan_wallet.balance}")
#     fan_wallet.spend(coins)
#     logger.info(f"Fan wallet balance after: {fan_wallet.balance}")

#     # Get creator's tier and calculate revenue split
#     tier = creator.creator_profile.tier
#     platform_pct, creator_pct = TIER_SPLITS[tier]
#     logger.info(f"Creator tier: {tier}, Split: {creator_pct*100}% creator, {platform_pct*100}% platform")

#     # Calculate USD values
    
#     if not can_earn(creator) and service != "profile_unlock":
#         # Fan can unlock a profile even if creator isn't monetized (goes to platform only)
#         raise PermissionError("Creator not yet monetized or approved.")

#     fan.wallet.spend(coins)

#     # Compute split
#     gross = Decimal(coins) * COIN_VALUE_USD
#     if service == "profile_unlock":
#         platform_pct, creator_pct = Decimal("1.00"), Decimal("0.00")
#     else:
#         tier = creator.creator_profile.tier
#         platform_pct, creator_pct = TIER_SPLITS[tier]

#     usd_platform = (platform_pct * gross).quantize(Decimal("0.01"))
#     usd_creator = (creator_pct * gross).quantize(Decimal("0.01"))
#     usd_creator  = (creator_pct  * gross).quantize(Decimal("0.01"))

#     logger.info(f"Revenue calculation: {coins} coins = ${gross} gross, "
#                 f"Creator gets: ${usd_creator}, Platform gets: ${usd_platform}")

#     # ✅ ADD COINS TO CREATOR'S WALLET
#     creator_wallet = creator.wallet
#     creator_coins_earned = coins  # Creator gets the same number of coins spent
#     creator_wallet.add(creator_coins_earned)
#     logger.info(f"Added {creator_coins_earned} coins to creator {creator.name}'s wallet. New balance: {creator_wallet.balance}")

#     # Record the spend event
#     ev = SpendEvent.objects.create(
#         creator=creator, 
#         fan=fan, 
#         service=service, 
#         coins_spent=coins,
#         usd_gross=gross.quantize(Decimal("0.01")),
#         usd_platform=usd_platform, 
#         usd_creator=usd_creator,
#     )

#     logger.info(f"SpendEvent created: ID {ev.id}")

#     # Update creator's engagement score
#     cp = creator.creator_profile
#     old_score = cp.engagement_score
#     old_tier = cp.tier
    
#     if service in ("chat",):
#         cp.engagement_score += 1
#     # Engagement bump (simple, matches spec)
#     if service in ("chat", "tip"):
#         creator.creator_profile.engagement_score += 1
#     elif service in ("photo", "video"):
#         creator.creator_profile.engagement_score += 5
#     elif service == "locked":
#         cp.engagement_score += 10
    
#     # Update tier based on new score
#     cp.update_tier_based_on_score()
#     cp.save(update_fields=["engagement_score", "tier"])
    
#     logger.info(f"Creator engagement: {old_score} -> {cp.engagement_score}, "
#                 f"Tier: {old_tier} -> {cp.tier}")



#     creator.creator_profile.engagement_score += 10
#     creator.creator_profile.save(update_fields=["engagement_score"])
#     return ev

