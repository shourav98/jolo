from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ChatSession, Message, MessageReaction

# Register your models here.
@admin.register(Message)
class MessagingAdmin(ModelAdmin):
    list_display = ('id', 'session', 'sender', 'message_type', 'content', 'created_at', 'is_read')
    list_filter = ('message_type', 'created_at', 'is_read')
    search_fields = ('content', 'sender__name', 'session__id')
    ordering = ('-created_at',)


@admin.register(MessageReaction)
class MessageReactionAdmin(ModelAdmin):
    list_display = ('id', 'message', 'user', 'reaction', 'created_at')
    list_filter = ('reaction', 'created_at')
    search_fields = ('message__content', 'user__name')
    ordering = ('-created_at',)



@admin.register(ChatSession)
class ChatSessionAdmin(ModelAdmin):
    list_display = ('id', 'creator', 'fan', 'created_at', 'free_window_until')
    list_filter = ('created_at', 'free_window_until')
    search_fields = ('creator__name', 'fan__name', 'id')
    ordering = ('-created_at',)

