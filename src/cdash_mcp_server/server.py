#!/usr/bin/env python3
"""CDash MCP Server - Provides CDash query capabilities via MCP."""

import asyncio
import click
import os
from fastmcp import FastMCP
from .cdash_client import CDashClient

# Initialize MCP server
mcp = FastMCP("CDash MCP Server")

# Global CDash client (will be initialized with token)
_cdash_client = None


def _get_client() -> CDashClient:
    """Get or create CDash client instance."""
    global _cdash_client
    if _cdash_client is None:
        token = os.getenv('CDASH_TOKEN')
        base_url = os.getenv('CDASH_BASE_URL', 'https://cdash.spack.io')
        _cdash_client = CDashClient(base_url=base_url, token=token)
    return _cdash_client


def _set_client(base_url: str, token: str):
    """Set the global CDash client with specific credentials."""
    global _cdash_client
    _cdash_client = CDashClient(base_url=base_url, token=token)


def _list_projects_impl() -> str:
    """Implementation of list_projects tool."""
    client = _get_client()

    if not client.token:
        return "Error: CDASH_TOKEN environment variable not set or --token not provided"

    try:
        projects = client.list_projects()

        if projects is None:
            return "Error: Failed to retrieve projects from CDash API"

        if not projects:
            return "No projects found in CDash"

        # Format projects nicely
        lines = ["# CDash Projects", ""]
        for project in projects:
            lines.append(f"## {project['name']}")
            if project.get('description'):
                lines.append(f"**Description:** {project['description']}")
            lines.append(f"**Build Count:** {project.get('buildCount', 0)}")
            if project.get('homeurl'):
                lines.append(f"**Home URL:** {project['homeurl']}")
            lines.append(f"**Visibility:** {project.get('visibility', 'Unknown')}")
            lines.append(f"**ID:** {project['id']}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"Error listing projects: {str(e)}"


def _list_builds_impl(project_name: str, limit: int = 50) -> str:
    """Implementation of list_builds tool."""
    client = _get_client()

    if not client.token:
        return "Error: CDASH_TOKEN environment variable not set or --token not provided"

    if not project_name:
        return "Error: project_name is required"

    try:
        builds = client.list_builds(project_name, limit)

        if builds is None:
            return f"Error: Failed to retrieve builds for project '{project_name}'. Project may not exist."

        if not builds:
            return f"No builds found for project '{project_name}'"

        # Format builds nicely
        lines = [f"# Builds for Project: {project_name}", ""]
        lines.append(f"Showing {len(builds)} builds (limit: {limit})")
        lines.append("")

        for i, build in enumerate(builds, 1):
            status = "FAILED" if build.get('failedTestsCount', 0) > 0 else "PASSED"
            status_emoji = "❌" if status == "FAILED" else "✅"

            lines.append(f"## Build {i}: {build['name']} {status_emoji}")
            lines.append(f"**Status:** {status}")
            lines.append(f"**ID:** {build['id']}")
            lines.append(f"**Site:** {build['site']['name']}")
            lines.append(f"**Stamp:** {build.get('stamp', 'N/A')}")
            lines.append(f"**Start Time:** {build.get('startTime', 'N/A')}")
            lines.append(f"**End Time:** {build.get('endTime', 'N/A')}")
            lines.append(f"**Failed Tests:** {build.get('failedTestsCount', 0)}")
            lines.append(f"**Passed Tests:** {build.get('passedTestsCount', 0)}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"Error listing builds for '{project_name}': {str(e)}"


@mcp.tool()
def list_projects() -> str:
    """List all available CDash projects.

    Returns:
        Formatted string with project information including name, description,
        build count, and home URL for each project.
    """
    return _list_projects_impl()


@mcp.tool()
def list_builds(project_name: str, limit: int = 50) -> str:
    """List builds for a specific CDash project.

    Args:
        project_name: Name of the CDash project (e.g., "Spack Testing")
        limit: Maximum number of builds to return (default: 50)

    Returns:
        Formatted string with build information including build name, ID,
        site, start/end times, and test counts.
    """
    return _list_builds_impl(project_name, limit)


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="Transport protocol",
)
@click.option("--host", default="127.0.0.1", help="Host (HTTP only)")
@click.option("--port", default=8000, type=int, help="Port (HTTP only)")
@click.option("--token", help="CDash authentication token (can also use CDASH_TOKEN env var)")
@click.option("--base-url", default="https://cdash.spack.io", help="CDash base URL")
def main(transport, host, port, token, base_url):
    """Run the CDash MCP Server."""
    # Set token from command line or environment
    if token:
        os.environ['CDASH_TOKEN'] = token
    if base_url:
        os.environ['CDASH_BASE_URL'] = base_url

    # Initialize client with provided credentials
    if token:
        _set_client(base_url, token)

    if transport == "http":
        click.echo(f"Starting CDash MCP Server on http://{host}:{port}")
        asyncio.run(mcp.run_http_async(host=host, port=port))
    else:
        click.echo("Starting CDash MCP Server on stdio transport")
        mcp.run()


if __name__ == "__main__":
    main()
