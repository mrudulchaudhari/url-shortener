import os
import json
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

DEFAULT_TTL = int(os.getenv("CACHE_TTL", "3600"))