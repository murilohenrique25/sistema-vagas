"""Redis connection configuration for cache and task queues."""

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

# Connection pool for Redis
redis_pool: ConnectionPool | None = None


async def init_redis_pool() -> None:
    """Initialize the Redis connection pool."""
    global redis_pool
    redis_pool = ConnectionPool.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        decode_responses=True,
    )


async def close_redis_pool() -> None:
    """Close the Redis connection pool."""
    global redis_pool
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None


def get_redis() -> Redis:
    """Get a Redis client instance from the pool.

    Returns:
        Redis client connected to the configured Redis instance.

    Raises:
        RuntimeError: If the Redis pool has not been initialized.
    """
    if redis_pool is None:
        raise RuntimeError(
            "Redis pool not initialized. Call init_redis_pool() first."
        )
    return Redis(connection_pool=redis_pool)
