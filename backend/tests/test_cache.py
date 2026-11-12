"""Tests for Redis cache utility and job search caching behavior."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cache import (
    MAX_CACHE_TTL,
    build_job_search_cache_key,
    cache_get,
    cache_invalidate,
    cache_set,
)


class TestCacheGet:
    """Tests for cache_get function."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data(self):
        """Cache hit returns deserialized cached data."""
        expected_data = {"items": [{"id": "123", "title": "Dev Python"}], "total": 1}
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(expected_data))

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await cache_get("jobs:search:abc123")

        assert result == expected_data
        mock_redis.get.assert_called_once_with("jobs:search:abc123")

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        """Cache miss (key not found) returns None."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await cache_get("jobs:search:nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_redis_unavailable_returns_none(self):
        """When Redis is unavailable, cache_get returns None (graceful fallback)."""
        with patch("app.core.redis.get_redis", side_effect=RuntimeError("Redis pool not initialized")):
            result = await cache_get("jobs:search:any")

        assert result is None

    @pytest.mark.asyncio
    async def test_redis_connection_error_returns_none(self):
        """When Redis connection fails, cache_get returns None."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=ConnectionError("Connection refused"))

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await cache_get("jobs:search:any")

        assert result is None


class TestCacheSet:
    """Tests for cache_set function."""

    @pytest.mark.asyncio
    async def test_cache_set_stores_value_with_ttl(self):
        """cache_set stores serialized value with correct TTL."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)

        data = {"items": [], "total": 0}

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await cache_set("jobs:search:key1", data, ttl=300)

        assert result is True
        mock_redis.set.assert_called_once_with(
            "jobs:search:key1", json.dumps(data, default=str), ex=300
        )

    @pytest.mark.asyncio
    async def test_cache_set_caps_ttl_at_max(self):
        """cache_set caps TTL at MAX_CACHE_TTL (300s)."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await cache_set("key", {"data": 1}, ttl=600)

        assert result is True
        # TTL should be capped at 300
        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == MAX_CACHE_TTL

    @pytest.mark.asyncio
    async def test_cache_set_redis_unavailable_returns_false(self):
        """When Redis is unavailable, cache_set returns False (silent failure)."""
        with patch("app.core.redis.get_redis", side_effect=RuntimeError("Redis pool not initialized")):
            result = await cache_set("key", {"data": 1})

        assert result is False

    @pytest.mark.asyncio
    async def test_cache_set_connection_error_returns_false(self):
        """When Redis connection fails, cache_set returns False."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(side_effect=ConnectionError("Connection refused"))

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await cache_set("key", {"data": 1})

        assert result is False


class TestCacheInvalidate:
    """Tests for cache_invalidate function."""

    @pytest.mark.asyncio
    async def test_cache_invalidate_deletes_matching_keys(self):
        """cache_invalidate removes all keys matching the pattern."""
        mock_redis = AsyncMock()

        async def mock_scan_iter(match=None):
            for key in ["jobs:search:a", "jobs:search:b"]:
                yield key

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.delete = AsyncMock(return_value=1)

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            result = await cache_invalidate("jobs:search:*")

        assert result == 2
        assert mock_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_invalidate_redis_unavailable_returns_zero(self):
        """When Redis is unavailable, cache_invalidate returns 0."""
        with patch("app.core.redis.get_redis", side_effect=RuntimeError("Redis pool not initialized")):
            result = await cache_invalidate("jobs:search:*")

        assert result == 0


class TestBuildJobSearchCacheKey:
    """Tests for build_job_search_cache_key function."""

    def test_same_params_produce_same_key(self):
        """Same search parameters produce the same cache key."""
        key1 = build_job_search_cache_key(q="python", page=1, page_size=20)
        key2 = build_job_search_cache_key(q="python", page=1, page_size=20)
        assert key1 == key2

    def test_different_params_produce_different_keys(self):
        """Different search parameters produce different cache keys."""
        key1 = build_job_search_cache_key(q="python", page=1)
        key2 = build_job_search_cache_key(q="java", page=1)
        assert key1 != key2

    def test_different_pages_produce_different_keys(self):
        """Different page numbers produce different cache keys."""
        key1 = build_job_search_cache_key(q="python", page=1)
        key2 = build_job_search_cache_key(q="python", page=2)
        assert key1 != key2

    def test_key_starts_with_prefix(self):
        """Cache key starts with the 'jobs:search:' prefix."""
        key = build_job_search_cache_key(q="test")
        assert key.startswith("jobs:search:")


class TestCacheFallbackBehavior:
    """Tests verifying the fallback behavior when Redis is down."""

    @pytest.mark.asyncio
    async def test_full_flow_cache_miss_then_db_query(self):
        """When cache misses, the flow proceeds to DB query (simulated)."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Cache miss
        mock_redis.set = AsyncMock(return_value=True)  # Cache set succeeds

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            # Simulate the flow: cache_get returns None -> app queries DB
            result = await cache_get("jobs:search:somekey")
            assert result is None  # This means the app should query DB

            # After DB query, result is cached
            db_result = {"items": [{"title": "Job 1"}], "total": 1}
            success = await cache_set("jobs:search:somekey", db_result, ttl=300)
            assert success is True

    @pytest.mark.asyncio
    async def test_full_flow_redis_down_fallback(self):
        """When Redis is completely down, both get and set fail silently."""
        with patch("app.core.redis.get_redis", side_effect=RuntimeError("Redis pool not initialized")):
            # cache_get fails silently -> app falls through to DB
            result = await cache_get("jobs:search:somekey")
            assert result is None

            # cache_set also fails silently -> no error raised
            success = await cache_set("jobs:search:somekey", {"data": 1}, ttl=300)
            assert success is False
