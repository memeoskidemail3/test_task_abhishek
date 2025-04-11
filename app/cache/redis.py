import os
import json
from typing import Any, Optional
import redis.asyncio as redis
from loguru import logger

# Initialize Redis connection
redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

# Cache TTL in seconds (2 minutes)
CACHE_TTL = 120

async def get_cache_key(netuid: Optional[int] = None, hotkey: Optional[str] = None) -> str:
    """Generate a cache key for the dividend data."""
    if netuid is not None and hotkey is not None:
        return f"dividend:{netuid}:{hotkey}"
    elif netuid is not None:
        return f"dividend:{netuid}:all"
    else:
        return f"dividend:all"

async def get_cached_data(key: str) -> Optional[dict]:
    """Retrieve data from Redis cache."""
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Redis cache error: {str(e)}")
        return None

async def set_cached_data(key: str, data: Any) -> bool:
    """Store data in Redis cache with TTL."""
    try:
        await redis_client.set(key, json.dumps(data), ex=CACHE_TTL)
        return True
    except Exception as e:
        logger.error(f"Redis cache error: {str(e)}")
        return False

async def check_redis_connection() -> bool:
    """Check if Redis connection is working."""
    try:
        return await redis_client.ping()
    except Exception as e:
        logger.error(f"Redis connection error: {str(e)}")
        return False