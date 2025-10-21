from django.contrib import admin
from .models import (
    Feed, FeedFile, Comment, Like, Follow,
    Unlock, FeedTip, Story, StoryItem, TopFan
)


# ---------- FEED ----------
@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
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
class FeedFileAdmin(admin.ModelAdmin):
    list_display = ("feed", "file", "created_at")
    search_fields = ("feed__profile__user__name",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- COMMENT ----------
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "comment_by", "content", "created_at")
    search_fields = ("comment_by__user__name", "content")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- LIKE ----------
@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("id", "liked_by", "content_type", "object_id", "created_at")
    search_fields = ("liked_by__user__name",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- FOLLOW ----------
@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__user__name", "following__user__name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- UNLOCK ----------
@admin.register(Unlock)
class UnlockAdmin(admin.ModelAdmin):
    list_display = ("fan", "feed", "created_at")
    search_fields = ("fan__user__name", "feed__profile__user__name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- FEED TIP ----------
@admin.register(FeedTip)
class FeedTipAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "amount", "created_at")
    search_fields = ("sender__user__name", "receiver__user__name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- STORY ----------
@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("profile", "created_at")
    search_fields = ("profile__user__name",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- STORY ITEM ----------
@admin.register(StoryItem)
class StoryItemAdmin(admin.ModelAdmin):
    list_display = ("story", "file", "expired_at", "is_active", "created_at")
    search_fields = ("story__profile__user__name",)
    readonly_fields = ("created_at",)
    list_filter = ("is_active",)
    ordering = ("-created_at",)
    list_per_page = 50


# ---------- TOP FAN ----------
@admin.register(TopFan)
class TopFanAdmin(admin.ModelAdmin):
    list_display = ("fan", "creator", "score", "last_interacted", "status")
    search_fields = ("fan__user__name", "creator__user__name")
    list_filter = ("status",)
    ordering = ("-score", "-last_interacted")
    readonly_fields = ("last_interacted",)
    list_per_page = 50
