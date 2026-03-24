import uuid
from django.db import models
from shortener.models import ShortenedURL


class ClickEvent(models.Model):
    DEVICE_CHOICES = [
        ('mobile', 'Mobile'),
        ('desktop', 'Desktop'),
        ('tablet', 'Tablet'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.ForeignKey(
        ShortenedURL,
        on_delete=models.CASCADE,
        related_name='click_events'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.TextField(blank=True)
    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES, default='other')
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'click_events'
        indexes = [
            models.Index(fields=['url', '-clicked_at']),
            models.Index(fields=['clicked_at']),
        ]
        ordering = ['-clicked_at']

    def __str__(self):
        return f"Click on {self.url.short_code} at {self.clicked_at}"
