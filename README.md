# CDash MCP Server

Access CDash project and build information through a Model Context Protocol server.

## Installation

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install .
```

## Architecture

The server is stateless and requires **no configuration** at startup. Instead, the CDash URL and authentication token are passed as parameters when calling tools. This allows a single server instance to query multiple CDash servers.

## Usage

### Server

The server requires no CDash credentials at startup:

```bash
# Start stdio server (for MCP clients)
cdash-mcp-server

# Start HTTP server for testing
cdash-mcp-server --transport http --port 8000
```

### Client

The client passes the CDash URL and token when calling tools:

```bash
# List projects from open.cdash.org (default)
cdash-mcp-client --token YOUR_TOKEN list-projects

# List projects from cdash.spack.io
cdash-mcp-client --token YOUR_TOKEN --base-url https://cdash.spack.io list-projects

# List builds from a specific CDash instance
cdash-mcp-client --token YOUR_TOKEN --base-url https://cdash.spack.io list-builds "Spack Testing" --limit 10

# List available tools (no token needed)
cdash-mcp-client list-tools

# Connect to custom server
cdash-mcp-client --host localhost --port 8000 --token YOUR_TOKEN list-projects
```

## MCP Tools

The server provides two MCP tools. Both accept `base_url` and `token` as parameters:

- **`list_projects(base_url, token)`** - List all available CDash projects
  - `base_url`: CDash server URL (default: "https://open.cdash.org")
  - `token`: CDash authentication token

- **`list_builds(project_name, base_url, token, limit)`** - List builds for a specific project
  - `project_name`: Name of the CDash project (required)
  - `base_url`: CDash server URL (default: "https://open.cdash.org")
  - `token`: CDash authentication token
  - `limit`: Maximum number of builds to return (default: 50)

## Development

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .

# Test the HTTP server and client
cdash-mcp-server --token YOUR_TOKEN --transport http &
cdash-mcp-client --token YOUR_TOKEN list-projects
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

# Run specific test types using markers
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests only
pytest -m http                  # HTTP transport tests
pytest -m stdio                 # Stdio transport tests
```

## Authors
- Vicente Bolea <vicente.bolea@kitware.com>
