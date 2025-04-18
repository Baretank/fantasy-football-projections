import pytest
import time
import json
from unittest.mock import patch, MagicMock
from services.cache_service import CacheService, get_cache, _cache_instance


@pytest.fixture(autouse=True)
def reset_cache_singleton():
    """Reset the global cache singleton before each test."""
    global _cache_instance
    _cache_instance = None
    yield
    _cache_instance = None


class TestCacheService:
    def test_get_cache_singleton(self):
        """Test the get_cache function returns a singleton instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    def test_get_miss(self):
        """Test cache miss behavior."""
        cache = CacheService()
        result = cache.get("nonexistent_key")
        assert result is None

    def test_get_hit(self):
        """Test cache hit behavior."""
        cache = CacheService()
        test_value = {"test": "data"}
        cache.set("test_key", test_value)
        result = cache.get("test_key")
        assert result == test_value

    def test_expiration(self):
        """Test cache expiration."""
        cache = CacheService(ttl_seconds=1)
        cache.set("short_lived", "value")
        assert cache.get("short_lived") == "value"
        time.sleep(1.1)  # Wait for expiration
        assert cache.get("short_lived") is None

    def test_custom_ttl_with_mock_time(self):
        """Test custom TTL with mocked time for reliability."""
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0  # Start time

            cache = CacheService(ttl_seconds=300)
            cache.set("default_ttl", "default_value")
            cache.set("custom_ttl", "custom_value", ttl_seconds=1)

            # Both should be available immediately
            assert cache.get("default_ttl") == "default_value"
            assert cache.get("custom_ttl") == "custom_value"

            # Advance time beyond custom TTL
            mock_time.return_value = 1001.5  # Add 1.5 seconds

            assert cache.get("default_ttl") == "default_value"  # Still available
            assert cache.get("custom_ttl") is None  # Should be expired

    def test_delete(self):
        """Test deleting a cache entry."""
        cache = CacheService()
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

        cache.delete("test_key")
        assert cache.get("test_key") is None

    def test_clear(self):
        """Test clearing all cache entries."""
        cache = CacheService()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_clear_pattern(self):
        """Test clearing cache entries by pattern."""
        cache = CacheService()
        cache.set("prefix_key1", "value1")
        cache.set("prefix_key2", "value2")
        cache.set("other_key", "value3")

        removed = cache.clear_pattern("prefix_")
        assert removed == 2
        assert cache.get("prefix_key1") is None
        assert cache.get("prefix_key2") is None
        assert cache.get("other_key") == "value3"

    def test_cleanup(self):
        """Test cleaning up expired entries."""
        cache = CacheService(ttl_seconds=1)
        cache.set("expired1", "value1")
        cache.set("expired2", "value2")
        cache.set("active", "value3", ttl_seconds=300)

        time.sleep(1.1)  # Wait for first entries to expire

        removed = cache.cleanup()
        assert removed == 2
        assert cache.get("expired1") is None
        assert cache.get("expired2") is None
        assert cache.get("active") == "value3"

    def test_cache_key_generation(self):
        """Test cache key generation."""
        cache = CacheService()
        key1 = cache.cache_key("test", 1, 2, a="b")
        key2 = cache.cache_key("test", 1, 2, a="b")
        key3 = cache.cache_key("test", 1, 2, a="c")

        assert key1 == key2  # Same inputs should produce same key
        assert key1 != key3  # Different inputs should produce different keys

    def test_get_stats(self):
        """Test cache statistics."""
        cache = CacheService()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        assert stats["expired_entries"] == 0
        assert stats["size_bytes"] > 0

    def test_cached_decorator(self):
        """Test the @cached decorator."""
        cache = CacheService()

        counter = 0

        @cache.cached()
        def test_function(x, y):
            nonlocal counter
            counter += 1
            return x + y

        # First call should execute function
        result1 = test_function(1, 2)
        assert result1 == 3
        assert counter == 1

        # Second call with same args should use cache
        result2 = test_function(1, 2)
        assert result2 == 3
        assert counter == 1  # Counter shouldn't increment

        # Call with different args should execute function
        result3 = test_function(2, 3)
        assert result3 == 5
        assert counter == 2

    @pytest.mark.asyncio
    async def test_cached_async_decorator(self):
        """Test the @cached_async decorator."""
        cache = CacheService()

        counter = 0

        @cache.cached_async()
        async def test_async_function(x, y):
            nonlocal counter
            counter += 1
            return x + y

        # First call should execute function
        result1 = await test_async_function(1, 2)
        assert result1 == 3
        assert counter == 1

        # Second call with same args should use cache
        result2 = await test_async_function(1, 2)
        assert result2 == 3
        assert counter == 1  # Counter shouldn't increment

    def test_memory_management(self):
        """Test memory usage estimation."""
        cache = CacheService()

        # Add some entries with different sizes
        cache.set("small", "x")
        cache.set("medium", "x" * 1000)
        cache.set("large", "x" * 10000)

        stats = cache.get_stats()
        assert stats["size_bytes"] > 11000  # Should be at least the sum of data sizes
        assert stats["size_mb"] == stats["size_bytes"] / (1024 * 1024)

    def test_thread_safety_with_locks(self):
        """Test that locks are used for thread safety."""
        cache = CacheService()

        with patch.object(cache, "_get_lock") as mock_get_lock:
            mock_lock = MagicMock()
            mock_get_lock.return_value = mock_lock

            cache.set("key", "value")
            mock_get_lock.assert_called_with("key")
            mock_lock.__enter__.assert_called()
            mock_lock.__exit__.assert_called()
