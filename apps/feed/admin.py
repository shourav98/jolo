from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Feed, FeedFile, FeedVideo, Comment, Like, Unlike, Story, StoryItem

@admin.register(Feed)
class FeedAdmin(ModelAdmin):
    list_display = ('id', 'profile', 'content', 'total_like', 'total_comment', 'status', 'created_at')
    search_fields = ('content',)
    list_filter = ('status', 'created_at')

@admin.register(FeedFile)
class FeedFileAdmin(ModelAdmin):
    list_display = ('id', 'feed', 'file')
    search_fields = ('feed__content',)

@admin.register(FeedVideo)
class FeedVideoAdmin(ModelAdmin):
    list_display = ('id', 'profile', 'title', 'total_like', 'total_comment', 'total_view', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('created_at',)

@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ('id', 'content_type_id', 'comment_by', 'content', 'created_at')
    search_fields = ('content',)
    list_filter = ('created_at',)

@admin.register(Like)
class LikeAdmin(ModelAdmin):
    list_display = ('id', 'content_type_id', 'liked_by', 'created_at')
    list_filter = ('created_at',)

@admin.register(Unlike)
class UnlikeAdmin(ModelAdmin):
    list_display = ('id', 'content_type_id', 'unliked_by', 'created_at')
    list_filter = ('created_at',)

@admin.register(Story)
class StoryAdmin(ModelAdmin):
    list_display = ('id', 'profile', 'created_at')
    list_filter = ('created_at',)

@admin.register(StoryItem)
class StoryItemAdmin(ModelAdmin):
    list_display = ('id', 'story', 'file', 'created_at', 'expired_at', 'is_active', 'total_view')
    list_filter = ('is_active', 'created_at', 'expired_at')