from rest_framework import serializers
from django.utils import timezone
from .models import ShortenedURL


class ShortenURLSerializer(serializers.Serializer):
    """Serializer for creating shortened URLs."""
    url = serializers.URLField(required=True, help_text="Original long URL to shorten")
    custom = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=50,
        help_text="Optional custom alias"
    )
    expires_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Optional expiration timestamp"
    )

    def validate_custom(self, value):
        """Validate custom code."""
        if value:
            if ShortenedURL.objects.filter(short_code=value).exists():
                raise serializers.ValidationError("Custom code already exists")
        return value

    def validate_expires_at(self, value):
        """Validate expiration date is in the future."""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiration date must be in the future")
        return value


class ShortenedURLSerializer(serializers.ModelSerializer):
    """Serializer for ShortenedURL model."""
    is_expired = serializers.ReadOnlyField()
    effective_code = serializers.ReadOnlyField()

    class Meta:
        model = ShortenedURL
        fields = (
            'id', 'short_code', 'effective_code', 'original_url',
            'custom_alias', 'expires_at', 'is_active', 'is_expired',
            'click_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'short_code', 'click_count', 'created_at', 'updated_at')


class UpdateURLSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortenedURL
        fields = ('is_active', 'expires_at')
