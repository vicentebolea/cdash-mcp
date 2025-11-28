#!/usr/bin/env python3
"""CDash MCP Server - Provides CDash GraphQL query execution via MCP."""

import asyncio
import json
import click
from fastmcp import FastMCP
from .cdash_client import CDashClient
from .cache import QueryCache

# Initialize MCP server
mcp = FastMCP("CDash GraphQL MCP Server")

# Global cache instance (configurable TTL and size)
query_cache = QueryCache(max_size=100, default_ttl=300)


def _execute_graphql_query_impl(
    query: str,
    base_url: str = "https://open.cdash.org",
    variables: dict = None,
    use_cache: bool = True,
    cache_ttl: int = None,
) -> str:
    """Execute a GraphQL query against a CDash instance.

    This tool allows you to run any GraphQL query against CDash. The server
    will cache results to improve performance for repeated queries.

    Args:
        query: GraphQL query string (required)
        base_url: CDash instance URL (default: https://open.cdash.org)
        variables: Dictionary of GraphQL variables (optional)
        use_cache: Whether to use cached results if available (default: True)
        cache_ttl: Cache time-to-live in seconds, overrides default 300s (optional)

    Returns:
        JSON string with query results or error information

    Example queries:
        1. List all projects:
           query {
             projects { edges { node { id name description } } }
           }

        2. Get builds for a project:
           query GetBuilds($projectName: String!, $first: Int) {
             project(name: $projectName) {
               builds(first: $first) {
                 edges { node { id name startTime failedTestsCount } }
               }
             }
           }
           Variables: {"projectName": "MyProject", "first": 10}
    """
    if not query or not query.strip():
        return json.dumps(
            {"success": False, "errors": [{"message": "Query cannot be empty"}]},
            indent=2,
        )

    # Check cache first
    if use_cache:
        cached_result = query_cache.get(query, variables, base_url)
        if cached_result is not None:
            result = cached_result.copy()
            result["cached"] = True
            return json.dumps(result, indent=2)

    # Execute query
    client = CDashClient(base_url=base_url)
    result = client.execute_query(query, variables)

    # Cache successful results
    if use_cache and result.get("success"):
        query_cache.set(query, variables, base_url, result, ttl=cache_ttl)

    return json.dumps(result, indent=2)


def _get_cache_stats_impl() -> str:
    """Get statistics about the query cache.

    Returns:
        JSON string with cache statistics including size and expired items
    """
    stats = query_cache.stats()
    return json.dumps(stats, indent=2)


def _clear_cache_impl() -> str:
    """Clear all cached query results.

    Returns:
        Confirmation message
    """
    query_cache.clear()
    return json.dumps({"success": True, "message": "Cache cleared successfully"})


def _get_graphql_schema_impl() -> str:
    """Provides the CDash GraphQL schema documentation.

    This resource contains helpful information about available queries,
    types, and fields in the CDash GraphQL API.
    """
    return """# CDash GraphQL Schema Guide

## Common Query Patterns

### 1. List All Projects
```graphql
query {
  projects {
    edges {
      node {
        id
        name
        description
        homeurl
        visibility
        buildCount
      }
    }
  }
}
```

### 2. Get a Specific Project
```graphql
query GetProject($name: String!) {
  project(name: $name) {
    id
    name
    description
    buildCount
  }
}
```
Variables: `{"name": "YourProjectName"}`

### 3. List Builds for a Project
```graphql
query GetBuilds($projectName: String!, $first: Int) {
  project(name: $projectName) {
    builds(first: $first) {
      edges {
        node {
          id
          name
          stamp
          startTime
          endTime
          failedTestsCount
          passedTestsCount
          site {
            name
          }
        }
      }
    }
  }
}
```
Variables: `{"projectName": "MyProject", "first": 50}`

### 4. Get Build Details
```graphql
query GetBuild($buildId: ID!) {
  build(id: $buildId) {
    id
    name
    stamp
    startTime
    endTime
    failedTestsCount
    passedTestsCount
    site {
      id
      name
    }
    project {
      name
    }
  }
}
```
Variables: `{"buildId": "123"}`

## Available Top-Level Queries

- `me` - Get current user (requires authentication)
- `user(id: ID!)` - Get a specific user by ID
- `project(id: ID, name: String)` - Get a project by ID or name
- `projects(first: Int!, after: String)` - List projects with pagination
- `build(id: ID!)` - Get a specific build by ID
- `site(id: ID!)` - Get a specific site by ID
- `users(first: Int!, after: String)` - List users with pagination

## Pagination

CDash uses cursor-based pagination:
- Use `first: Int` to limit results
- Use `after: String` with the cursor from previous query for next page
- Results are in `edges` array with `node` containing the actual data
- Use `pageInfo { hasNextPage endCursor }` to navigate pages

## Tips

1. **Cache awareness**: Queries are cached for 5 minutes by default
2. **Performance**: Request only the fields you need to reduce payload size
3. **Pagination**: Use appropriate `first` values (10-100) for large datasets
4. **Error handling**: Check the response for `errors` field"""


# MCP Tool and Resource wrappers
@mcp.tool()
def execute_graphql_query(
    query: str,
    base_url: str = "https://open.cdash.org",
    variables: dict = None,
    use_cache: bool = True,
    cache_ttl: int = None,
) -> str:
    """Execute a GraphQL query against a CDash instance.

    This tool allows you to run any GraphQL query against CDash. The server
    will cache results to improve performance for repeated queries.

    Args:
        query: GraphQL query string (required)
        base_url: CDash instance URL (default: https://open.cdash.org)
        variables: Dictionary of GraphQL variables (optional)
        use_cache: Whether to use cached results if available (default: True)
        cache_ttl: Cache time-to-live in seconds, overrides default 300s (optional)

    Returns:
        JSON string with query results or error information
    """
    return _execute_graphql_query_impl(query, base_url, variables, use_cache, cache_ttl)


@mcp.tool()
def get_cache_stats() -> str:
    """Get statistics about the query cache.

    Returns:
        JSON string with cache statistics including size and expired items
    """
    return _get_cache_stats_impl()


@mcp.tool()
def clear_cache() -> str:
    """Clear all cached query results.

    Returns:
        Confirmation message
    """
    return _clear_cache_impl()


@mcp.resource("cdash://schema_reference")
def get_graphql_schema() -> str:
    """Provides the CDash GraphQL schema documentation.

    This resource contains helpful information about available queries,
    types, and fields in the CDash GraphQL API.
    """
    return _get_graphql_schema_impl()


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="Transport protocol",
)
@click.option("--host", default="127.0.0.1", help="Host (HTTP only)")
@click.option("--port", default=8000, type=int, help="Port (HTTP only)")
@click.option(
    "--cache-size",
    default=100,
    type=int,
    help="Maximum cache size (default: 100)",
)
@click.option(
    "--cache-ttl",
    default=300,
    type=int,
    help="Default cache TTL in seconds (default: 300)",
)
def main(transport, host, port, cache_size, cache_ttl):
    """Run the CDash GraphQL MCP Server.

    This server provides a generic GraphQL query executor for CDash instances,
    with built-in caching for improved performance.
    """
    # Update cache configuration
    global query_cache
    query_cache = QueryCache(max_size=cache_size, default_ttl=cache_ttl)

    if transport == "http":
        click.echo(f"Starting CDash GraphQL MCP Server on http://{host}:{port}")
        click.echo(f"Cache: max_size={cache_size}, default_ttl={cache_ttl}s")
        click.echo("Use execute_graphql_query tool to run queries")
        asyncio.run(mcp.run_http_async(host=host, port=port))
    else:
        click.echo("Starting CDash GraphQL MCP Server on stdio transport")
        click.echo(f"Cache: max_size={cache_size}, default_ttl={cache_ttl}s")
        click.echo("Use execute_graphql_query tool to run queries")
        mcp.run()


if __name__ == "__main__":
    main()
