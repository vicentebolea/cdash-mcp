"""Unit tests for query cache."""

import time
from cdash_mcp_server.cache import QueryCache


class TestQueryCache:
    """Test QueryCache class."""

    def test_cache_initialization(self):
        """Test cache initialization with default values."""
        cache = QueryCache()
        assert cache.max_size == 100
        assert cache.default_ttl == 300

    def test_cache_custom_initialization(self):
        """Test cache initialization with custom values."""
        cache = QueryCache(max_size=50, default_ttl=600)
        assert cache.max_size == 50
        assert cache.default_ttl == 600

    def test_cache_set_and_get(self):
        """Test setting and getting cached values."""
        cache = QueryCache()
        query = "query { test }"
        variables = {"var1": "value1"}
        base_url = "https://test.cdash.org"
        result = {"data": {"test": "result"}}

        cache.set(query, variables, base_url, result)
        cached_result = cache.get(query, variables, base_url)

        assert cached_result == result

    def test_cache_get_nonexistent(self):
        """Test getting a nonexistent cache entry."""
        cache = QueryCache()
        result = cache.get("query { test }", None, "https://test.cdash.org")
        assert result is None

    def test_cache_key_uniqueness(self):
        """Test that different queries produce different cache keys."""
        cache = QueryCache()
        base_url = "https://test.cdash.org"

        cache.set("query { test1 }", None, base_url, {"data": "result1"})
        cache.set("query { test2 }", None, base_url, {"data": "result2"})

        result1 = cache.get("query { test1 }", None, base_url)
        result2 = cache.get("query { test2 }", None, base_url)

        assert result1["data"] == "result1"
        assert result2["data"] == "result2"

    def test_cache_variables_affect_key(self):
        """Test that variables affect cache key."""
        cache = QueryCache()
        query = "query GetProject($name: String!) { project(name: $name) { id } }"
        base_url = "https://test.cdash.org"

        cache.set(query, {"name": "Project1"}, base_url, {"data": "result1"})
        cache.set(query, {"name": "Project2"}, base_url, {"data": "result2"})

        result1 = cache.get(query, {"name": "Project1"}, base_url)
        result2 = cache.get(query, {"name": "Project2"}, base_url)

        assert result1["data"] == "result1"
        assert result2["data"] == "result2"

    def test_cache_base_url_affects_key(self):
        """Test that base_url affects cache key."""
        cache = QueryCache()
        query = "query { test }"

        cache.set(query, None, "https://url1.cdash.org", {"data": "result1"})
        cache.set(query, None, "https://url2.cdash.org", {"data": "result2"})

        result1 = cache.get(query, None, "https://url1.cdash.org")
        result2 = cache.get(query, None, "https://url2.cdash.org")

        assert result1["data"] == "result1"
        assert result2["data"] == "result2"

    def test_cache_ttl_expiration(self):
        """Test that cached entries expire after TTL."""
        cache = QueryCache(default_ttl=1)  # 1 second TTL
        query = "query { test }"
        base_url = "https://test.cdash.org"

        cache.set(query, None, base_url, {"data": "result"})

        # Should be cached immediately
        result = cache.get(query, None, base_url)
        assert result is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired now
        result = cache.get(query, None, base_url)
        assert result is None

    def test_cache_custom_ttl(self):
        """Test setting custom TTL for specific entries."""
        cache = QueryCache(default_ttl=300)
        query = "query { test }"
        base_url = "https://test.cdash.org"

        # Set with custom TTL of 1 second
        cache.set(query, None, base_url, {"data": "result"}, ttl=1)

        # Should be cached immediately
        result = cache.get(query, None, base_url)
        assert result is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        result = cache.get(query, None, base_url)
        assert result is None

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = QueryCache(max_size=3)
        base_url = "https://test.cdash.org"

        # Fill cache
        cache.set("query1", None, base_url, {"data": "result1"})
        cache.set("query2", None, base_url, {"data": "result2"})
        cache.set("query3", None, base_url, {"data": "result3"})

        # All should be cached
        assert cache.get("query1", None, base_url) is not None
        assert cache.get("query2", None, base_url) is not None
        assert cache.get("query3", None, base_url) is not None

        # Add one more - should evict query1 (oldest)
        cache.set("query4", None, base_url, {"data": "result4"})

        # query1 should be evicted
        assert cache.get("query1", None, base_url) is None

        # Others should still be cached
        assert cache.get("query2", None, base_url) is not None
        assert cache.get("query3", None, base_url) is not None
        assert cache.get("query4", None, base_url) is not None

    def test_cache_lru_access_updates_order(self):
        """Test that accessing an entry updates its position in LRU."""
        cache = QueryCache(max_size=3)
        base_url = "https://test.cdash.org"

        cache.set("query1", None, base_url, {"data": "result1"})
        cache.set("query2", None, base_url, {"data": "result2"})
        cache.set("query3", None, base_url, {"data": "result3"})

        # Access query1 to make it most recently used
        cache.get("query1", None, base_url)

        # Add query4 - should evict query2 (now oldest)
        cache.set("query4", None, base_url, {"data": "result4"})

        # query2 should be evicted, query1 should still be there
        assert cache.get("query1", None, base_url) is not None
        assert cache.get("query2", None, base_url) is None
        assert cache.get("query3", None, base_url) is not None
        assert cache.get("query4", None, base_url) is not None

    def test_cache_clear(self):
        """Test clearing the cache."""
        cache = QueryCache()
        base_url = "https://test.cdash.org"

        cache.set("query1", None, base_url, {"data": "result1"})
        cache.set("query2", None, base_url, {"data": "result2"})

        # Verify entries are cached
        assert cache.get("query1", None, base_url) is not None
        assert cache.get("query2", None, base_url) is not None

        # Clear cache
        cache.clear()

        # Verify cache is empty
        assert cache.get("query1", None, base_url) is None
        assert cache.get("query2", None, base_url) is None

    def test_cache_invalidate(self):
        """Test invalidating a specific cache entry."""
        cache = QueryCache()
        base_url = "https://test.cdash.org"

        cache.set("query1", None, base_url, {"data": "result1"})
        cache.set("query2", None, base_url, {"data": "result2"})

        # Invalidate query1
        result = cache.invalidate("query1", None, base_url)
        assert result is True

        # query1 should be gone, query2 should remain
        assert cache.get("query1", None, base_url) is None
        assert cache.get("query2", None, base_url) is not None

        # Invalidating non-existent entry should return False
        result = cache.invalidate("query3", None, base_url)
        assert result is False

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = QueryCache(max_size=10, default_ttl=300)
        base_url = "https://test.cdash.org"

        # Initial stats
        stats = cache.stats()
        assert stats["size"] == 0
        assert stats["max_size"] == 10
        assert stats["default_ttl"] == 300
        assert stats["expired_items"] == 0

        # Add some entries
        cache.set("query1", None, base_url, {"data": "result1"})
        cache.set("query2", None, base_url, {"data": "result2"})

        stats = cache.stats()
        assert stats["size"] == 2

        # Add expired entry
        cache.set("query3", None, base_url, {"data": "result3"}, ttl=0)

        stats = cache.stats()
        assert stats["size"] == 3
        assert stats["expired_items"] >= 1

    def test_cache_query_normalization(self):
        """Test that queries are normalized (whitespace doesn't matter)."""
        cache = QueryCache()
        base_url = "https://test.cdash.org"

        # These should produce the same cache key
        query1 = "query { test }"
        query2 = "query  {  test  }"
        query3 = "query\n{\n  test\n}"

        cache.set(query1, None, base_url, {"data": "result"})

        # All variations should retrieve the same cached value
        assert cache.get(query2, None, base_url) is not None
        assert cache.get(query3, None, base_url) is not None
