"""Session management using Redis with 24-hour expiration.

Provides user session storage backed by Redis. If Redis is unavailable,
session operations fail silently and the application continues to function
using JWT-based auth as the primary mechanism.
"""

import json
import logging
from typing import Any
from uuid import UUID

from app.core.config import settings

logger = logging.getLogger(__name__)

# Session key prefix
SESSION_PREFIX = "session:"

# Session TTL: 24 hours (86400 seconds)
SESSION_TTL = settings.redis_session_ttl


async def create_session(user_id: UUID, session_data: dict[str, Any]) -> str | None:
    """Create a new user session in Redis with 24h expiration.

    Args:
        user_id: The user's unique identifier.
        session_data: Dictionary with session metadata (e.g., role, ip, user_agent).

    Returns:
        The session key if created successfully, None if Redis is unavailable.
    """
    try:
        import uuid as uuid_mod

        from app.core.redis import get_redis

        session_id = str(uuid_mod.uuid4())
        key = f"{SESSION_PREFIX}{session_id}"

        payload = {
            "user_id": str(user_id),
            **session_data,
        }

        redis = get_redis()
        await redis.set(key, json.dumps(payload, default=str), ex=SESSION_TTL)

        # Also maintain a user-to-sessions index for cleanup
        user_sessions_key = f"user_sessions:{user_id}"
        await redis.sadd(user_sessions_key, session_id)
        await redis.expire(user_sessions_key, SESSION_TTL)

        logger.debug("Session created: %s for user %s", session_id, user_id)
        return session_id
    except Exception as e:
        logger.warning("create_session failed for user %s: %s", user_id, e)
        return None


async def get_session(session_id: str) -> dict[str, Any] | None:
    """Retrieve session data from Redis.

    Args:
        session_id: The session identifier.

    Returns:
        Session data dictionary if found and valid, None otherwise.
    """
    try:
        from app.core.redis import get_redis

        key = f"{SESSION_PREFIX}{session_id}"
        redis = get_redis()
        raw = await redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning("get_session failed for session %s: %s", session_id, e)
        return None


async def refresh_session(session_id: str) -> bool:
    """Refresh the session TTL (extend by another 24h).

    Args:
        session_id: The session identifier to refresh.

    Returns:
        True if refreshed successfully, False otherwise.
    """
    try:
        from app.core.redis import get_redis

        key = f"{SESSION_PREFIX}{session_id}"
        redis = get_redis()
        result = await redis.expire(key, SESSION_TTL)
        return bool(result)
    except Exception as e:
        logger.warning("refresh_session failed for session %s: %s", session_id, e)
        return False


async def destroy_session(session_id: str) -> bool:
    """Destroy a session (logout).

    Args:
        session_id: The session identifier to destroy.

    Returns:
        True if destroyed successfully, False otherwise.
    """
    try:
        from app.core.redis import get_redis

        key = f"{SESSION_PREFIX}{session_id}"
        redis = get_redis()

        # Get user_id before deleting to clean up user sessions index
        raw = await redis.get(key)
        if raw:
            data = json.loads(raw)
            user_id = data.get("user_id")
            if user_id:
                user_sessions_key = f"user_sessions:{user_id}"
                await redis.srem(user_sessions_key, session_id)

        deleted = await redis.delete(key)
        return bool(deleted)
    except Exception as e:
        logger.warning("destroy_session failed for session %s: %s", session_id, e)
        return False


async def destroy_user_sessions(user_id: UUID) -> int:
    """Destroy all sessions for a user (force logout everywhere).

    Args:
        user_id: The user whose sessions should be destroyed.

    Returns:
        Number of sessions destroyed.
    """
    try:
        from app.core.redis import get_redis

        redis = get_redis()
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = await redis.smembers(user_sessions_key)

        destroyed = 0
        for sid in session_ids:
            key = f"{SESSION_PREFIX}{sid}"
            if await redis.delete(key):
                destroyed += 1

        await redis.delete(user_sessions_key)
        return destroyed
    except Exception as e:
        logger.warning("destroy_user_sessions failed for user %s: %s", user_id, e)
        return 0
