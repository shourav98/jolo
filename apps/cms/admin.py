# legal/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import InfoSection, DataDeletionRequest


@admin.register(InfoSection)
class InfoSectionAdmin(ModelAdmin):
    list_display = ['page', 'title', 'order', 'is_active', 'content']
    list_filter = ['page', 'is_active']
    search_fields = ['title', 'content']


@admin.register(DataDeletionRequest)
class DataDeletionRequestAdmin(ModelAdmin):
    list_display = ['user', 'reason', 'email', 'status', 'created_at', 'processed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'email', 'reason']
    readonly_fields = ['created_at', 'processed_at']