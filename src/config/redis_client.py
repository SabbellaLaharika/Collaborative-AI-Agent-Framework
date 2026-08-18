import redis
from src.config.settings import settings

_redis_client = None

def get_redis_client() -> redis.Redis:
    """Returns a singleton Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client
