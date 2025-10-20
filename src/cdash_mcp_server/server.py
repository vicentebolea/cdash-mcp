#!/usr/bin/env python3
"""CDash MCP Server - Provides CDash query capabilities via MCP."""

import asyncio
import click
from fastmcp import FastMCP
from .cdash_client import CDashClient

# Initialize MCP server
mcp = FastMCP("CDash MCP Server")


def _list_projects_impl(base_url: str, token: str) -> str:
    """Implementation of list_projects tool."""
    if not token:
        return "Error: token parameter is required"

    if not base_url:
        return "Error: base_url parameter is required"

    try:
        client = CDashClient(base_url=base_url, token=token)
        projects = client.list_projects()

        if projects is None:
            return f"Error: Failed to retrieve projects from CDash API at {base_url}"

        if not projects:
            return f"No projects found in CDash at {base_url}"

        # Format projects nicely
        lines = [f"# CDash Projects ({base_url})", ""]
        for project in projects:
            lines.append(f"## {project['name']}")
            if project.get("description"):
                lines.append(f"**Description:** {project['description']}")
            lines.append(f"**Build Count:** {project.get('buildCount', 0)}")
            if project.get("homeurl"):
                lines.append(f"**Home URL:** {project['homeurl']}")
            lines.append(f"**Visibility:** {project.get('visibility', 'Unknown')}")
            lines.append(f"**ID:** {project['id']}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"Error listing projects from {base_url}: {str(e)}"


def _list_builds_impl(
    base_url: str, token: str, project_name: str, limit: int = 50
) -> str:
    """Implementation of list_builds tool."""
    if not token:
        return "Error: token parameter is required"

    if not base_url:
        return "Error: base_url parameter is required"

    if not project_name:
        return "Error: project_name is required"

    try:
        client = CDashClient(base_url=base_url, token=token)
        builds = client.list_builds(project_name, limit)

        if builds is None:
            return (
                f"Error: Failed to retrieve builds for project '{project_name}' "
                f"from {base_url}. Project may not exist."
            )

        if not builds:
            return f"No builds found for project '{project_name}' at {base_url}"

        # Format builds nicely
        lines = [f"# Builds for Project: {project_name} ({base_url})", ""]
        lines.append(f"Showing {len(builds)} builds (limit: {limit})")
        lines.append("")

        for i, build in enumerate(builds, 1):
            status = "FAILED" if build.get("failedTestsCount", 0) > 0 else "PASSED"
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
        return f"Error listing builds for '{project_name}' from {base_url}: {str(e)}"


@mcp.tool()
def list_projects(base_url: str = "https://open.cdash.org", token: str = "") -> str:
    """List all available CDash projects.

    Args:
        base_url: CDash server URL (default: https://open.cdash.org)
        token: CDash authentication token

    Returns:
        Formatted string with project information including name, description,
        build count, and home URL for each project.
    """
    return _list_projects_impl(base_url, token)


@mcp.tool()
def list_builds(
    project_name: str,
    base_url: str = "https://open.cdash.org",
    token: str = "",
    limit: int = 50,
) -> str:
    """List builds for a specific CDash project.

    Args:
        project_name: Name of the CDash project (e.g., "Spack Testing")
        base_url: CDash server URL (default: https://open.cdash.org)
        token: CDash authentication token
        limit: Maximum number of builds to return (default: 50)

    Returns:
        Formatted string with build information including build name, ID,
        site, start/end times, and test counts.
    """
    return _list_builds_impl(base_url, token, project_name, limit)


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="Transport protocol",
)
@click.option("--host", default="127.0.0.1", help="Host (HTTP only)")
@click.option("--port", default=8000, type=int, help="Port (HTTP only)")
def main(transport, host, port):
    """Run the CDash MCP Server.

    The server accepts CDash URL and token as parameters when calling tools.
    No configuration needed at server startup.
    """
    if transport == "http":
        click.echo(f"Starting CDash MCP Server on http://{host}:{port}")
        click.echo("Tools accept base_url and token as parameters")
        asyncio.run(mcp.run_http_async(host=host, port=port))
    else:
        click.echo("Starting CDash MCP Server on stdio transport")
        click.echo("Tools accept base_url and token as parameters")
        mcp.run()


if __name__ == "__main__":
    main()
