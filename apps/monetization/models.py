from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal

# split base USD (spec )
COIN_VALUE_USD = Decimal("0.02")

# Tier split (platform_pct, creator_pct) — spec 
TIER_SPLITS = {
    "silver":   (Decimal("0.70"), Decimal("0.30")),
    "gold":     (Decimal("0.60"), Decimal("0.40")),
    "platinum": (Decimal("0.50"), Decimal("0.50")),
    "diamond":  (Decimal("0.40"), Decimal("0.60")),
}


class CoinPackage(models.Model):
    name = models.CharField(max_length=50)
    coins = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_usd = models.DecimalField(max_digits=7, decimal_places=2)
    per_coin_rate = models.DecimalField(max_digits=7, decimal_places=4)

    class Meta:
        ordering = ["coins"]

    def __str__(self):
        return f"{self.name} • {self.coins}c • ${self.price_usd}"


class Wallet(models.Model):
    # Vault
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def add(self, coins: int):
        coins = int(coins)
        self.balance += coins
        self.save(update_fields=["balance", "updated_at"])

    def spend(self, coins: int):
        coins = int(coins)
        if self.balance < coins:
            raise ValueError("Insufficient Vault balance")
        self.balance -= coins
        self.save(update_fields=["balance", "updated_at"])

    def __str__(self):
        return f"{self.user.name} • Vault: {self.balance}c"


class PurchaseMethod(models.TextChoices):
    APPLE_PAY = "apple_pay", "Apple Pay"
    GOOGLE_PAY = "google_pay", "Google Pay"
    CARD      = "card", "Card"


class CoinPurchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coin_purchases")
    package = models.ForeignKey(CoinPackage, on_delete=models.SET_NULL, null=True, blank=True)
    coins_added = models.PositiveIntegerField()
    amount_usd = models.DecimalField(max_digits=7, decimal_places=2)
    method = models.CharField(max_length=20, choices=PurchaseMethod.choices)
    txn_id = models.CharField(max_length=128, unique=True)  # idempotency
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.name} +{self.coins_added}c (${self.amount_usd})"


class MonetizationStatus(models.TextChoices):
    NON_MONETIZED = "non_monetized", "Apply For Monetization"
    PENDING       = "pending", "Pending Review"
    ACTIVE        = "active", "Active"
    DENIED        = "denied", "Denied"


class CreatorMonetization(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="monetization")
    status = models.CharField(max_length=20, choices=MonetizationStatus.choices,
                              default=MonetizationStatus.NON_MONETIZED)
    applied_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="monetization_reviews")
    admin_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.name} • {self.get_status_display()}"


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

    def __str__(self):
        return f"{self.user.name} • {self.get_tier_display()}"


class PayoutAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payout_accounts")
    bank_name = models.CharField(max_length=100)
    account_holder_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=64)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.bank_name} • {self.account_holder_name}"


class SpendEvent(models.Model):
    SERVICE_TYPES = (
        ("chat", "Text/Voice Chat"),
        ("photo", "Photo Message"),
        ("video", "Video Message"),
        ("locked", "Locked Content"),
        ("profile_unlock", "Profile Unlock"),
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
