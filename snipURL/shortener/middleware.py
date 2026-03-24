"""
Middleware for rate limiting and request processing.
"""
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import hashlib


class RateLimitMiddleware:
    """
    Simple rate limiting middleware using Redis cache.

    Limits requests per IP address per time window.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Configure rate limits for different endpoints
        # Format: {path: {'anonymous': {requests, window}, 'authenticated': {requests, window}}}
        self.rate_limits = {
            '/shorten': {
                'anonymous': {'requests': 5, 'window': 3600},      # 5 per hour for anonymous
                'authenticated': {'requests': 30, 'window': 3600}  # 30 per hour for logged in
            },
            'default': {
                'anonymous': {'requests': 50, 'window': 60},       # 50 per minute
                'authenticated': {'requests': 200, 'window': 60}   # 200 per minute
            }
        }

    def __call__(self, request):
        path = request.path

        # Skip rate limiting for certain paths (including redirects for speed)
        skip_paths = (
            path.startswith('/admin/') or
            path == '/healthz' or
            path == '/health' or
            # Skip rate limiting for redirects (already limited at /shorten)
            (not path.startswith('/shorten') and
             not path.startswith('/api/') and
             not path.startswith('/auth/') and
             not path.startswith('/analytics/'))
        )

        if skip_paths:
            return self.get_response(request)

        # Get client IP
        ip = self.get_client_ip(request)

        # Check if user is authenticated
        is_authenticated = request.user.is_authenticated if hasattr(request, 'user') else False

        # Check rate limit
        if self.is_rate_limited(request.path, ip, is_authenticated):
            return JsonResponse({
                'error': 'Rate limit exceeded. Please try again later.' +
                         (' Login for higher limits!' if not is_authenticated else '')
            }, status=429)

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def is_rate_limited(self, path, ip, is_authenticated):
        """
        Check if request should be rate limited.

        Args:
            path: Request path
            ip: Client IP address
            is_authenticated: Whether user is authenticated

        Returns:
            bool: True if rate limit exceeded, False otherwise
        """
        try:
            # Get rate limit config for path
            path_config = self.rate_limits.get(path, self.rate_limits['default'])

            # Choose config based on authentication status
            user_type = 'authenticated' if is_authenticated else 'anonymous'
            config = path_config[user_type]

            max_requests = config['requests']
            window_seconds = config['window']

            # Create cache key with user type
            cache_key = f"ratelimit:{path}:{user_type}:{ip}"

            # Get current count
            current = cache.get(cache_key, 0)

            if current >= max_requests:
                return True

            # Increment counter
            if current == 0:
                # First request in window - set expiry
                cache.set(cache_key, 1, window_seconds)
            else:
                # Increment existing counter
                cache.incr(cache_key)

            return False
        except Exception:
            # If cache is unavailable, don't block requests
            return False
