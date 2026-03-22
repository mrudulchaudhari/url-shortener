from django.db import models
from django.utils import timezone
from django.conf import settings


class Url(models.Model):
    """
    Stores shortened URL mappings.
    Supports both auto-generated base62 codes and custom aliases.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='urls',
        help_text="Owner of the URL (null for anonymous)"
    )
    code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Short code or custom alias"
    )
    original_url = models.TextField(
        help_text="Original long URL (normalized)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Expiration timestamp (null = never expires)"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Soft delete flag"
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Public URL (visible in user's public profile)"
    )
    password = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Optional password protection (hashed)"
    )

    class Meta:
        db_table = 'urls'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.code} -> {self.original_url[:50]}"

    def is_expired(self):
        """Check if URL has expired."""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at


class URLStats(models.Model):
    """
    Aggregates click counts per URL.
    Updated by background worker that flushes buffered Redis counts.
    """
    url = models.OneToOneField(
        Url,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='stats'
    )
    total_clicks = models.BigIntegerField(
        default=0,
        help_text="Total number of clicks/redirects"
    )
    last_flushed = models.DateTimeField(
        auto_now=True,
        help_text="Last time Redis buffer was flushed to this record"
    )

    class Meta:
        db_table = 'url_stats'
        verbose_name = 'URL Statistics'
        verbose_name_plural = 'URL Statistics'

    def __str__(self):
        return f"{self.url.code}: {self.total_clicks} clicks"
