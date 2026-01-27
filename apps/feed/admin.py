from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    Feed, FeedFile, Comment, Like, Follow,
    Unlock, FeedTip, Story, StoryItem, TopFan,
    BlockedUser, MutedPost, ReportedPost
)


# ---------- FEED ----------
@admin.register(Feed)
class FeedAdmin(ModelAdmin):
    list_display = (
        "id", "profile", "status", "unlock_price",
        "total_like", "total_comment", "total_view",
        "created_at"
    )
    list_filter = ("status", "created_at")
    search_fields = ("profile__user__name", "content")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- FEED FILE ----------
@admin.register(FeedFile)
class FeedFileAdmin(ModelAdmin):
    list_display = ("feed", "file", "created_at")
    search_fields = ("feed__profile__user__name",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- COMMENT ----------
@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("id", "comment_by", "content", "created_at")
    search_fields = ("comment_by__user__name", "content")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- LIKE ----------
@admin.register(Like)
class LikeAdmin(ModelAdmin):
    list_display = ("id", "liked_by", "content_type", "object_id", "created_at")
    search_fields = ("liked_by__user__name",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- FOLLOW ----------
@admin.register(Follow)
class FollowAdmin(ModelAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__user__name", "following__user__name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- UNLOCK ----------
@admin.register(Unlock)
class UnlockAdmin(ModelAdmin):
    list_display = ("fan", "feed", "created_at")
    search_fields = ("fan__user__name", "feed__profile__user__name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- FEED TIP ----------
@admin.register(FeedTip)
class FeedTipAdmin(ModelAdmin):
    list_display = ("sender", "receiver", "amount", "created_at")
    search_fields = ("sender__user__name", "receiver__user__name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- STORY ----------
@admin.register(Story)
class StoryAdmin(ModelAdmin):
    list_display = ("profile", "created_at")
    search_fields = ("profile__user__name",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- STORY ITEM ----------
@admin.register(StoryItem)
class StoryItemAdmin(ModelAdmin):
    list_display = ("story", "file", "expired_at", "is_active", "created_at")
    search_fields = ("story__profile__user__name",)
    readonly_fields = ("created_at",)
    list_filter = ("is_active",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- TOP FAN ----------
@admin.register(TopFan)
class TopFanAdmin(ModelAdmin):
    list_display = ("fan", "creator", "score", "last_interacted", "status")
    search_fields = ("fan__user__name", "creator__user__name")
    list_filter = ("status",)
    ordering = ("-score", "-last_interacted")
    readonly_fields = ("last_interacted",)
    list_per_page = 50


# ---------- BLOCKED USER ----------
@admin.register(BlockedUser)
class BlockedUserAdmin(ModelAdmin):
    list_display = ("blocker", "blocked", "created_at")
    search_fields = ("blocker__user__name", "blocked__user__name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- MUTED POST ----------
@admin.register(MutedPost)
class MutedPostAdmin(ModelAdmin):
    list_display = ("user", "post", "created_at")
    search_fields = ("user__user__name", "post__id")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- REPORTED POST ----------
@admin.register(ReportedPost)
class ReportedPostAdmin(ModelAdmin):
    list_display = ("reporter", "post", "reason", "status", "created_at")
    search_fields = ("reporter__user__name", "post__id")
    list_filter = ("status", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50
    
    list_editable = ("status",)
    actions = ["mark_as_reviewed", "mark_as_resolved", "mark_as_dismissed"]
    
    def mark_as_reviewed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status="reviewed", reviewed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} reports marked as reviewed.")
    mark_as_reviewed.short_description = "Mark selected reports as reviewed"
    
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(status="resolved", reviewed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} reports marked as resolved.")
    mark_as_resolved.short_description = "Mark selected reports as resolved"

    def mark_as_dismissed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status="dismissed", reviewed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} reports marked as dismissed.")
    mark_as_dismissed.short_description = "Mark selected reports as dismissed"

