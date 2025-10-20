# CDash MCP Server - Usage Examples

## Installation

```bash
cd /home/vicente/Projects/cdash-mcp
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Configuration

Set your CDash authentication token:

```bash
export CDASH_TOKEN="your-cdash-token-here"
export CDASH_BASE_URL="https://cdash.spack.io"  # Optional, defaults to this value
```

## Running the Server

### Stdio Transport (for MCP clients like Claude Desktop)

```bash
cdash-mcp-server --token $CDASH_TOKEN
```

### HTTP Transport (for direct testing)

```bash
cdash-mcp-server --token $CDASH_TOKEN --transport http --host localhost --port 8000
```

## Using the Client

Once the HTTP server is running, you can use the client:

### List All Projects

```bash
cdash-mcp-client --token $CDASH_TOKEN list-projects
```

Example output:
```
# CDash Projects

## Spack Testing
**Description:** Continuous integration testing for Spack package manager
**Build Count:** 1234
**Home URL:** https://github.com/spack/spack
**Visibility:** PUBLIC
**ID:** 123
```

### List Builds for a Project

```bash
cdash-mcp-client --token $CDASH_TOKEN list-builds "Spack Testing"
```

With custom limit:
```bash
cdash-mcp-client --token $CDASH_TOKEN list-builds "Spack Testing" --limit 10
```

Example output:
```
# Builds for Project: Spack Testing

Showing 10 builds (limit: 10)

## Build 1: py-torch@2.1.0 (Data and Vis SDK) ✅
**Status:** PASSED
**ID:** 12345
**Site:** ubuntu-runner
**Stamp:** 20241020-1234
**Start Time:** 2024-10-20T12:34:00Z
**End Time:** 2024-10-20T13:00:00Z
**Failed Tests:** 0
**Passed Tests:** 150

## Build 2: vtk@9.3.0 (Data and Vis SDK) ❌
**Status:** FAILED
**ID:** 12346
**Site:** windows-runner
**Stamp:** 20241020-1235
**Start Time:** 2024-10-20T12:35:00Z
**End Time:** 2024-10-20T13:15:00Z
**Failed Tests:** 3
**Passed Tests:** 147
```

### List Available Tools

```bash
cdash-mcp-client --token $CDASH_TOKEN list-tools
```

## MCP Tools

The server exposes two MCP tools:

### 1. list_projects()

Lists all available CDash projects with metadata including:
- Project name
- Description
- Build count
- Home URL
- Visibility
- Project ID

### 2. list_builds(project_name, limit=50)

Lists builds for a specific project with information including:
- Build name
- Build ID
- Site name
- Timestamp
- Start and end times
- Test pass/fail counts
- Status (PASSED/FAILED)

## Integrating with Claude Desktop

Add to your Claude Desktop MCP configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "cdash": {
      "command": "/home/vicente/Projects/cdash-mcp/venv/bin/cdash-mcp-server",
      "args": ["--token", "YOUR_CDASH_TOKEN"],
      "env": {
        "CDASH_BASE_URL": "https://cdash.spack.io"
      }
    }
  }
}
```

Then restart Claude Desktop and you can ask questions like:
- "List all projects in CDash"
- "Show me the recent builds for Spack Testing"
- "How many builds does the project have?"

## Testing

Run the test suite:

```bash
pytest
pytest -v  # Verbose output
pytest -m unit  # Only unit tests
```

## Development

Install in development mode:

```bash
pip install -e ".[test]"
```

Run the server locally for testing:

```bash
# Terminal 1: Start server
cdash-mcp-server --token $CDASH_TOKEN --transport http

# Terminal 2: Test with client
cdash-mcp-client --token $CDASH_TOKEN list-projects
```
