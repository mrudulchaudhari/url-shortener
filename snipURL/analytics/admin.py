from django.contrib import admin
from .models import ClickEvent


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = ('url', 'device_type', 'browser', 'country', 'clicked_at')
    list_filter = ('device_type', 'browser', 'country', 'clicked_at')
    search_fields = ('url__short_code', 'ip_address', 'referrer')
    readonly_fields = ('id', 'clicked_at')
    date_hierarchy = 'clicked_at'
