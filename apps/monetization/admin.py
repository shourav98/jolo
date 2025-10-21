from django.contrib import admin, messages
from unfold.admin import ModelAdmin
from django.utils import timezone
from .models import (
    CoinPackage, Wallet, CoinPurchase, CreatorMonetization,
    CreatorProfile, PayoutAccount, PayoutRequest, SpendEvent, MonetizationStatus
)
from apps.monetization.utils_notify import send_sms, send_whatsapp


#  COIN PACKAGE 
@admin.register(CoinPackage)
class CoinPackageAdmin(ModelAdmin):
    list_display = ("name", "coins", "price_usd", "per_coin_rate")
    search_fields = ("name",)
    ordering = ("coins",)
    list_per_page = 25


# WALLET 
@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_display = ("user", "balance", "updated_at")
    search_fields = ("user__name", "user__phone")
    readonly_fields = ("updated_at",)
    list_per_page = 50


#  COIN PURCHASE 
@admin.register(CoinPurchase)
class CoinPurchaseAdmin(ModelAdmin):
    list_display = ("user", "package", "coins_added", "amount_usd", "method", "txn_id", "created_at")
    list_filter = ("method", "created_at")
    search_fields = ("user__name", "txn_id")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


#  MONETIZATION APPROVAL 
@admin.action(description="Approve selected applicants")
def approve_selected(modeladmin, request, queryset):
    ok = 0
    for obj in queryset:
        if obj.status == MonetizationStatus.PENDING:
            obj.status = MonetizationStatus.ACTIVE
            obj.approved_at = timezone.now()
            obj.reviewed_by = request.user
            obj.save(update_fields=["status", "approved_at", "reviewed_by"])

            # Ensure CreatorProfile exists
            from apps.monetization.models import CreatorProfile
            CreatorProfile.objects.get_or_create(user=obj.user)

            # Notify applicant
            msg = (
                "🎉 Congrats! Your Whyspers monetization has been approved. "
                "You can now start earning, post locked content, and withdraw funds from your Vault."
            )
            phone = getattr(obj.user, "phone", None)
            if phone:
                try:
                    send_sms(phone, msg)
                    send_whatsapp(phone, msg)
                except Exception:
                    pass
            ok += 1
    messages.success(request, f"✅ Approved {ok} applicant(s).")


@admin.register(CreatorMonetization)
class CreatorMonetizationAdmin(ModelAdmin):
    list_display = ("user", "status", "applied_at", "approved_at", "reviewed_by")
    list_filter = ("status",)
    search_fields = ("user__name", "user__phone")
    readonly_fields = ("applied_at", "approved_at")
    actions = [approve_selected]
    date_hierarchy = "applied_at"


# ---------- CREATOR PROFILE ----------
@admin.register(CreatorProfile)
class CreatorProfileAdmin(ModelAdmin):
    list_display = ("user", "tier", "engagement_score", "active_fans", "is_inactive", "last_refresh")
    list_filter = ("tier", "is_inactive")
    search_fields = ("user__name", "user__phone")
    ordering = ("-engagement_score",)
    list_per_page = 50


# PAYOUT ACCOUNT 
@admin.register(PayoutAccount)
class PayoutAccountAdmin(ModelAdmin):
    list_display = ("user", "bank_name", "account_holder_name", "account_number", "is_default", "created_at")
    list_filter = ("is_default", "created_at")
    search_fields = ("user__name", "bank_name", "account_holder_name")
    list_per_page = 30


# PAYOUT REQUEST 
@admin.action(description="Mark selected payouts as paid")
def mark_as_paid(modeladmin, request, queryset):
    count = queryset.update(status="paid", processed_at=timezone.now())
    messages.success(request, f"💰 Marked {count} payout(s) as paid.")

@admin.action(description="Reject selected payouts")
def reject_selected(modeladmin, request, queryset):
    count = queryset.update(status="rejected", processed_at=timezone.now())
    for pr in queryset:
        msg = (
            f"❌ Your payout request of ${pr.amount_usd} has been rejected. "
            "Please check your bank details or contact support."
        )
        phone = getattr(pr.user, "phone", None)
        if phone:
            try:
                send_sms(phone, msg)
                send_whatsapp(phone, msg)
            except Exception:
                pass
    messages.warning(request, f"⚠️ Rejected {count} payout(s).")

@admin.register(PayoutRequest)
class PayoutRequestAdmin(ModelAdmin):
    list_display = ("user", "amount_usd", "status", "account", "created_at", "processed_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__name", "user__phone")
    ordering = ("-created_at",)
    actions = [mark_as_paid, reject_selected]
    date_hierarchy = "created_at"
    list_per_page = 50


# SPEND EVENTS 
@admin.register(SpendEvent)
class SpendEventAdmin(ModelAdmin):
    list_display = ("creator", "fan", "service", "coins_spent", "usd_creator", "usd_platform", "created_at")
    list_filter = ("service", "created_at")
    search_fields = ("creator__name", "fan__name", "service")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 100
