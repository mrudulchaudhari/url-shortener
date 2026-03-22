from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for custom User model."""

    list_display = [
        'username',
        'email',
        'is_premium',
        'total_urls',
        'is_staff',
        'is_active',
        'created_at'
    ]
    list_filter = ['is_premium', 'is_staff', 'is_active', 'created_at']
    search_fields = ['username', 'email']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('is_premium', 'api_key', 'created_at', 'updated_at')
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'api_key']

    def total_urls(self, obj):
        """Display total URLs created by user."""
        return obj.urls.filter(is_active=True).count()
    total_urls.short_description = 'Total URLs'
