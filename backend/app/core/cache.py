"""Cache utility wrapping Redis with graceful fallback.

All operations are wrapped in try/except so that if Redis is unavailable,
the application continues to function by falling through to direct DB queries.
"""

import json
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Maximum allowed TTL (seconds) per design: 300s
MAX_CACHE_TTL = 300


async def cache_get(key: str) -> Any | None:
    """Get a cached value by key.

    Returns the deserialized value if found, or None if:
    - Key does not exist
    - Redis is unavailable
    - Deserialization fails

    Args:
        key: The cache key to look up.

    Returns:
        The cached value (deserialized from JSON) or None.
    """
    try:
        from app.core.redis import get_redis

        redis = get_redis()
        raw = await redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning("cache_get failed for key '%s': %s", key, e)
        return None


async def cache_set(key: str, value: Any, ttl: int = settings.redis_cache_ttl) -> bool:
    """Set a cache value with TTL.

    The TTL is capped at MAX_CACHE_TTL (300 seconds) per design requirements.
    If Redis is unavailable, the operation silently fails.

    Args:
        key: The cache key.
        value: The value to cache (must be JSON-serializable).
        ttl: Time-to-live in seconds (default from settings, max 300s).

    Returns:
        True if the value was cached successfully, False otherwise.
    """
    try:
        from app.core.redis import get_redis

        # Enforce max TTL
        effective_ttl = min(ttl, MAX_CACHE_TTL)

        redis = get_redis()
        serialized = json.dumps(value, default=str)
        await redis.set(key, serialized, ex=effective_ttl)
        return True
    except Exception as e:
        logger.warning("cache_set failed for key '%s': %s", key, e)
        return False


async def cache_invalidate(pattern: str) -> int:
    """Invalidate cache keys matching a pattern.

    Uses Redis SCAN + DELETE to remove keys matching the given pattern.
    If Redis is unavailable, the operation silently fails.

    Args:
        pattern: Glob-style pattern for keys to invalidate (e.g., "jobs:search:*").

    Returns:
        Number of keys deleted, or 0 if Redis is unavailable.
    """
    try:
        from app.core.redis import get_redis

        redis = get_redis()
        deleted_count = 0
        async for key in redis.scan_iter(match=pattern):
            await redis.delete(key)
            deleted_count += 1
        return deleted_count
    except Exception as e:
        logger.warning("cache_invalidate failed for pattern '%s': %s", pattern, e)
        return 0


def build_job_search_cache_key(
    q: str | None = None,
    modality: str | None = None,
    location: str | None = None,
    salary_min: Any = None,
    salary_max: Any = None,
    contract_type: str | None = None,
    sort_by: str = "date",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Build a deterministic cache key for job search results.

    Args:
        All search parameters used to uniquely identify a query.

    Returns:
        A string cache key like "jobs:search:<hash_of_params>".
    """
    import hashlib

    params = (
        f"q={q or ''}|mod={modality or ''}|loc={location or ''}|"
        f"smin={salary_min or ''}|smax={salary_max or ''}|"
        f"ct={contract_type or ''}|sort={sort_by}|order={sort_order}|"
        f"page={page}|size={page_size}"
    )
    key_hash = hashlib.md5(params.encode()).hexdigest()
    return f"jobs:search:{key_hash}"
