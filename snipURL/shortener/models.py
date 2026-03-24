import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class ShortenedURL(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short_code = models.CharField(max_length=10, unique=True, db_index=True)
    original_url = models.TextField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shortened_urls'
    )
    custom_alias = models.CharField(max_length=50, unique=True, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    click_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shortened_urls'
        indexes = [
            models.Index(fields=['short_code']),
            models.Index(fields=['user', '-created_at']),
        ]
        ordering = ['-created_at']

    @property
    def is_expired(self):
        """Check if URL has expired"""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    @property
    def effective_code(self):
        """Return custom_alias if set, otherwise short_code"""
        return self.custom_alias or self.short_code

    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"
