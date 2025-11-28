#!/usr/bin/env python3
"""Simple CLI client for testing CDash MCP Server."""

import click
import requests
import json
import sys


class MCPClient:
    """Simple MCP client for HTTP transport."""

    def __init__(self, host: str = "localhost", port: int = 8000):
        """Initialize MCP client.

        Args:
            host: Server host
            port: Server port
        """
        self.base_url = f"http://{host}:{port}"
        self.session_id = None
        self._initialize_session()

    def _initialize_session(self):
        """Initialize MCP session with handshake."""
        try:
            # Initialize
            payload = {
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "cdash-mcp-client", "version": "1.0.0"},
                },
            }
            response = self._make_request(payload)
            if not response:
                return

            self.session_id = response.headers.get("Mcp-Session-Id")

            # Send initialized notification
            self._make_request(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                }
            )
        except Exception as e:
            print(f"Session initialization failed: {e}", file=sys.stderr)

    def _make_request(self, payload):
        """Make HTTP request with proper headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        try:
            response = requests.post(
                f"{self.base_url}/mcp/", json=payload, headers=headers, timeout=30
            )
            if response.status_code != 200:
                return None
            return response
        except Exception as e:
            print(f"Request failed: {e}", file=sys.stderr)
            return None

    def _parse_response(self, response):
        """Parse SSE response and extract result."""
        try:
            for line in response.text.strip().split("\n"):
                if line.startswith("data: "):
                    return json.loads(line[6:])  # Remove 'data: ' prefix
        except Exception:
            pass
        return None

    def list_tools(self):
        """List available tools from the MCP server."""
        payload = {"jsonrpc": "2.0", "id": "list_tools", "method": "tools/list"}
        response = self._make_request(payload)
        if response:
            result = self._parse_response(response)
            return result if result else {"error": "Failed to parse response"}
        return {"error": "Failed to list tools"}

    def call_tool(self, tool_name: str, arguments: dict = None):
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool response
        """
        payload = {
            "jsonrpc": "2.0",
            "id": "call_tool",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments or {}},
        }
        response = self._make_request(payload)
        if response:
            result = self._parse_response(response)
            return result if result else {"error": "Failed to parse response"}
        return {"error": f"Failed to call tool {tool_name}"}


@click.group()
@click.option("--host", default="localhost", help="Server host")
@click.option("--port", default=8000, type=int, help="Server port")
@click.option("--base-url", default="https://open.cdash.org", help="CDash server URL")
@click.pass_context
def cli(ctx, host, port, base_url):
    """CDash MCP Client - Execute GraphQL queries against CDash via MCP server."""
    ctx.ensure_object(dict)
    ctx.obj["client"] = MCPClient(host=host, port=port)
    ctx.obj["base_url"] = base_url


@cli.command()
@click.pass_context
def list_tools(ctx):
    """List available MCP tools."""
    client = ctx.obj["client"]
    result = client.list_tools()

    if "error" in result:
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)

    click.echo("Available tools:")
    if "tools" in result:
        for tool in result["tools"]:
            click.echo(f"\n  {tool['name']}")
            if "description" in tool:
                click.echo(f"    {tool['description']}")
    else:
        click.echo(json.dumps(result, indent=2))


@cli.command()
@click.argument("query")
@click.option("--variables", default=None, help="GraphQL variables as JSON string")
@click.option("--no-cache", is_flag=True, help="Disable caching for this query")
@click.pass_context
def query(ctx, query, variables, no_cache):
    """Execute a GraphQL query against CDash."""
    client = ctx.obj["client"]
    base_url = ctx.obj["base_url"]

    arguments = {
        "query": query,
        "base_url": base_url,
        "use_cache": not no_cache,
    }

    if variables:
        try:
            arguments["variables"] = json.loads(variables)
        except json.JSONDecodeError as e:
            click.echo(f"Error: Invalid JSON in variables: {e}", err=True)
            sys.exit(1)

    result = client.call_tool("execute_graphql_query", arguments)

    if "error" in result:
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)

    if "result" in result and "content" in result["result"]:
        for item in result["result"]["content"]:
            if "text" in item:
                click.echo(item["text"])
    else:
        click.echo(json.dumps(result, indent=2))


@cli.command()
@click.pass_context
def cache_stats(ctx):
    """Get cache statistics."""
    client = ctx.obj["client"]
    result = client.call_tool("get_cache_stats", {})

    if "error" in result:
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)

    if "result" in result and "content" in result["result"]:
        for item in result["result"]["content"]:
            if "text" in item:
                click.echo(item["text"])
    else:
        click.echo(json.dumps(result, indent=2))


@cli.command()
@click.pass_context
def clear_cache(ctx):
    """Clear all cached queries."""
    client = ctx.obj["client"]
    result = client.call_tool("clear_cache", {})

    if "error" in result:
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)

    if "result" in result and "content" in result["result"]:
        for item in result["result"]["content"]:
            if "text" in item:
                click.echo(item["text"])
    else:
        click.echo(json.dumps(result, indent=2))


def main():
    """Entry point for the client."""
    cli(obj={})


if __name__ == "__main__":
    main()
