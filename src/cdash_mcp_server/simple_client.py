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
        payload = {
            "jsonrpc": "2.0",
            "id": "list_tools",
            "method": "tools/list"
        }
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
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
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
@click.option("--token", default="", help="CDash authentication token")
@click.pass_context
def cli(ctx, host, port, base_url, token):
    """CDash MCP Client - Query CDash via MCP server."""
    ctx.ensure_object(dict)
    ctx.obj['client'] = MCPClient(host=host, port=port)
    ctx.obj['base_url'] = base_url
    ctx.obj['token'] = token


@cli.command()
@click.pass_context
def list_tools(ctx):
    """List available MCP tools."""
    client = ctx.obj['client']
    result = client.list_tools()

    if 'error' in result:
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)

    click.echo("Available tools:")
    if 'tools' in result:
        for tool in result['tools']:
            click.echo(f"\n  {tool['name']}")
            if 'description' in tool:
                click.echo(f"    {tool['description']}")
    else:
        click.echo(json.dumps(result, indent=2))


@cli.command()
@click.pass_context
def list_projects(ctx):
    """List all CDash projects."""
    client = ctx.obj['client']
    base_url = ctx.obj['base_url']
    token = ctx.obj['token']

    result = client.call_tool("list_projects", {
        "base_url": base_url,
        "token": token
    })

    if 'error' in result:
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)

    if 'result' in result and 'content' in result['result']:
        for item in result['result']['content']:
            if 'text' in item:
                click.echo(item['text'])
    else:
        click.echo(json.dumps(result, indent=2))


@cli.command()
@click.argument('project_name')
@click.option('--limit', default=50, type=int, help='Maximum number of builds to return')
@click.pass_context
def list_builds(ctx, project_name, limit):
    """List builds for a specific project."""
    client = ctx.obj['client']
    base_url = ctx.obj['base_url']
    token = ctx.obj['token']

    result = client.call_tool("list_builds", {
        "project_name": project_name,
        "base_url": base_url,
        "token": token,
        "limit": limit
    })

    if 'error' in result:
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)

    if 'result' in result and 'content' in result['result']:
        for item in result['result']['content']:
            if 'text' in item:
                click.echo(item['text'])
    else:
        click.echo(json.dumps(result, indent=2))


def main():
    """Entry point for the client."""
    cli(obj={})


if __name__ == '__main__':
    main()
