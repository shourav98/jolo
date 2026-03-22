from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import ContentViolationLog, UserModerationProfile


# ──────────────────────────────────────
#  ContentViolationLog Admin
# ──────────────────────────────────────

@admin.register(ContentViolationLog)
class ContentViolationLogAdmin(ModelAdmin):
    list_display = (
        "id", "user", "content_type", "action_taken",
        "appeal_status", "reviewed_by", "created_at"
    )
    list_filter = ("action_taken", "content_type", "appeal_status")
    search_fields = ("user__name", "user__phone")
    readonly_fields = (
        "feed", "user", "content_type", "violation_categories",
        "action_taken", "ai_raw_response", "created_at",
        "reviewed_by", "reviewed_at",
    )
    ordering = ("-created_at",)

    fieldsets = (
        ("📋 Violation Summary", {
            "fields": ("user", "feed", "content_type", "action_taken", "created_at")
        }),
        ("🤖 AI Decision", {
            "fields": ("violation_categories", "ai_raw_response"),
            "classes": ("collapse",),
        }),
        ("⚖️ Appeal & Review", {
            "fields": ("appeal_status", "appeal_note", "reviewed_by", "reviewed_at", "admin_notes")
        }),
    )

    actions = ["approve_appeal", "reject_appeal", "lift_ban"]

    @admin.action(description="✅ Approve appeal (lift restriction by 1 strike)")
    def approve_appeal(self, request, queryset):
        for log in queryset:
            log.appeal_status = "approved"
            log.reviewed_by = request.user
            log.reviewed_at = timezone.now()
            log.save()
            # Reduce violation count
            mod_profile = getattr(log.user, "moderation_profile", None)
            if mod_profile and mod_profile.violation_count >= 1:
                mod_profile.violation_count = max(0, mod_profile.violation_count - 1)
                if mod_profile.violation_count == 0:
                    mod_profile.restriction_level = "none"
                    mod_profile.restricted_until = None
                elif mod_profile.violation_count == 1:
                    mod_profile.restriction_level = "warned"
                    mod_profile.restricted_until = None
                mod_profile.save()
            if log.action_taken == "banned":
                log.user.is_active = True
                log.user.save(update_fields=["is_active"])
        self.message_user(request, f"{queryset.count()} appeal(s) approved.")

    @admin.action(description="❌ Reject appeal (action stands)")
    def reject_appeal(self, request, queryset):
        queryset.update(
            appeal_status="rejected",
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"{queryset.count()} appeal(s) rejected.")

    @admin.action(description="🔓 Lift account ban (reactivate user)")
    def lift_ban(self, request, queryset):
        for log in queryset.filter(action_taken="banned"):
            log.user.is_active = True
            log.user.save(update_fields=["is_active"])
            mod_profile = getattr(log.user, "moderation_profile", None)
            if mod_profile:
                mod_profile.restriction_level = "none"
                mod_profile.restricted_until = None
                mod_profile.save()
        self.message_user(request, "Selected bans lifted.")


# ──────────────────────────────────────
#  UserModerationProfile Admin
# ──────────────────────────────────────

@admin.register(UserModerationProfile)
class UserModerationProfileAdmin(ModelAdmin):
    list_display = (
        "user", "violation_count", "restriction_level",
        "restricted_until", "last_violation_at"
    )
    list_filter = ("restriction_level",)
    search_fields = ("user__name", "user__phone")
    readonly_fields = ("user", "violation_count", "last_violation_at")
    ordering = ("-violation_count",)

    fieldsets = (
        ("👤 User", {"fields": ("user",)}),
        ("📊 Strike Status", {
            "fields": ("violation_count", "restriction_level", "restricted_until", "last_violation_at")
        }),
        ("📝 Admin Notes", {"fields": ("admin_notes",)}),
    )

    actions = ["reset_strikes", "ban_user", "lift_restriction"]

    @admin.action(description="🔄 Reset violation count to 0")
    def reset_strikes(self, request, queryset):
        queryset.update(violation_count=0, restriction_level="none", restricted_until=None)
        self.message_user(request, f"{queryset.count()} user(s) strikes reset.")

    @admin.action(description="🚫 Permanently ban user(s)")
    def ban_user(self, request, queryset):
        for profile in queryset:
            profile.restriction_level = "banned"
            profile.save()
            profile.user.is_active = False
            profile.user.save(update_fields=["is_active"])
        self.message_user(request, f"{queryset.count()} user(s) banned.")

    @admin.action(description="🔓 Lift restriction (set to none)")
    def lift_restriction(self, request, queryset):
        for profile in queryset:
            profile.restriction_level = "none"
            profile.restricted_until = None
            profile.save()
            profile.user.is_active = True
            profile.user.save(update_fields=["is_active"])
        self.message_user(request, f"{queryset.count()} restriction(s) lifted.")
