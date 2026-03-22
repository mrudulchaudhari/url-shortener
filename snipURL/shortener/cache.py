"""
Redis cache utilities for URL shortener.
Implements two-tier caching strategy:
1. Code-to-URL lookups cached in Redis
2. Click counts buffered in Redis before batch DB writes
"""
from django.core.cache import cache
from django.conf import settings
import json


# Cache key format: "code:{short_code}"
CACHE_KEY_PREFIX = "code:"
# Redis hash for buffered click counts
CLICKS_HASH_KEY = "clicks"
# Set of url_ids with pending clicks
CLICKS_PENDING_SET = "clicks_pending"

# Default cache TTL (can be overridden by CACHE_TTL env var)
DEFAULT_CACHE_TTL = getattr(settings, 'CACHE_TTL', 3600)


def get_cache_key(code):
    """
    Generate cache key for a short code.

    Args:
        code (str): Short code

    Returns:
        str: Cache key
    """
    return f"{CACHE_KEY_PREFIX}{code}"


def cache_url(code, url_data, ttl=None):
    """
    Cache URL data in Redis.

    Args:
        code (str): Short code
        url_data (dict): URL data with keys: url_id, original_url, expires_at, is_active
        ttl (int, optional): Cache TTL in seconds. Defaults to DEFAULT_CACHE_TTL.
    """
    try:
        if ttl is None:
            ttl = DEFAULT_CACHE_TTL

        key = get_cache_key(code)

        # Store as JSON
        cache_value = {
            'url_id': url_data['url_id'],
            'original_url': url_data['original_url'],
            'expires_at': url_data['expires_at'].isoformat() if url_data['expires_at'] else None,
            'is_active': url_data['is_active']
        }

        cache.set(key, json.dumps(cache_value), ttl)
    except Exception:
        # Silently fail if cache is unavailable
        pass


def get_cached_url(code):
    """
    Retrieve cached URL data.

    Args:
        code (str): Short code

    Returns:
        dict or None: URL data if cached, None if cache miss
    """
    try:
        key = get_cache_key(code)
        cached = cache.get(key)

        if cached:
            return json.loads(cached)

        return None
    except Exception:
        # Return None if cache is unavailable
        return None


def invalidate_cache(code):
    """
    Remove URL from cache.

    Args:
        code (str): Short code to invalidate
    """
    try:
        key = get_cache_key(code)
        cache.delete(key)
    except Exception:
        # Silently fail if cache is unavailable
        pass


def increment_click_redis(url_id):
    """
    Increment click count in Redis buffer.
    Avoids DB write on every redirect.

    Args:
        url_id (int): URL database ID
    """
    try:
        # Get the Redis client directly for hash operations
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")

        # Increment click count in hash
        redis_conn.hincrby(CLICKS_HASH_KEY, url_id, 1)

        # Add to pending set
        redis_conn.sadd(CLICKS_PENDING_SET, url_id)
    except Exception:
        # Silently fail if Redis is unavailable
        # In production, consider direct DB update or logging
        pass


def get_buffered_clicks():
    """
    Get all buffered click counts from Redis.

    Returns:
        dict: {url_id: click_count} mapping
    """
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")

        clicks_data = redis_conn.hgetall(CLICKS_HASH_KEY)

        # Convert bytes to int
        return {int(k): int(v) for k, v in clicks_data.items()}
    except Exception:
        # Return empty dict if Redis is unavailable
        return {}


def get_buffered_click_count():
    """
    Get total number of buffered clicks across all URLs.

    Returns:
        int: Total buffered clicks
    """
    buffered = get_buffered_clicks()
    return sum(buffered.values())


def read_and_clear_clicks_atomic():
    """
    Atomically read buffered clicks and clear them from Redis.
    This should be called by a background worker to flush clicks to DB.

    Returns:
        dict: {url_id: click_count} mapping of clicks to flush
    """
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")

        # Use pipeline for atomicity
        pipe = redis_conn.pipeline()

        # Get all clicks
        pipe.hgetall(CLICKS_HASH_KEY)

        # Delete the hash and pending set
        pipe.delete(CLICKS_HASH_KEY)
        pipe.delete(CLICKS_PENDING_SET)

        results = pipe.execute()

        clicks_data = results[0]

        # Convert bytes to int
        return {int(k): int(v) for k, v in clicks_data.items()}
    except Exception:
        # Return empty dict if Redis is unavailable
        return {}


def get_pending_url_ids():
    """
    Get set of URL IDs with pending buffered clicks.

    Returns:
        set: Set of url_id integers
    """
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")

        pending = redis_conn.smembers(CLICKS_PENDING_SET)
        return {int(url_id) for url_id in pending}
    except Exception:
        # Return empty set if Redis is unavailable
        return set()
