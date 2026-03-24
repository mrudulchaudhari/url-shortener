from django.contrib import admin
from .models import ShortenedURL


@admin.register(ShortenedURL)
class ShortenedURLAdmin(admin.ModelAdmin):
    list_display = ('short_code', 'original_url', 'user', 'click_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('short_code', 'original_url', 'custom_alias')
    readonly_fields = ('id', 'created_at', 'updated_at', 'click_count')
    date_hierarchy = 'created_at'
