import os
import json
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

DEFAULT_TTL = int(os.getenv("CACHE_TTL", "3600"))


def cache_set_code(code: str, payload: dict,ttl: int = DEFAULT_TTL):
    """Store code -> payload in Redis with TTl

    Payload contains original_url, expires_at, is_active, url_id.
       """

    key = f"code:{code}"
    r.set(key, json.dumps(payload), ex=ttl)


def cache_get_code(code: str):
    """Attempt to get cached payload for a code.

    Returns parsed payload dict or None on miss.
    """
    key = f"code:{code}"
    v = r.get(key)
    return json.loads(v) if v else None


def increment_click_redis(url_id:int, delta: int = 1):
    """Increment click counter for a URL in Redis (buffer).
    Uses a single hash 'clicks' and a set 'clicks_pending' to track which url_ids
    have buffered counts to be flushed by a background job.
    """
    r.hincrby("clicks", url_id, delta)
    r.sadd("clicks_pending", url_id)


def get_buffered_clicks_total() -> int:
    """Return total buffered clicks currently in Redis (integer sum)."""
    vals = r.hvals("clicks") or []
    return sum(int(v) for v in vals)