"""Query result caching for CDash GraphQL queries."""

import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple
from collections import OrderedDict


class QueryCache:
    """LRU cache for GraphQL query results with TTL support."""

    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        """Initialize the cache.

        Args:
            max_size: Maximum number of cached items (LRU eviction)
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()

    def _make_key(
        self, query: str, variables: Optional[Dict[str, Any]], base_url: str
    ) -> str:
        """Create a cache key from query, variables, and base_url.

        Args:
            query: GraphQL query string
            variables: Query variables
            base_url: CDash instance URL

        Returns:
            SHA256 hash of the normalized query components
        """
        # Normalize the query by removing extra whitespace
        normalized_query = " ".join(query.split())

        # Create a deterministic representation
        key_data = {
            "query": normalized_query,
            "variables": variables or {},
            "base_url": base_url,
        }

        # Hash the JSON representation
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self, query: str, variables: Optional[Dict[str, Any]], base_url: str
    ) -> Optional[Any]:
        """Get a cached result if available and not expired.

        Args:
            query: GraphQL query string
            variables: Query variables
            base_url: CDash instance URL

        Returns:
            Cached result or None if not found/expired
        """
        key = self._make_key(query, variables, base_url)

        if key not in self._cache:
            return None

        result, expiry_time = self._cache[key]

        # Check if expired
        if time.time() > expiry_time:
            del self._cache[key]
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return result

    def set(
        self,
        query: str,
        variables: Optional[Dict[str, Any]],
        base_url: str,
        result: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Cache a query result.

        Args:
            query: GraphQL query string
            variables: Query variables
            base_url: CDash instance URL
            result: Query result to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        key = self._make_key(query, variables, base_url)
        expiry_time = time.time() + (ttl if ttl is not None else self.default_ttl)

        # Add or update the cache
        self._cache[key] = (result, expiry_time)
        self._cache.move_to_end(key)

        # Evict oldest item if over max_size
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()

    def invalidate(
        self, query: str, variables: Optional[Dict[str, Any]], base_url: str
    ) -> bool:
        """Invalidate a specific cached query.

        Args:
            query: GraphQL query string
            variables: Query variables
            base_url: CDash instance URL

        Returns:
            True if item was removed, False if not found
        """
        key = self._make_key(query, variables, base_url)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        current_time = time.time()
        expired_count = sum(
            1 for _, expiry in self._cache.values() if current_time > expiry
        )

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "expired_items": expired_count,
            "default_ttl": self.default_ttl,
        }
