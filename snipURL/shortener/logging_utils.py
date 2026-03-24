"""
Logging utilities and helpers.
"""
import logging
import time
from functools import wraps
from django.core.cache import cache

logger = logging.getLogger('shortener')
performance_logger = logging.getLogger('performance')


def log_execution_time(func):
    """
    Decorator to log function execution time.

    Usage:
        @log_execution_time
        def my_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            performance_logger.info(
                f'Function {func.__name__} executed',
                extra={
                    'function': func.__name__,
                    'duration': duration,
                    'status': 'success'
                }
            )

            return result
        except Exception as e:
            duration = time.time() - start_time

            performance_logger.error(
                f'Function {func.__name__} failed',
                extra={
                    'function': func.__name__,
                    'duration': duration,
                    'status': 'error',
                    'error': str(e)
                }
            )

            raise

    return wrapper


def log_user_action(action, user, details=None):
    """
    Log a user action with structured data.

    Args:
        action (str): Action name (e.g., 'create_url', 'login')
        user: User object or user ID
        details (dict): Additional details to log
    """
    user_id = user.id if hasattr(user, 'id') else user
    username = user.username if hasattr(user, 'username') else 'anonymous'

    log_data = {
        'action': action,
        'user_id': user_id,
        'username': username,
    }

    if details:
        log_data.update(details)

    logger.info(
        f'User action: {action}',
        extra=log_data
    )


def log_security_event(event_type, details=None, level='WARNING'):
    """
    Log a security-related event.

    Args:
        event_type (str): Type of security event
        details (dict): Event details
        level (str): Log level (WARNING, ERROR, CRITICAL)
    """
    security_logger = logging.getLogger('security')

    log_data = {
        'event_type': event_type,
        'timestamp': time.time()
    }

    if details:
        log_data.update(details)

    log_method = getattr(security_logger, level.lower())
    log_method(
        f'Security event: {event_type}',
        extra=log_data
    )


def log_api_call(endpoint, method, user=None, response_code=None, duration=None):
    """
    Log an API call with details.

    Args:
        endpoint (str): API endpoint
        method (str): HTTP method
        user: User object (optional)
        response_code (int): HTTP response code (optional)
        duration (float): Request duration in seconds (optional)
    """
    log_data = {
        'endpoint': endpoint,
        'method': method,
        'response_code': response_code,
        'duration': duration
    }

    if user:
        log_data['user_id'] = user.id if hasattr(user, 'id') else str(user)

    logger.info(
        f'API call: {method} {endpoint}',
        extra=log_data
    )


def track_metric(metric_name, value=1, tags=None):
    """
    Track a metric in Redis for monitoring.

    Args:
        metric_name (str): Name of the metric
        value (int/float): Value to track
        tags (dict): Optional tags for the metric
    """
    from datetime import datetime

    # Create metric key with timestamp (hourly buckets)
    hour = datetime.now().strftime('%Y%m%d%H')
    key = f"metrics:{metric_name}:{hour}"

    # Increment counter
    try:
        cache.incr(key, delta=value)
        # Set expiry to 7 days
        cache.expire(key, 86400 * 7)

        # Log metric
        performance_logger.info(
            f'Metric tracked: {metric_name}',
            extra={
                'metric': metric_name,
                'value': value,
                'tags': tags,
                'hour': hour
            }
        )
    except Exception as e:
        logger.error(f'Failed to track metric {metric_name}: {str(e)}')


def get_metric_summary(metric_name, hours=24):
    """
    Get summary of a metric for the last N hours.

    Args:
        metric_name (str): Name of the metric
        hours (int): Number of hours to look back

    Returns:
        dict: Summary with total, average, min, max
    """
    from datetime import datetime, timedelta

    values = []
    for i in range(hours):
        hour = (datetime.now() - timedelta(hours=i)).strftime('%Y%m%d%H')
        key = f"metrics:{metric_name}:{hour}"
        value = cache.get(key, 0)
        values.append(value)

    if not values or sum(values) == 0:
        return {
            'total': 0,
            'average': 0,
            'min': 0,
            'max': 0,
            'hours': hours
        }

    return {
        'total': sum(values),
        'average': sum(values) / len(values),
        'min': min(values),
        'max': max(values),
        'hours': hours
    }


class LogContext:
    """
    Context manager for structured logging with timing.

    Usage:
        with LogContext('database_query', user_id=123):
            # ... do work ...
            pass
    """

    def __init__(self, operation, **context):
        self.operation = operation
        self.context = context
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        logger.debug(
            f'Starting: {self.operation}',
            extra={'operation': self.operation, **self.context}
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if exc_type is None:
            logger.info(
                f'Completed: {self.operation}',
                extra={
                    'operation': self.operation,
                    'duration': duration,
                    'status': 'success',
                    **self.context
                }
            )
        else:
            logger.error(
                f'Failed: {self.operation}',
                extra={
                    'operation': self.operation,
                    'duration': duration,
                    'status': 'error',
                    'error': str(exc_val),
                    **self.context
                },
                exc_info=True
            )


def mask_sensitive_data(data, fields=['password', 'api_key', 'secret', 'token']):
    """
    Mask sensitive fields in data before logging.

    Args:
        data (dict): Data to mask
        fields (list): List of field names to mask

    Returns:
        dict: Data with masked sensitive fields
    """
    if not isinstance(data, dict):
        return data

    masked = data.copy()
    for field in fields:
        if field in masked:
            value = str(masked[field])
            # Show first 4 chars, mask the rest
            if len(value) > 4:
                masked[field] = value[:4] + '*' * (len(value) - 4)
            else:
                masked[field] = '****'

    return masked


# Example usage in views
def example_usage():
    """
    Example of how to use logging utilities.
    """
    # 1. Log user action
    log_user_action('create_url', request.user, {
        'code': 'abc123',
        'original_url': 'https://example.com'
    })

    # 2. Use decorator
    @log_execution_time
    def expensive_operation():
        # ... do work ...
        pass

    # 3. Use context manager
    with LogContext('database_query', query='SELECT * FROM urls'):
        results = Url.objects.all()

    # 4. Track metrics
    track_metric('urls_created', 1)
    track_metric('api_calls', 1, tags={'endpoint': '/shorten'})

    # 5. Log security event
    log_security_event('failed_login', {
        'username': 'admin',
        'ip_address': '1.2.3.4'
    }, level='WARNING')

    # 6. Mask sensitive data
    user_data = {
        'username': 'john',
        'password': 'secret123',
        'email': 'john@example.com'
    }
    safe_data = mask_sensitive_data(user_data)
    logger.info('User data', extra=safe_data)

    # 7. Get metric summary
    summary = get_metric_summary('urls_created', hours=24)
    logger.info(f'URLs created in last 24h: {summary["total"]}')
