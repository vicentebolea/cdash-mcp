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

## Configuration

The server requires a CDash authentication token and optionally a base URL. These can be provided via:
- Environment variables: `CDASH_TOKEN` and `CDASH_BASE_URL`
- Command line arguments: `--token` and `--base-url`

```bash
# Set environment variables
export CDASH_TOKEN="your-token-here"
export CDASH_BASE_URL="https://open.cdash.org"  # Default value

# Or use a different CDash instance
export CDASH_BASE_URL="https://cdash.spack.io"
```

## Usage

### Server

```bash
# Start stdio server (for MCP clients) with default CDash instance
cdash-mcp-server --token YOUR_TOKEN

# Use a specific CDash instance
cdash-mcp-server --token YOUR_TOKEN --base-url https://cdash.spack.io

# Start HTTP server for direct access
cdash-mcp-server --token YOUR_TOKEN --transport http --host localhost --port 8000

# Use custom CDash instance with HTTP transport
cdash-mcp-server --token YOUR_TOKEN --base-url https://cdash.spack.io --transport http
```

### Client

```bash
# List all available projects
cdash-mcp-client --token YOUR_TOKEN list-projects

# List builds for a specific project
cdash-mcp-client --token YOUR_TOKEN list-builds "Spack Testing"

# Get builds with a limit
cdash-mcp-client --token YOUR_TOKEN list-builds "Spack Testing" --limit 10

# List available tools
cdash-mcp-client --token YOUR_TOKEN list-tools

# Connect to different server
cdash-mcp-client --host localhost --port 8000 list-projects
```

## MCP Tools

The server provides two MCP tools:

- `list_projects()` - List all available CDash projects with their metadata
- `list_builds(project_name, limit)` - List builds for a specific project

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
- Vicente Bolea @ Kitware
