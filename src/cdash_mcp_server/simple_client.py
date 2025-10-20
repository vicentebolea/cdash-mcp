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
        self.base_url = f"http://{host}:{port}/mcp"

    def list_tools(self):
        """List available tools from the MCP server."""
        url = f"{self.base_url}/list_tools"
        try:
            response = requests.post(url, json={}, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def call_tool(self, tool_name: str, arguments: dict = None):
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool response
        """
        url = f"{self.base_url}/call_tool"
        payload = {
            "name": tool_name,
            "arguments": arguments or {}
        }
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}


@click.group()
@click.option("--host", default="localhost", help="Server host")
@click.option("--port", default=8000, type=int, help="Server port")
@click.pass_context
def cli(ctx, host, port):
    """CDash MCP Client - Query CDash via MCP server."""
    ctx.ensure_object(dict)
    ctx.obj['client'] = MCPClient(host=host, port=port)


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
    result = client.call_tool("list_projects")

    if 'error' in result:
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)

    if 'content' in result:
        for item in result['content']:
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
    result = client.call_tool("list_builds", {
        "project_name": project_name,
        "limit": limit
    })

    if 'error' in result:
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)

    if 'content' in result:
        for item in result['content']:
            if 'text' in item:
                click.echo(item['text'])
    else:
        click.echo(json.dumps(result, indent=2))


def main():
    """Entry point for the client."""
    cli(obj={})


if __name__ == '__main__':
    main()
