from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta  

import logging
logger = logging.getLogger(__name__)

# Coin value and tier splits (add these constants)
COIN_VALUE_USD = Decimal("0.02")

TIER_SPLITS = {
    "silver": (Decimal("0.70"), Decimal("0.30")),    # 70% platform, 30% creator
    "gold": (Decimal("0.60"), Decimal("0.40")),      # 60% platform, 40% creator  
    "platinum": (Decimal("0.50"), Decimal("0.50")),  # 50% platform, 50% creator
    "diamond": (Decimal("0.40"), Decimal("0.60")),   # 40% platform, 60% creator
}


MIN_PAYOUT_USD = Decimal("50.00")  # 
COIN_EXPIRY_DAYS = 30  # 

class CoinPackage(models.Model):
    name = models.CharField(max_length=50, unique=True)
    coins = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_usd = models.DecimalField(max_digits=7, decimal_places=2)
    per_coin_rate = models.DecimalField(max_digits=7, decimal_places=4)
    class Meta: ordering = ["coins"]
    def __str__(self): return f"{self.name} • {self.coins}c • ${self.price_usd}"

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.PositiveIntegerField(default=0)  # Keep this as the actual stored balance
    updated_at = models.DateTimeField(auto_now=True)
    last_purchase_at = models.DateTimeField(null=True, blank=True)



    @property
    def calculated_balance(self):
        """Calculate balance from coin lots (for verification)"""
        return sum(lot.coins_remaining for lot in self.user.coin_lots.filter(coins_remaining__gt=0))

    def add(self, coins: int):
        coins = int(coins)
        # Create coin lot
        CoinLot.objects.create(user=self.user, coins_granted=coins, coins_remaining=coins)
        # Update the actual balance field
        self.balance += coins
        self.updated_at = timezone.now()
        self.last_purchase_at = timezone.now()
        self.save(update_fields=["balance", "updated_at", "last_purchase_at"])

    def spend(self, coins: int):
        coins = int(coins)
        
        # Check if we have enough balance
        if self.balance < coins:
            raise ValueError("Insufficient Vault balance")
        
        # Update coin lots using FIFO
        remaining = coins
        for lot in self.user.coin_lots.filter(coins_remaining__gt=0).order_by('grant_ts'):
            if remaining <= 0:
                break
                
            spend_from_lot = min(remaining, lot.coins_remaining)
            lot.coins_remaining -= spend_from_lot
            lot.save(update_fields=['coins_remaining'])
            remaining -= spend_from_lot
        
        # Update the actual balance field
        self.balance -= coins
        self.updated_at = timezone.now()
        self.save(update_fields=["balance", "updated_at"])
        
        # Verify that calculated balance matches stored balance
        calculated = self.calculated_balance
        if calculated != self.balance:
            logger.warning(f"Balance mismatch: stored={self.balance}, calculated={calculated}")
            # Auto-correct the balance if there's a mismatch
            self.balance = calculated
            self.save(update_fields=["balance"])

    def expire_coins(self):
        # Call via cron
        expired_date = timezone.now() - timedelta(days=30)
        expired_lots = self.user.coin_lots.filter(grant_ts__lt=expired_date, coins_remaining__gt=0)
        
        total_expired = 0
        for lot in expired_lots:
            total_expired += lot.coins_remaining
            lot.coins_remaining = 0
            lot.save()
        
        # Update balance if coins were expired
        if total_expired > 0:
            self.balance = max(0, self.balance - total_expired)
            self.save(update_fields=["balance"])

    def __str__(self):
        return f"{self.user.name} • Vault: {self.balance}c"

    # @property
    # def calculated_balance(self):
    #     """Calculate balance from coin lots (for verification)"""
    #     return sum(lot.coins_remaining for lot in self.user.coin_lots.all())

    # def add(self, coins: int):
    #     coins = int(coins)
    #     # Create coin lot
    #     CoinLot.objects.create(user=self.user, coins_granted=coins, coins_remaining=coins)
    #     # Update the actual balance field
    #     self.balance += coins
    #     self.updated_at = timezone.now()
    #     self.last_purchase_at = timezone.now()
    #     self.save(update_fields=["balance", "updated_at", "last_purchase_at"])

    # def spend(self, coins: int):
    #     coins = int(coins)
        
    #     # Check if we have enough balance
    #     if self.balance < coins:
    #         raise ValueError("Insufficient Vault balance")
        
    #     # Update coin lots using FIFO
    #     remaining = coins
    #     for lot in self.user.coin_lots.filter(coins_remaining__gt=0).order_by('grant_ts'):
    #         if remaining <= 0:
    #             break
                
    #         spend_from_lot = min(remaining, lot.coins_remaining)
    #         lot.coins_remaining -= spend_from_lot
    #         lot.save(update_fields=['coins_remaining'])
    #         remaining -= spend_from_lot
        
    #     # Update the actual balance field
    #     self.balance -= coins
    #     self.updated_at = timezone.now()
    #     self.save(update_fields=["balance", "updated_at"])
        
    #     # Verify that calculated balance matches stored balance
    #     calculated = self.calculated_balance
    #     if calculated != self.balance:
    #         logger.warning(f"Balance mismatch: stored={self.balance}, calculated={calculated}")
    #         # Auto-correct the balance if there's a mismatch
    #         self.balance = calculated
    #         self.save(update_fields=["balance"])

    # def expire_coins(self):
    #     # Call via cron
    #     expired_date = timezone.now() - timedelta(days=30)
    #     expired_lots = self.user.coin_lots.filter(grant_ts__lt=expired_date, coins_remaining__gt=0)
        
    #     total_expired = 0
    #     for lot in expired_lots:
    #         total_expired += lot.coins_remaining
    #         lot.coins_remaining = 0
    #         lot.save()
        
    #     # Update balance if coins were expired
    #     if total_expired > 0:
    #         self.balance = max(0, self.balance - total_expired)
    #         self.save(update_fields=["balance"])

    # def __str__(self):
    #     return f"{self.user.name} • Vault: {self.balance}c"


class PurchaseMethod(models.TextChoices):
    STRIPE    = "stripe", "Stripe"
    APPLE_PAY = "apple_pay", "Apple Pay"
    GOOGLE_PAY= "google_pay", "Google Pay"
    CARD      = "card", "Card"

class CoinPurchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coin_purchases")
    package = models.ForeignKey(CoinPackage, on_delete=models.SET_NULL, null=True, blank=True)
    coins_added = models.PositiveIntegerField()
    amount_usd = models.DecimalField(max_digits=7, decimal_places=2)
    method = models.CharField(max_length=20, choices=PurchaseMethod.choices)
    txn_id = models.CharField(max_length=128, unique=True)  # idempotent key
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
    def __str__(self): return f"{self.user.name} +{self.coins_added}c (${self.amount_usd})"

class MonetizationStatus(models.TextChoices):
    NON_MONETIZED = "non_monetized", "Apply For Monetization"
    PENDING       = "pending", "Pending Review"
    ACTIVE        = "active", "Active"
    DENIED        = "denied", "Denied"

class CreatorMonetization(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="monetization")
    status = models.CharField(max_length=20, choices=MonetizationStatus.choices, default=MonetizationStatus.NON_MONETIZED)
    applied_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="monetization_reviews")
    # application artifacts
    id_proof = models.URLField(null=True, blank=True)  # Store Cloudinary URL
    id_proof_public_id = models.CharField(max_length=255, null=True, blank=True)  # Store Cloudinary public ID
    intro_video = models.URLField(null=True, blank=True)  # Store Cloudinary URL
    intro_video_public_id = models.CharField(max_length=255, null=True, blank=True)  # Store Cloudinary public ID
    admin_notes = models.TextField(blank=True, null=True)
    def __str__(self): return f"{self.user.name} • {self.get_status_display()}"

class CreatorTier(models.TextChoices):
    SILVER   = "silver", "Silver (70/30)"
    GOLD     = "gold", "Gold (60/40)"
    PLATINUM = "platinum", "Platinum (50/50)"
    DIAMOND  = "diamond", "Diamond (40/60)"

class CreatorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="creator_profile")
    tier = models.CharField(max_length=20, choices=CreatorTier.choices, default=CreatorTier.SILVER)
    engagement_score = models.PositiveIntegerField(default=0)
    active_fans = models.PositiveIntegerField(default=0)
    last_refresh = models.DateTimeField(auto_now_add=True)
    is_inactive = models.BooleanField(default=False)


    def update_tier_based_on_score(self):
        """Update tier based on engagement score"""
        if self.engagement_score >= 85:
            self.tier = CreatorTier.DIAMOND
        elif self.engagement_score >= 70:
            self.tier = CreatorTier.PLATINUM
        elif self.engagement_score >= 50:
            self.tier = CreatorTier.GOLD
        else:
            self.tier = CreatorTier.SILVER
        self.save()
        

    def __str__(self):
        return f"{self.user.name} • {self.get_tier_display()}"


    def __str__(self): return f"{self.user.name} • {self.get_tier_display()}"


class PayoutAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payout_accounts")
    stripe_account_id = models.CharField(max_length=64, unique=True)
    onboarding_complete = models.BooleanField(default=False)
    account_name = models.CharField(max_length=100, blank=True, default="")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-is_default","-created_at"]
    def __str__(self): return f"Stripe {self.stripe_account_id} • {self.account_name or self.user.name}"

class PayoutRequest(models.Model):
    STATUS = (("pending","Pending"),("processing","Processing"),("paid","Paid"),("rejected","Rejected"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payout_requests")
    amount_usd = models.DecimalField(max_digits=9, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    account = models.ForeignKey(PayoutAccount, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    stripe_transfer_id = models.CharField(max_length=128, blank=True, null=True)
    def __str__(self): return f"{self.user.name} • ${self.amount_usd} • {self.status}"

class SpendEvent(models.Model):
    SERVICE_TYPES = (
        ("chat", "Text/Voice Chat"),
        ("photo", "Photo Message"),
        ("video", "Video Message"),
        ("locked", "Locked Content"),
        ("profile_unlock", "Profile Unlock"),  # 100% platform per spec
        ("tip", "Tip"),
    )
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="spend_events_as_creator")
    fan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="spend_events_as_fan")
    service = models.CharField(max_length=32, choices=SERVICE_TYPES)
    coins_spent = models.PositiveIntegerField()
    usd_gross = models.DecimalField(max_digits=9, decimal_places=2)
    usd_platform = models.DecimalField(max_digits=9, decimal_places=2)
    usd_creator = models.DecimalField(max_digits=9, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.fan.name}→{self.creator.name} {self.service} {self.coins_spent}c"
    




class CoinLot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coin_lots")
    coins_granted = models.PositiveIntegerField()
    coins_remaining = models.PositiveIntegerField()
    grant_ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['grant_ts']  # Oldest first for FIFO

    def save(self, *args, **kwargs):
        # Auto-set coins_remaining on first save if not set
        if not self.pk and self.coins_remaining is None:
            self.coins_remaining = self.coins_granted
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lot: {self.coins_granted}c ({self.coins_remaining}c remaining)"

