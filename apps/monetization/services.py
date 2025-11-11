
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Wallet, SpendEvent, CreatorMonetization, TIER_SPLITS, COIN_VALUE_USD, MonetizationStatus
import logging
logger = logging.getLogger(__name__)

def can_earn(user) -> bool:
    """Check if creator is eligible to earn."""
    try:
        return user.monetization.status == MonetizationStatus.ACTIVE
    except CreatorMonetization.DoesNotExist:
        return False


@transaction.atomic
def spend_coins(fan, creator, service: str, coins: int):
    """
    ✅ Unified coin spending logic:
    - Deducts coins from fan.
    - Splits amount based on creator tier.
    - Adds only creator's share to creator's wallet.
    - Records SpendEvent.
    """

    logger.info(f"💰 {fan.name} spending {coins} coins for {service} to {creator.name}")

    # Validation
    if coins <= 0:
        raise ValueError("Coin amount must be positive.")

    fan_wallet = fan.wallet
    if fan_wallet.balance < coins:
        raise ValueError(f"Insufficient coins. Required: {coins}, Available: {fan_wallet.balance}")

    # Deduct from fan
    fan_wallet.spend(coins)
    logger.info(f"✅ Deducted {coins} from {fan.name}'s wallet. Remaining: {fan_wallet.balance}")

    # Default split (for profile_unlock → 100% platform)
    if service == "profile_unlock":
        platform_pct, creator_pct = Decimal("1.00"), Decimal("0.00")
    else:
        if not can_earn(creator):
            raise PermissionError("Creator is not yet monetized or approved.")
        tier = getattr(creator.creator_profile, "tier", "silver")
        platform_pct, creator_pct = TIER_SPLITS.get(tier, (Decimal("0.70"), Decimal("0.30")))

    # 💵 USD values
    gross_usd = Decimal(coins) * COIN_VALUE_USD
    usd_platform = (gross_usd * platform_pct).quantize(Decimal("0.01"))
    usd_creator = (gross_usd * creator_pct).quantize(Decimal("0.01"))

    # 🎯 Split coins for creator
    creator_coins = int(coins * creator_pct)
    platform_coins = coins - creator_coins

    logger.info(f"Split: {creator_pct*100}% creator ({creator_coins}c), {platform_pct*100}% platform ({platform_coins}c)")

    # Add only creator's share
    if creator_coins > 0:
        creator_wallet = creator.wallet
        before = creator_wallet.balance
        creator_wallet.balance += creator_coins
        creator_wallet.save(update_fields=["balance"])
        logger.info(f"Added {creator_coins} coins to {creator.name}'s wallet ({before} → {creator_wallet.balance})")

    # 🧾 Record spend event
    ev = SpendEvent.objects.create(
        creator=creator,
        fan=fan,
        service=service,
        coins_spent=coins,
        usd_gross=gross_usd.quantize(Decimal("0.01")),
        usd_platform=usd_platform,
        usd_creator=usd_creator,
    )

    logger.info(f"SpendEvent logged (ID {ev.id})")

    # ⭐ Engagement boost
    try:
        cp = creator.creator_profile
        old_score, old_tier = cp.engagement_score, cp.tier

        if service in ("chat", "tip"):
            cp.engagement_score += 1
        elif service in ("photo", "video"):
            cp.engagement_score += 5
        elif service == "locked":
            cp.engagement_score += 10

        cp.update_tier_based_on_score()
        cp.save(update_fields=["engagement_score", "tier"])

        logger.info(f"Engagement: {old_score} → {cp.engagement_score}, Tier: {old_tier} → {cp.tier}")
    except Exception as e:
        logger.warning(f"Engagement update failed for {creator.name}: {e}")

    # ✅ Return structured data
    return {
        "coins_spent": coins,
        "creator_share": creator_coins,
        "platform_share": platform_coins,
        "gross_usd": float(gross_usd),
        "creator_usd": float(usd_creator),
        "platform_usd": float(usd_platform),
        "event_id": ev.id,
    }









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
#     Fixed coin spending logic - only add creator's share to creator wallet
#     """
#     logger.info(f"Starting coin spend: {fan.name} -> {creator.name}, {coins} coins for {service}")
    
#     if not can_earn(creator):
#         logger.warning(f"Creator {creator.name} cannot earn - monetization not active")
#         raise PermissionError("Creator not yet monetized or approved.")

#     # Get fan's wallet and spend coins
#     fan_wallet = fan.wallet
#     logger.info(f"Fan wallet balance before: {fan_wallet.balance}")
    
#     # Check balance before spending
#     if fan_wallet.balance < coins:
#         raise ValueError(f"Insufficient coins. Required: {coins}, Available: {fan_wallet.balance}")
    
#     fan_wallet.spend(coins)
#     logger.info(f"Fan wallet balance after: {fan_wallet.balance}")

#     # Get creator's tier and calculate revenue split
#     tier = creator.creator_profile.tier
#     platform_pct, creator_pct = TIER_SPLITS[tier]
#     logger.info(f"Creator tier: {tier}, Split: {creator_pct*100}% creator, {platform_pct*100}% platform")

#     # Calculate USD values
#     gross = Decimal(coins) * COIN_VALUE_USD
#     usd_platform = (platform_pct * gross).quantize(Decimal("0.01"))
#     usd_creator = (creator_pct * gross).quantize(Decimal("0.01"))

#     logger.info(f"Revenue calculation: {coins} coins = ${gross} gross, "
#                 f"Creator gets: ${usd_creator}, Platform earns: ${usd_platform}")

#     # ✅ FIXED: Calculate creator's coin share based on percentage
#     # Convert Decimal to float for multiplication, then back to int
#     creator_coins_earned = int(float(coins) * float(creator_pct))
    
#     # Add only creator's share to creator's wallet
#     if creator_coins_earned > 0:
#         creator_wallet = creator.wallet
#         current_creator_balance = creator_wallet.balance
#         creator_wallet.add(creator_coins_earned)
#         logger.info(f"Added {creator_coins_earned} coins to creator {creator.name}'s wallet. Balance: {current_creator_balance} -> {creator_wallet.balance}")

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
#     elif service in ("photo", "video"):
#         cp.engagement_score += 5
#     elif service == "locked":
#         cp.engagement_score += 10
    
#     # Update tier based on new score
#     cp.update_tier_based_on_score()
#     cp.save(update_fields=["engagement_score", "tier"])
    
#     logger.info(f"Creator engagement: {old_score} -> {cp.engagement_score}, "
#                 f"Tier: {old_tier} -> {cp.tier}")

#     return ev



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

