from django.contrib import admin
from .models import Url, URLStats


@admin.register(Url)
class UrlAdmin(admin.ModelAdmin):
    """Admin interface for URL model."""
    list_display = ['code', 'original_url_short', 'created_at', 'expires_at', 'is_active', 'click_count']
    list_filter = ['is_active', 'created_at', 'expires_at']
    search_fields = ['code', 'original_url']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    def original_url_short(self, obj):
        """Display shortened version of original URL."""
        return obj.original_url[:50] + '...' if len(obj.original_url) > 50 else obj.original_url
    original_url_short.short_description = 'Original URL'

    def click_count(self, obj):
        """Display total clicks from stats."""
        try:
            return obj.stats.total_clicks
        except URLStats.DoesNotExist:
            return 0
    click_count.short_description = 'Total Clicks'


@admin.register(URLStats)
class URLStatsAdmin(admin.ModelAdmin):
    """Admin interface for URL statistics."""
    list_display = ['url_code', 'total_clicks', 'last_flushed']
    readonly_fields = ['url', 'last_flushed']
    ordering = ['-total_clicks']

    def url_code(self, obj):
        """Display the short code."""
        return obj.url.code
    url_code.short_description = 'Code'
