from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model with additional fields.
    """
    email = models.EmailField(
        unique=True,
        help_text="Email address"
    )
    api_key = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="API key for programmatic access"
    )
    is_premium = models.BooleanField(
        default=False,
        help_text="Premium user status"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return self.username
