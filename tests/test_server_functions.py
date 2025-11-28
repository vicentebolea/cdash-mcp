"""Unit tests for MCP server functions."""

import json
import pytest
from cdash_mcp_server import server


@pytest.mark.unit
class TestServerFunctions:
    """Test MCP server tool functions."""

    def setup_method(self):
        """Reset cache before each test."""
        server.query_cache.clear()

    def test_execute_graphql_query_empty_query(self):
        """Test execute_graphql_query with empty query."""
        result = server._execute_graphql_query_impl("")
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "errors" in result_data

    def test_execute_graphql_query_success(self, monkeypatch):
        """Test successful GraphQL query execution."""
        from cdash_mcp_server.cdash_client import CDashClient

        def mock_execute_query(self, query, variables=None):
            return {
                "success": True,
                "data": {
                    "projects": {
                        "edges": [
                            {
                                "node": {
                                    "id": "1",
                                    "name": "Test Project",
                                    "description": "A test",
                                }
                            }
                        ]
                    }
                },
            }

        monkeypatch.setattr(CDashClient, "execute_query", mock_execute_query)

        query = "query { projects { edges { node { id name } } } }"
        result = server._execute_graphql_query_impl(query)
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert "data" in result_data
        assert (
            result_data["data"]["projects"]["edges"][0]["node"]["name"]
            == "Test Project"
        )

    def test_execute_graphql_query_with_variables(self, monkeypatch):
        """Test query execution with variables."""
        from cdash_mcp_server.cdash_client import CDashClient

        def mock_execute_query(self, query, variables=None):
            return {
                "success": True,
                "data": {"project": {"id": "1", "name": variables["name"]}},
            }

        monkeypatch.setattr(CDashClient, "execute_query", mock_execute_query)

        query = "query GetProject($name: String!) { project(name: $name) { id name } }"
        variables = {"name": "Test Project"}
        result = server._execute_graphql_query_impl(query, variables=variables)
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["data"]["project"]["name"] == "Test Project"

    def test_execute_graphql_query_caching(self, monkeypatch):
        """Test that results are cached."""
        from cdash_mcp_server.cdash_client import CDashClient

        call_count = {"count": 0}

        def mock_execute_query(self, query, variables=None):
            call_count["count"] += 1
            return {"success": True, "data": {"test": "data"}}

        monkeypatch.setattr(CDashClient, "execute_query", mock_execute_query)

        query = "query { test }"

        # First call - should hit the API
        result1 = server._execute_graphql_query_impl(query)
        result1_data = json.loads(result1)
        assert result1_data["success"] is True
        assert call_count["count"] == 1
        assert "cached" not in result1_data

        # Second call - should use cache
        result2 = server._execute_graphql_query_impl(query)
        result2_data = json.loads(result2)
        assert result2_data["success"] is True
        assert call_count["count"] == 1  # No additional API call
        assert result2_data["cached"] is True

    def test_execute_graphql_query_cache_disabled(self, monkeypatch):
        """Test query execution with caching disabled."""
        from cdash_mcp_server.cdash_client import CDashClient

        call_count = {"count": 0}

        def mock_execute_query(self, query, variables=None):
            call_count["count"] += 1
            return {"success": True, "data": {"test": "data"}}

        monkeypatch.setattr(CDashClient, "execute_query", mock_execute_query)

        query = "query { test }"

        # Both calls should hit the API
        server._execute_graphql_query_impl(query, use_cache=False)
        assert call_count["count"] == 1

        server._execute_graphql_query_impl(query, use_cache=False)
        assert call_count["count"] == 2

    def test_execute_graphql_query_custom_base_url(self, monkeypatch):
        """Test query execution with custom base URL."""
        from cdash_mcp_server.cdash_client import CDashClient

        captured_base_url = {"url": None}

        original_init = CDashClient.__init__

        def mock_init(self, base_url="https://open.cdash.org"):
            captured_base_url["url"] = base_url
            original_init(self, base_url)

        def mock_execute_query(self, query, variables=None):
            return {"success": True, "data": {}}

        monkeypatch.setattr(CDashClient, "__init__", mock_init)
        monkeypatch.setattr(CDashClient, "execute_query", mock_execute_query)

        query = "query { test }"
        server._execute_graphql_query_impl(query, base_url="https://custom.cdash.io")

        assert captured_base_url["url"] == "https://custom.cdash.io"

    def test_get_cache_stats(self):
        """Test cache statistics retrieval."""
        result = server._get_cache_stats_impl()
        stats = json.loads(result)

        assert "size" in stats
        assert "max_size" in stats
        assert "expired_items" in stats
        assert "default_ttl" in stats

    def test_clear_cache(self, monkeypatch):
        """Test cache clearing."""
        from cdash_mcp_server.cdash_client import CDashClient

        def mock_execute_query(self, query, variables=None):
            return {"success": True, "data": {"test": "data"}}

        monkeypatch.setattr(CDashClient, "execute_query", mock_execute_query)

        # Add something to cache
        query = "query { test }"
        server._execute_graphql_query_impl(query)

        # Verify cache has content
        stats = json.loads(server._get_cache_stats_impl())
        assert stats["size"] > 0

        # Clear cache
        result = server._clear_cache_impl()
        result_data = json.loads(result)
        assert result_data["success"] is True

        # Verify cache is empty
        stats = json.loads(server._get_cache_stats_impl())
        assert stats["size"] == 0

    def test_get_graphql_schema_resource(self):
        """Test GraphQL schema resource."""
        schema = server._get_graphql_schema_impl()

        assert isinstance(schema, str)
        assert "CDash GraphQL Schema Guide" in schema
        assert "Common Query Patterns" in schema
        assert "List All Projects" in schema
        assert "Pagination" in schema
