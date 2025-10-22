from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from apps.monetization.models import SpendEvent, COIN_VALUE_USD, TIER_SPLITS
from apps.monetization.models import CreatorProfile

def spend_coins(fan, creator, service, coins):
    """
    Handle coin spending with proper revenue split according to creator tier
    
    Args:
        fan: The user spending coins
        creator: The creator receiving the payment
        service: Type of service (chat, photo, video, etc.)
        coins: Number of coins being spent
    """
    # Validate inputs
    if not hasattr(fan, 'wallet'):
        raise ValueError("Fan wallet not found")
    
    if not hasattr(creator, 'creator_profile'):
        raise ValueError("Creator profile not found")
    
    # Check fan's wallet balance
    if fan.wallet.balance < coins:
        raise ValueError(f"Insufficient coins. Required: {coins}, Available: {fan.wallet.balance}")
    
    # Calculate USD values based on coin value
    usd_gross = Decimal(coins) * COIN_VALUE_USD
    
    # Get creator's tier and revenue split percentages
    creator_profile = creator.creator_profile
    platform_pct, creator_pct = TIER_SPLITS.get(creator_profile.tier, (Decimal("0.70"), Decimal("0.30")))
    
    # Calculate platform and creator earnings
    usd_platform = usd_gross * platform_pct
    usd_creator = usd_gross * creator_pct
    
    # Round to 2 decimal places for currency
    usd_gross = usd_gross.quantize(Decimal('0.01'))
    usd_platform = usd_platform.quantize(Decimal('0.01'))
    usd_creator = usd_creator.quantize(Decimal('0.01'))
    
    # Deduct coins from fan's wallet
    fan.wallet.spend(coins)
    
    # Record the spend event with revenue split
    spend_event = SpendEvent.objects.create(
        creator=creator,
        fan=fan,
        service=service,
        coins_spent=coins,
        usd_gross=usd_gross,
        usd_platform=usd_platform,
        usd_creator=usd_creator
    )
    
    # Update creator's engagement score
    update_engagement_score(creator)
    
    # Log the transaction for debugging
    print(f"Coin spend: {fan.name} -> {creator.name}, {coins} coins, "
          f"Tier: {creator_profile.tier}, Split: {creator_pct*100}% creator, "
          f"Creator earns: ${usd_creator}, Platform earns: ${usd_platform}")
    
    return spend_event

def update_engagement_score(creator):
    """
    Update creator's engagement score based on paid messages in the last 7 days
    +1 point for every paid message received
    """
    if not hasattr(creator, 'creator_profile'):
        return
    
    week_ago = timezone.now() - timedelta(days=7)
    
    # Count paid chat messages in the last 7 days
    paid_messages_count = SpendEvent.objects.filter(
        creator=creator,
        created_at__gte=week_ago,
        service="chat"
    ).count()
    
    # Update engagement score (1 point per paid message as per requirements)
    creator_profile = creator.creator_profile
    creator_profile.engagement_score = paid_messages_count
    creator_profile.save()
    
    # Check and update tier based on engagement score
    update_creator_tier(creator_profile)

def update_creator_tier(creator_profile):
    """
    Update creator's tier based on engagement score according to requirements:
    - Silver to Gold: score ≥ 50
    - Gold to Platinum: score ≥ 70  
    - Platinum to Diamond: score ≥ 85
    """
    score = creator_profile.engagement_score
    
    if score >= 85 and creator_profile.tier != "diamond":
        creator_profile.tier = "diamond"
        creator_profile.save()
        print(f"Creator {creator_profile.user.name} promoted to DIAMOND tier")
    elif score >= 70 and creator_profile.tier not in ["platinum", "diamond"]:
        creator_profile.tier = "platinum"
        creator_profile.save()
        print(f"Creator {creator_profile.user.name} promoted to PLATINUM tier")
    elif score >= 50 and creator_profile.tier not in ["gold", "platinum", "diamond"]:
        creator_profile.tier = "gold"
        creator_profile.save()
        print(f"Creator {creator_profile.user.name} promoted to GOLD tier")

def can_send_free_message(session, user):
    """
    Check if user can send a free message based on chat rules:
    - Creators always send free messages
    - Fans send free messages during 60-second free window after creator response
    - First fan message is free if creator has messaged first
    """
    if user == session.creator:
        return True  # Creators always send free messages
    
    if session.is_free_window_active():
        return True
        
    # Check if this is the first fan message and creator has messaged first
    is_first_fan_message = not session.messages.filter(sender=user).exists()
    if is_first_fan_message and session.messages.filter(sender=session.creator).exists():
        return True
        
    return False

def get_message_cost(creator_tier):
    """
    Get cost for sending a message based on creator tier
    """
    tier_costs = {
        "silver": 10,
        "gold": 10,
        "platinum": 15,
        "diamond": 20
    }
    return tier_costs.get(creator_tier, 10)

def calculate_revenue_split(coins_spent, creator_tier):
    """
    Calculate revenue split for a given coin amount and creator tier
    Returns: (usd_gross, usd_platform, usd_creator)
    """
    usd_gross = Decimal(coins_spent) * COIN_VALUE_USD
    platform_pct, creator_pct = TIER_SPLITS.get(creator_tier, (Decimal("0.70"), Decimal("0.30")))
    
    usd_platform = (usd_gross * platform_pct).quantize(Decimal('0.01'))
    usd_creator = (usd_gross * creator_pct).quantize(Decimal('0.01'))
    
    return usd_gross, usd_platform, usd_creator