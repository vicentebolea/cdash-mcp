# CDash GraphQL MCP Server

A Model Context Protocol (MCP) server that provides generic GraphQL query execution against CDash instances with built-in caching.

## Features

- **Generic GraphQL Query Executor**: Execute any GraphQL query against CDash instances
- **Smart Caching**: LRU cache with configurable TTL to improve performance
- **No Authentication Required**: Works with public CDash instances (e.g., open.cdash.org)
- **Flexible Configuration**: Customize cache size and TTL at server startup
- **MCP Resources**: Built-in schema documentation to help construct queries

## Installation

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install .
```

## Architecture

The server uses a generic GraphQL query executor instead of implementing individual functions for each CDash operation. This allows LLMs to construct any GraphQL query they need, while the server handles caching and execution.

Key components:
- **CDashClient**: Generic GraphQL client for executing queries
- **QueryCache**: LRU cache with TTL support for query results
- **MCP Resources**: Schema documentation exposed via `cdash://schema_reference`

## Usage

### Server

Start the server with optional cache configuration:

```bash
# Start stdio server (for MCP clients)
cdash-mcp-server

# Start HTTP server with custom cache settings
cdash-mcp-server --transport http --port 8000 --cache-size 200 --cache-ttl 600

# Start with minimal caching (for testing)
cdash-mcp-server --cache-size 10 --cache-ttl 60
```

**Server Options:**
- `--transport`: Communication protocol (stdio or http, default: stdio)
- `--host`: HTTP server host (default: 127.0.0.1)
- `--port`: HTTP server port (default: 8000)
- `--cache-size`: Maximum number of cached queries (default: 100)
- `--cache-ttl`: Default cache TTL in seconds (default: 300)

## MCP Tools

The server provides three MCP tools:

### 1. execute_graphql_query

Execute any GraphQL query against a CDash instance.

**Parameters:**
- `query` (string, required): GraphQL query string
- `base_url` (string): CDash instance URL (default: "https://open.cdash.org")
- `variables` (dict): GraphQL variables (optional)
- `use_cache` (bool): Whether to use cache (default: true)
- `cache_ttl` (int): Custom TTL in seconds (optional)

**Example Queries:**

List all projects:
```graphql
query {
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
}
```

Get builds for a project:
```graphql
query GetBuilds($projectName: String!, $first: Int) {
  project(name: $projectName) {
    builds(first: $first) {
      edges {
        node {
          id
          name
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

Get specific build details:
```graphql
query GetBuild($buildId: ID!) {
  build(id: $buildId) {
    id
    name
    stamp
    failedTestsCount
    passedTestsCount
    project {
      name
    }
  }
}
```
Variables: `{"buildId": "123"}`

### 2. get_cache_stats

Get statistics about the query cache.

**Returns:**
- `size`: Current number of cached items
- `max_size`: Maximum cache size
- `expired_items`: Number of expired items
- `default_ttl`: Default TTL in seconds

### 3. clear_cache

Clear all cached query results.

## MCP Resources

### cdash://schema_reference

Access the CDash GraphQL schema documentation including:
- Common query patterns
- Available top-level queries
- Pagination information
- Best practices

## CLI Client

A simple CLI client is provided for testing:

```bash
# List available tools
cdash-mcp-client list-tools

# Execute a GraphQL query
cdash-mcp-client query 'query { projects { edges { node { id name } } } }'

# Execute a query with variables
cdash-mcp-client query 'query GetBuilds($name: String!) {
  project(name: $name) {
    builds(first: 10) {
      edges { node { id name } }
    }
  }
}' --variables '{"name": "MyProject"}'

# Execute query without caching
cdash-mcp-client query 'query { projects { edges { node { id } } } }' --no-cache

# Get cache statistics
cdash-mcp-client cache-stats

# Clear cache
cdash-mcp-client clear-cache

# Use custom server and CDash URL
cdash-mcp-client --host localhost --port 8000 --base-url https://cdash.spack.io query 'query { projects { edges { node { id name } } } }'
```

## Development

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode with test dependencies
pip install -e ".[test]"

# Start the server
cdash-mcp-server --transport http --port 8000

# In another terminal, test with the CLI client
cdash-mcp-client query 'query { projects { edges { node { id name } } } }'

# Or test with curl
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "execute_graphql_query",
      "arguments": {
        "query": "query { projects { edges { node { id name } } } }"
      }
    }
  }'
```

## Testing

Install test dependencies:

```bash
pip install -e ".[test]"
```

Run tests:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test files
pytest tests/test_cache.py
pytest tests/test_cdash_client.py
pytest tests/test_server_functions.py

# Run specific test types using markers
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests only
```

## Caching Behavior

- Queries are cached based on the query string, variables, and base_url
- Query strings are normalized (whitespace differences don't affect caching)
- Default TTL is 5 minutes (300 seconds)
- LRU eviction when cache reaches max_size
- Cache can be disabled per-query with `use_cache=false`
- Use `get_cache_stats` to monitor cache performance
- Use `clear_cache` to invalidate all cached entries

## Authors
- Vicente Bolea <vicente.bolea@kitware.com>

## License
MIT
