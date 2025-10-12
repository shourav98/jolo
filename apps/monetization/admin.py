from django.contrib import admin, messages
from django.utils import timezone
from .models import (
    CoinPackage, Wallet, CoinPurchase,
    CreatorMonetization, CreatorProfile, PayoutAccount, SpendEvent,
    MonetizationStatus
)
from .utils_notify import send_sms, send_whatsapp

@admin.action(description="Approve selected applicants")
def approve_selected(modeladmin, request, queryset):
    ok = 0
    for obj in queryset:
        if obj.status == MonetizationStatus.PENDING:
            obj.status = MonetizationStatus.ACTIVE
            obj.approved_at = timezone.now()
            obj.reviewed_by = request.user
            obj.save(update_fields=["status", "approved_at", "reviewed_by"])
            # Notify user
            msg = "🎉 Congrats! Your Whyspers monetization has been approved. You can start earning now."
            phone = getattr(obj.user, "phone", None)
            if phone:
                try:
                    send_sms(phone, msg)
                    send_whatsapp(phone, msg)
                except Exception:
                    pass
            ok += 1
    messages.success(request, f"Approved {ok} applicant(s).")

@admin.action(description="Deny selected applicants")
def deny_selected(modeladmin, request, queryset):
    n = queryset.exclude(status=MonetizationStatus.ACTIVE).update(
        status=MonetizationStatus.DENIED, reviewed_by=request.user
    )
    messages.warning(request, f"Denied {n} applicant(s).")

@admin.register(CreatorMonetization)
class CreatorMonetizationAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "applied_at", "approved_at", "reviewed_by")
    list_filter = ("status",)
    search_fields = ("user__name", "user__phone")
    actions = [approve_selected, deny_selected]

@admin.register(CoinPackage)
class CoinPackageAdmin(admin.ModelAdmin):
    list_display = ("name", "coins", "price_usd", "per_coin_rate")
    ordering = ("coins",)

admin.site.register([Wallet, CoinPurchase, CreatorProfile, PayoutAccount, SpendEvent])
