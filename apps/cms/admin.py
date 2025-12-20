# legal/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import InfoSection


@admin.register(InfoSection)
class LegalPageAdmin(ModelAdmin):
    list_display = ('title', 'page', 'is_active', 'content', 'order')
    list_filter = ('page', 'is_active')