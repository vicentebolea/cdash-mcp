#!/usr/bin/env python3
"""CDash MCP Server - Provides CDash GraphQL query execution via MCP."""

import asyncio
import json
import click
from fastmcp import FastMCP
from .cdash_client import CDashClient
from .cache import QueryCache
from .query_utils import (
    parse_relative_date,
    build_builds_query,
)

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


def _describe_schema_impl(base_url: str = "https://open.cdash.org") -> str:
    """Fetch and describe the CDash GraphQL schema.

    Args:
        base_url: CDash instance URL (default: https://open.cdash.org)

    Returns:
        JSON string with schema information including types, queries, and fields
    """
    client = CDashClient(base_url=base_url)
    schema_result = client.get_schema()

    if not schema_result.get("success"):
        return json.dumps(schema_result, indent=2)

    # Extract and format schema information
    schema_data = schema_result.get("data", {}).get("__schema", {})

    output = {
        "success": True,
        "query_type": schema_data.get("queryType", {}).get("name"),
        "mutation_type": (
            schema_data.get("mutationType", {}).get("name")
            if schema_data.get("mutationType")
            else None
        ),
        "types": [],
    }

    # Get important types (skip internal types)
    types = schema_data.get("types", [])
    important_types = ["Query", "Project", "Build", "Site", "User"]

    for type_info in types:
        type_name = type_info.get("name", "")
        if type_name.startswith("__"):
            continue

        # Include important types with full details, others with just name
        if type_name in important_types:
            type_summary = {
                "name": type_name,
                "kind": type_info.get("kind"),
                "description": type_info.get("description", ""),
                "fields": [],
            }

            fields = type_info.get("fields", []) or []
            for field in fields:
                field_info = {
                    "name": field.get("name"),
                    "description": field.get("description", ""),
                    "args": [],
                }

                # Add arguments if present
                args = field.get("args", []) or []
                for arg in args:
                    arg_type = arg.get("type", {})
                    arg_info = {
                        "name": arg.get("name"),
                        "description": arg.get("description", ""),
                        "type": arg_type.get("name")
                        or (
                            arg_type.get("ofType", {}).get("name")
                            if arg_type.get("ofType")
                            else "Unknown"
                        ),
                    }
                    field_info["args"].append(arg_info)

                type_summary["fields"].append(field_info)

            output["types"].append(type_summary)
        elif type_info.get("kind") in ["OBJECT", "INPUT_OBJECT"]:
            # Include just name and kind for other types
            output["types"].append(
                {
                    "name": type_name,
                    "kind": type_info.get("kind"),
                }
            )

    return json.dumps(output, indent=2)


def _get_query_examples_impl() -> str:
    """Get common CDash GraphQL query examples.

    Returns:
        JSON string with categorized query examples
    """
    examples = {
        "success": True,
        "categories": [
            {
                "category": "Projects",
                "examples": [
                    {
                        "name": "List all projects",
                        "query": """query {
  projects {
    edges {
      node {
        id
        name
        description
        buildCount
      }
    }
  }
}""",
                        "variables": None,
                    },
                    {
                        "name": "Get specific project by name",
                        "query": """query GetProject($name: String!) {
  project(name: $name) {
    id
    name
    description
    buildCount
  }
}""",
                        "variables": {"name": "ParaView"},
                    },
                ],
            },
            {
                "category": "Builds",
                "examples": [
                    {
                        "name": "List recent builds for a project",
                        "query": """query GetBuilds($projectName: String!, $first: Int!) {
  project(name: $projectName) {
    builds(first: $first) {
      edges {
        node {
          id
          name
          stamp
          startTime
          endTime
          buildDuration
          configureDuration
          testDuration
          buildErrorsCount
          buildWarningsCount
          site {
            name
          }
        }
      }
    }
  }
}""",
                        "variables": {"projectName": "ParaView", "first": 10},
                    },
                    {
                        "name": "Get build details by ID",
                        "query": """query GetBuild($buildId: ID!) {
  build(id: $buildId) {
    id
    name
    stamp
    startTime
    endTime
    buildDuration
    configureDuration
    testDuration
    buildErrorsCount
    buildWarningsCount
    site {
      id
      name
    }
    project {
      name
    }
  }
}""",
                        "variables": {"buildId": "10607791"},
                    },
                ],
            },
            {
                "category": "Filtering & Sorting",
                "examples": [
                    {
                        "name": "Get builds with pagination",
                        "query": """query GetBuildsWithPagination(
  $projectName: String!
  $first: Int!
  $after: String
) {
  project(name: $projectName) {
    builds(first: $first, after: $after) {
      edges {
        node {
          id
          name
          startTime
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}""",
                        "variables": {
                            "projectName": "ParaView",
                            "first": 50,
                            "after": None,
                        },
                    }
                ],
            },
            {
                "category": "Date Filtering Tips",
                "examples": [
                    {
                        "name": "Filter by date (manual approach)",
                        "description": (
                            "CDash GraphQL doesn't directly support date "
                            "filtering in queries. You can filter by fetching "
                            "more builds and using the 'stamp' or 'startTime' "
                            "fields to filter results client-side."
                        ),
                        "query": """query GetBuildsForFiltering(
  $projectName: String!
  $first: Int!
) {
  project(name: $projectName) {
    builds(first: $first) {
      edges {
        node {
          id
          name
          stamp
          startTime
          buildDuration
        }
      }
    }
  }
}""",
                        "variables": {"projectName": "ParaView", "first": 200},
                        "note": (
                            "Fetch larger dataset and filter by "
                            "startTime/stamp client-side"
                        ),
                    }
                ],
            },
        ],
    }

    return json.dumps(examples, indent=2)


def _list_builds_impl(
    project_name: str,
    limit: int = 10,
    order_by: str = None,
    order_direction: str = "DESC",
    date: str = None,
    site_name: str = None,
    base_url: str = "https://open.cdash.org",
    use_cache: bool = True,
) -> str:
    """List builds with advanced filtering and sorting.

    Args:
        project_name: Name of the CDash project
        limit: Maximum number of builds to return (default: 10)
        order_by: Field to sort by (e.g., "buildDuration", "startTime")
        order_direction: Sort direction - "ASC" or "DESC" (default: DESC)
        date: Date filter - supports relative dates like "yesterday",
            "today", "last_7_days" or absolute "YYYY-MM-DD"
        site_name: Filter builds by site name
        base_url: CDash instance URL (default: https://open.cdash.org)
        use_cache: Whether to use cached results (default: True)

    Returns:
        JSON string with filtered and sorted builds
    """
    # Build query
    query, variables = build_builds_query(
        project_name=project_name,
        limit=limit * 2,  # Fetch more for client-side filtering
        date=date,
        site_name=site_name,
    )

    # Execute query using existing infrastructure
    result_str = _execute_graphql_query_impl(
        query=query,
        base_url=base_url,
        variables=variables,
        use_cache=use_cache,
    )

    result = json.loads(result_str)

    if not result.get("success"):
        return result_str

    # Extract builds
    try:
        builds_data = (
            result.get("data", {}).get("project", {}).get("builds", {}).get("edges", [])
        )
        builds = [edge["node"] for edge in builds_data]

        # Client-side filtering
        filtered_builds = builds

        # Filter by date if specified
        if date:
            target_date = parse_relative_date(date)
            filtered_builds = [
                b
                for b in filtered_builds
                if b.get("startTime", "").startswith(target_date)
            ]

        # Filter by site if specified
        if site_name:
            filtered_builds = [
                b
                for b in filtered_builds
                if b.get("site", {}).get("name", "").lower() == site_name.lower()
            ]

        # Client-side sorting
        if order_by and order_by in [
            "buildDuration",
            "configureDuration",
            "testDuration",
            "startTime",
            "endTime",
        ]:
            reverse = order_direction.upper() == "DESC"
            filtered_builds.sort(key=lambda x: x.get(order_by, 0) or 0, reverse=reverse)

        # Limit results
        filtered_builds = filtered_builds[:limit]

        return json.dumps(
            {
                "success": True,
                "data": {
                    "project": result.get("data", {}).get("project", {}),
                    "builds": filtered_builds,
                    "total_fetched": len(builds),
                    "total_filtered": len(filtered_builds),
                    "filters_applied": {
                        "date": date,
                        "site_name": site_name,
                        "order_by": order_by,
                        "order_direction": order_direction,
                    },
                },
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "errors": [{"message": f"Error processing builds: {str(e)}"}],
            },
            indent=2,
        )


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


@mcp.tool()
def describe_schema(base_url: str = "https://open.cdash.org") -> str:
    """Fetch and describe the CDash GraphQL schema with introspection.

    Args:
        base_url: CDash instance URL (default: https://open.cdash.org)

    Returns:
        JSON string with detailed schema information including types, queries, fields, and arguments
    """
    return _describe_schema_impl(base_url)


@mcp.tool()
def get_query_examples() -> str:
    """Get common CDash GraphQL query examples organized by category.

    Returns:
        JSON string with categorized examples for projects, builds, filtering, and more
    """
    return _get_query_examples_impl()


@mcp.tool()
def list_builds(
    project_name: str,
    limit: int = 10,
    order_by: str = None,
    order_direction: str = "DESC",
    date: str = None,
    site_name: str = None,
    base_url: str = "https://open.cdash.org",
    use_cache: bool = True,
) -> str:
    """List builds with advanced filtering and sorting capabilities.

    This is a convenience tool that handles common build queries with client-side
    filtering and sorting since CDash GraphQL has limited filter support.

    Args:
        project_name: Name of the CDash project (required)
        limit: Maximum number of builds to return (default: 10)
        order_by: Field to sort by - "buildDuration", "configureDuration",
            "testDuration", "startTime", "endTime"
        order_direction: Sort direction - "ASC" or "DESC" (default: DESC)
        date: Date filter - supports:
            - Relative: "yesterday", "today", "last_7_days"
            - Absolute: "2025-11-26" (YYYY-MM-DD format)
        site_name: Filter builds by site name (exact match,
            case-insensitive)
        base_url: CDash instance URL (default: https://open.cdash.org)
        use_cache: Whether to use cached results (default: True)

    Returns:
        JSON string with filtered and sorted builds

    Examples:
        - Get 10 slowest builds from yesterday:
          list_builds("ParaView", limit=10, order_by="buildDuration",
                     date="yesterday")

        - Get builds from specific site:
          list_builds("ParaView", site_name="gitlab-ci", limit=20)
    """
    return _list_builds_impl(
        project_name=project_name,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
        date=date,
        site_name=site_name,
        base_url=base_url,
        use_cache=use_cache,
    )


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
