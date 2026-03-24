"""
Middleware for monitoring and performance tracking.
"""
import time
import logging
from django.core.cache import cache

logger = logging.getLogger('performance')


class PerformanceMonitoringMiddleware:
    """
    Middleware to track request performance.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip monitoring for redirects (performance critical)
        path = request.path
        is_redirect = (
            not path.startswith('/admin/') and
            not path.startswith('/api/') and
            not path.startswith('/auth/') and
            not path.startswith('/shorten') and
            not path.startswith('/healthz') and
            not path.startswith('/stats') and
            not path.endswith('/qr.png')
        )

        if is_redirect:
            # Fast path for redirects - no monitoring
            return self.get_response(request)

        # Start timer for non-redirect paths
        start_time = time.time()

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log performance
        logger.info(
            f"Request: {request.method} {request.path}",
            extra={
                'method': request.method,
                'path': request.path,
                'duration': duration,
                'status_code': response.status_code,
                'user': str(request.user) if request.user.is_authenticated else 'anonymous'
            }
        )

        # Track slow requests
        if duration > 1.0:  # Requests taking more than 1 second
            logger.warning(
                f"Slow request: {request.method} {request.path} took {duration:.2f}s"
            )

        # Add performance header
        response['X-Response-Time'] = f"{duration:.4f}s"

        return response


class CacheHitRateMiddleware:
    """
    Middleware to track cache hit rates.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Track cache hits/misses
        if hasattr(request, 'cache_hit'):
            cache.incr('cache_hits', delta=1)
        else:
            cache.incr('cache_misses', delta=1)

        response = self.get_response(request)
        return response


class HealthCheckMiddleware:
    """
    Middleware to provide health check information.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/health':
            from django.http import JsonResponse
            from django.db import connection

            health_status = {
                'status': 'healthy',
                'checks': {}
            }

            # Check database
            try:
                connection.ensure_connection()
                health_status['checks']['database'] = 'ok'
            except Exception as e:
                health_status['status'] = 'unhealthy'
                health_status['checks']['database'] = f'error: {str(e)}'

            # Check Redis
            try:
                cache.set('health_check', 'ok', 10)
                cache.get('health_check')
                health_status['checks']['redis'] = 'ok'
            except Exception as e:
                health_status['status'] = 'unhealthy'
                health_status['checks']['redis'] = f'error: {str(e)}'

            return JsonResponse(health_status)

        response = self.get_response(request)
        return response
