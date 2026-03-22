"""
Serializers for user authentication and management.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
import secrets

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)

        # Generate API key
        user.api_key = secrets.token_urlsafe(32)
        user.save()

        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details."""

    total_urls = serializers.SerializerMethodField()
    total_clicks = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'is_premium',
            'api_key',
            'created_at',
            'total_urls',
            'total_clicks'
        ]
        read_only_fields = ['id', 'created_at', 'api_key']

    def get_total_urls(self, obj):
        return obj.urls.filter(is_active=True).count()

    def get_total_clicks(self, obj):
        from shortener.models import URLStats
        total = 0
        for url in obj.urls.filter(is_active=True):
            try:
                total += url.stats.total_clicks
            except URLStats.DoesNotExist:
                pass
        return total


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )


class APIKeyRegenerateSerializer(serializers.Serializer):
    """Serializer for API key regeneration."""

    api_key = serializers.CharField(read_only=True)
