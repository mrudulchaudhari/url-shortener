"""
Django REST Framework serializers for URL shortener API.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Url, URLStats
from .utils import validate_custom_code, normalize_url


class ShortenURLSerializer(serializers.Serializer):
    """
    Serializer for creating shortened URLs.
    """
    url = serializers.URLField(
        required=True,
        help_text="Original long URL to shorten"
    )
    custom = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=32,
        help_text="Optional custom alias (alphanumeric, max 32 chars)"
    )
    expires_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Optional expiration timestamp (ISO 8601 format)"
    )

    def validate_url(self, value):
        """Validate and normalize URL."""
        try:
            return normalize_url(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

    def validate_custom(self, value):
        """Validate custom code."""
        if value:
            try:
                validate_custom_code(value)
            except ValueError as e:
                raise serializers.ValidationError(str(e))

            # Check if custom code already exists
            if Url.objects.filter(code=value).exists():
                raise serializers.ValidationError("Custom code already exists")

        return value

    def validate_expires_at(self, value):
        """Validate expiration date is in the future."""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiration date must be in the future")
        return value


class ShortenURLResponseSerializer(serializers.Serializer):
    """
    Serializer for shorten URL response.
    """
    code = serializers.CharField(help_text="Short code")
    short_url = serializers.URLField(help_text="Full short URL")
    qr_base64 = serializers.CharField(help_text="Base64-encoded QR code PNG")


class UrlSerializer(serializers.ModelSerializer):
    """
    Serializer for Url model.
    """
    is_expired = serializers.BooleanField(read_only=True)
    total_clicks = serializers.SerializerMethodField()

    class Meta:
        model = Url
        fields = [
            'id',
            'code',
            'original_url',
            'created_at',
            'expires_at',
            'is_active',
            'is_expired',
            'total_clicks'
        ]
        read_only_fields = ['id', 'code', 'created_at']

    def get_total_clicks(self, obj):
        """Get total clicks from stats."""
        try:
            return obj.stats.total_clicks
        except URLStats.DoesNotExist:
            return 0


class URLStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for URLStats model.
    """
    code = serializers.CharField(source='url.code', read_only=True)
    original_url = serializers.CharField(source='url.original_url', read_only=True)

    class Meta:
        model = URLStats
        fields = [
            'code',
            'original_url',
            'total_clicks',
            'last_flushed'
        ]
        read_only_fields = fields


class StatsResponseSerializer(serializers.Serializer):
    """
    Serializer for global stats response.
    """
    total_urls = serializers.IntegerField(help_text="Total active URLs")
    buffered_clicks = serializers.IntegerField(help_text="Clicks buffered in Redis")
