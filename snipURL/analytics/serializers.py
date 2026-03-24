"""
Serializers for analytics API.
"""
from rest_framework import serializers
from .models import ClickEvent


class ClickEventSerializer(serializers.ModelSerializer):
    """Serializer for ClickEvent model."""

    url_code = serializers.CharField(source='url.code', read_only=True)

    class Meta:
        model = ClickEvent
        fields = [
            'id',
            'url_code',
            'timestamp',
            'ip_address',
            'referer',
            'country',
            'city',
            'browser',
            'os',
            'device_type'
        ]
        read_only_fields = fields


class ClickEventListSerializer(serializers.Serializer):
    """Serializer for list of click events with pagination."""

    count = serializers.IntegerField()
    results = ClickEventSerializer(many=True)


class AnalyticsSummarySerializer(serializers.Serializer):
    """Serializer for analytics summary data."""

    total_clicks = serializers.IntegerField()
    unique_ips = serializers.IntegerField()
    clicks_by_country = serializers.DictField()
    clicks_by_device = serializers.DictField()
    clicks_by_browser = serializers.DictField()
    clicks_over_time = serializers.ListField()
